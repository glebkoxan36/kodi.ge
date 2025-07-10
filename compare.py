import re
import logging
import time
from collections import defaultdict
from functools import lru_cache
from bson import ObjectId
from flask import jsonify, request

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Веса характеристик для сравнения
WEIGHTS = {
    "Процессор": 4.5,
    "CPU Балл": 5.0,
    "GPU": 5.0,
    "GPU Балл": 5.0,
    "Оценка AnTuTu": 4.7,
    "3DMark Wild Life": 4.8,
    "Игры (FPS @ 1080p)": 4.7,
    "ОЗУ (ГБ)": 3.2,
    "ПЗУ (ГБ)": 2.5,
    "Тип дисплея": 3.5,
    "Частота обновления (Гц)": 4.0,
    "Емкость батареи (mAh)": 3.8,
    "Время работы (ч)": 4.0,
    "TDP (Вт)": 3.0,
    "Вес (г)": 2.0,
    "Стартовая цена (руб)": 2.5
}

# Категории характеристик
SPEC_CATEGORIES = {
    "Процессор": [
        "Процессор", "CPU Балл", "CPU Ядра", "CPU Частота (ГГц)",
        "Оценка AnTuTu", "Geekbench (одиночное ядро)", "Geekbench (многоядерное)", "TDP (Вт)"
    ],
    "Видеокарта": [
        "GPU", "GPU Балл", "3DMark Wild Life", "GFXBench ES 3.1 (fps)", 
        "Игры (FPS @ 1080p)", "Поддержка RT"
    ],
    "Память": ["ОЗУ (ГБ)", "Тип ОЗУ", "ПЗУ (ГБ)"],
    "Экран": ["Тип дисплея", "Частота обновления (Гц)", "Плотность пикселей (PPI)"],
    "Батарея": ["Емкость батареи (mAh)", "Время работы (ч)"],
    "Дополнительно": ["Поддержка 5G", "NFC", "Вес (г)", "Стартовая цена (руб)"]
}

# Правила сравнения характеристик
SPEC_RULES = {
    "numeric": [
        "CPU Балл", "GPU Балл", "Оценка AnTuTu", "Geekbench (одиночное ядро)", 
        "Geekbench (многоядерное)", "3DMark Wild Life", "GFXBench ES 3.1 (fps)",
        "Игры (FPS @ 1080p)", "ОЗУ (ГБ)", "ПЗУ (ГБ)", "Плотность пикселей (PPI)",
        "Емкость батареи (mAh)", "Время работы (ч)"
    ],
    "numeric_reverse": ["TDP (Вт)", "Вес (г)", "Стартовая цена (руб)"],
    "boolean": ["Поддержка RT", "Поддержка 5G", "NFC"],
    "gpu_priority": [
        "Apple M4 10-core GPU", "Qualcomm Adreno 840", 
        "ARM Immortalis-G925", "Apple A18 Pro GPU", 
        "Samsung Xclipse 940"
    ]
}

# Справочник CPU (производительность в баллах)
CPU_SCORES = {
    "Dimensity 9300": 100, "Snapdragon 8 Gen 3": 98, "A17 Pro": 95, 
    "Exynos 2400": 92, "A16 Bionic": 90, "Dimensity 9200 Plus": 88, 
    "Snapdragon 8 Gen 2": 87, "Dimensity 9200": 85, "Dimensity 8300": 87, 
    "A15 Bionic": 85, "Snapdragon 8+ Gen 1": 82, "Dimensity 9000 Plus": 80,
    # ... остальные значения ...
}

# Справочник GPU (производительность в баллах)
GPU_SCORES = {
    "Apple M4 10-core GPU": 100, "Qualcomm Adreno 840": 98, 
    "ARM Immortalis-G925 MC16": 95, "Apple A18 Pro GPU": 92,
    "Qualcomm Adreno 830": 90, "ARM Immortalis-G925 MC12": 88,
    "Qualcomm Adreno 750": 90, "Samsung Xclipse 950": 85,
    # ... остальные значения ...
}

# Кэширование функций нормализации
@lru_cache(maxsize=512)
def normalize_cpu_name(name):
    """Нормализация названий процессоров с кэшированием"""
    if not name:
        return "Unknown CPU"
    
    name = name.lower()
    if "dimensity" in name:
        if "9300" in name: return "Dimensity 9300"
        if "9200+" in name: return "Dimensity 9200 Plus"
        # ... остальные условия ...
    return name.title()

@lru_cache(maxsize=512)
def normalize_gpu_name(name):
    """Нормализация названий видеокарт с кэшированием"""
    if not name:
        return "Unknown GPU"
    
    name = name.lower()
    if "adreno" in name:
        if "840" in name: return "Qualcomm Adreno 840"
        # ... остальные условия ...
    return name.title()

def enrich_phone_data(phone):
    """Обогащение данных телефона с обработкой ошибок"""
    try:
        # CPU
        cpu = phone.get("Процессор", "")
        if cpu:
            cpu_name = normalize_cpu_name(cpu)
            phone["Процессор"] = cpu_name
            phone["CPU Балл"] = CPU_SCORES.get(cpu_name, 0)
        
        # GPU
        gpu = phone.get("GPU", "")
        if gpu:
            gpu_name = normalize_gpu_name(gpu)
            phone["GPU"] = gpu_name
            phone["GPU Балл"] = GPU_SCORES.get(gpu_name, 0)
            
            # Автозаполнение FPS
            if "Adreno 840" in gpu_name: 
                phone["Игры (FPS @ 1080p)"] = 120
            elif "Immortalis-G925" in gpu_name: 
                phone["Игры (FPS @ 1080p)"] = 105
            # ... другие условия ...
        
        # 3DMark
        if "GPU Балл" in phone:
            phone["3DMark Wild Life"] = int(150 * phone["GPU Балл"])
            
    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        
    return phone

def try_parse_number(value):
    """Парсинг числовых значений из строк"""
    if isinstance(value, (int, float)):
        return value
    if value is None:
        return None
        
    try:
        match = re.search(r'([\d.,-]+)', str(value))
        if match:
            return float(match.group(1).replace(',', '.'))
    except:
        pass
    return None

def compare_values(rule, value1, value2):
    """Сравнение значений по заданным правилам"""
    try:
        if rule == "gpu_priority":
            gpu_priority_order = SPEC_RULES["gpu_priority"]
            val1 = normalize_gpu_name(str(value1))
            val2 = normalize_gpu_name(str(value2))
            
            idx1 = gpu_priority_order.index(val1) if val1 in gpu_priority_order else len(gpu_priority_order)
            idx2 = gpu_priority_order.index(val2) if val2 in gpu_priority_order else len(gpu_priority_order)
            
            if idx1 < idx2: return 'phone1'
            if idx1 > idx2: return 'phone2'
            return None
        
        elif rule == "numeric":
            num1 = try_parse_number(value1)
            num2 = try_parse_number(value2)
            if num1 is not None and num2 is not None:
                if num1 > num2: return 'phone1'
                if num1 < num2: return 'phone2'
            return None
        
        elif rule == "numeric_reverse":
            num1 = try_parse_number(value1)
            num2 = try_parse_number(value2)
            if num1 is not None and num2 is not None:
                if num1 < num2: return 'phone1'
                if num1 > num2: return 'phone2'
            return None
        
        elif rule == "boolean":
            true_values = ['да', 'yes', 'есть', '+', 'е', 'y', 'true', 'supported', 'присутствует']
            false_values = ['нет', 'no', 'отсутствует', '-', 'н', 'n', 'false', 'unsupported', 'не поддерживается']
            
            val1 = str(value1).strip().lower()
            val2 = str(value2).strip().lower()
            
            if val1 in true_values and val2 in false_values: return 'phone1'
            if val1 in false_values and val2 in true_values: return 'phone2'
            return None
            
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        
    return None

def compare_two_phones(phone1, phone2):
    """Основная функция сравнения с оптимизацией"""
    start_time = time.time()
    logger.info(f"Starting comparison: {phone1.get('model')} vs {phone2.get('model')}")
    
    # Обогащение данных
    try:
        phone1 = enrich_phone_data(phone1.copy())
        phone2 = enrich_phone_data(phone2.copy())
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        return {"error": "Data enrichment failed"}
    
    # Игнорируемые поля
    ignore_fields = {'_id', 'image_url', 'image', 'brand', 'model', 
                    'release_year', 'Бренд', 'Модель', 'Год выпуска'}
    
    # Сбор всех характеристик
    all_keys = set(phone1.keys()) | set(phone2.keys()) - ignore_fields
    
    # Группировка по категориям
    categories = defaultdict(list)
    for key in all_keys:
        category_name = "Дополнительно"
        for cat, fields in SPEC_CATEGORIES.items():
            if key in fields:
                category_name = cat
                break
        categories[category_name].append(key)
    
    # Упорядочивание категорий
    ordered_categories = [cat for cat in SPEC_CATEGORIES if cat in categories]
    if "Дополнительно" in categories: 
        ordered_categories.append("Дополнительно")
    
    # Основные структуры для результатов
    comparison = []
    overall_scores = {'phone1': 0, 'phone2': 0}
    category_scores = defaultdict(lambda: {'phone1': 0, 'phone2': 0})

    # Сравнение по категориям
    for category in ordered_categories:
        specs_list = []
        for key in categories[category]:
            val1 = phone1.get(key, "N/A")
            val2 = phone2.get(key, "N/A")
            
            # Определение правила
            rule = None
            for rule_type, fields in SPEC_RULES.items():
                if key in fields: 
                    rule = rule_type
                    break
            
            winner = None
            weight = WEIGHTS.get(key, 1.0)
            
            # Применение правила
            if rule:
                winner = compare_values(rule, val1, val2)
                if winner:
                    overall_scores[winner] += weight
                    category_scores[category][winner] += weight

            specs_list.append({
                'name': key,
                'phone1_value': val1,
                'phone2_value': val2,
                'winner': winner,
                'weight': weight
            })
        
        # Расчет процентов для категории
        total_cat = category_scores[category]['phone1'] + category_scores[category]['phone2']
        cat_percent_phone1 = round(category_scores[category]['phone1'] / total_cat * 100, 1) if total_cat > 0 else 0
        cat_percent_phone2 = round(category_scores[category]['phone2'] / total_cat * 100, 1) if total_cat > 0 else 0
        
        comparison.append({
            'category': category,
            'specs': specs_list,
            'category_percent_phone1': cat_percent_phone1,
            'category_percent_phone2': cat_percent_phone2,
        })
    
    # Общий результат
    total_score = overall_scores['phone1'] + overall_scores['phone2']
    if total_score > 0:
        percent_phone1 = round(overall_scores['phone1'] / total_score * 100, 1)
        percent_phone2 = round(overall_scores['phone2'] / total_score * 100, 1)
    else:
        percent_phone1 = percent_phone2 = 50.0
    
    # Определение победителя
    overall_winner = None
    if overall_scores['phone1'] > overall_scores['phone2']: 
        overall_winner = 'phone1'
    elif overall_scores['phone1'] < overall_scores['phone2']: 
        overall_winner = 'phone2'
    
    # Генерация анализа
    ai_analysis = generate_ai_analysis(phone1, phone2, comparison, overall_winner, percent_phone1, percent_phone2)
    
    logger.info(f"Comparison completed in {time.time() - start_time:.2f}s")
    
    return {
        'phone1': phone1,
        'phone2': phone2,
        'comparison': comparison,
        'overall_winner': overall_winner,
        'percent_phone1': percent_phone1,
        'percent_phone2': percent_phone2,
        'ai_analysis': ai_analysis
    }

def generate_ai_analysis(phone1, phone2, comparison, overall_winner, percent1, percent2):
    """Генерация текстового анализа с обработкой ошибок"""
    try:
        model1 = phone1.get('model', 'Phone 1')
        model2 = phone2.get('model', 'Phone 2')
        advantage = abs(percent1 - percent2)
        
        analysis = f"<p>შედარების შედეგები აჩვენებს, რომ <strong>{model1 if overall_winner == 'phone1' else model2}</strong> "
        analysis += f"საერთო ჯამში {advantage}%-ით უკეთესია.</p>"
        
        analysis += "<p>ძირითადი განსხვავებები:</p><ul>"
        for category in comparison:
            if abs(category['category_percent_phone1'] - category['category_percent_phone2']) > 5:
                winner = model1 if category['category_percent_phone1'] > category['category_percent_phone2'] else model2
                diff = abs(category['category_percent_phone1'] - category['category_percent_phone2'])
                analysis += f"<li><strong>{category['category']}</strong>: {winner} {diff}%-ით უკეთესია</li>"
        analysis += "</ul>"
        
        if advantage < 5:
            analysis += "<p>ორივე მოწყობილობა ძალიან ახლოსაა თავიანთ შესრულებაში.</p>"
        elif advantage < 15:
            analysis += f"<p><strong>{model1 if overall_winner == 'phone1' else model2}</strong> მნიშვნელოვან უპირატესობას იჩენს ზემოთ ჩამოთვლილ კატეგორიებში.</p>"
        else:
            analysis += f"<p><strong>{model1 if overall_winner == 'phone1' else model2}</strong> აშკარად უკეთესი არჩევანია.</p>"
        
        return analysis
        
    except Exception as e:
        logger.error(f"AI analysis generation failed: {e}")
        return "<p>AI ანალიზი ხელმიუწვდომელია</p>"

def parse_phone_id(phone_id):
    """Преобразование ID в ObjectId с валидацией"""
    try:
        if isinstance(phone_id, dict) and '$oid' in phone_id:
            return ObjectId(phone_id['$oid'])
        elif isinstance(phone_id, str):
            return ObjectId(phone_id)
        elif isinstance(phone_id, ObjectId):
            return phone_id
    except:
        logger.error(f"Invalid phone ID format: {phone_id}")
    raise ValueError("Invalid phone ID format")

def convert_objectids(obj):
    """Рекурсивное преобразование ObjectId в строки"""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [convert_objectids(item) for item in obj]
    if isinstance(obj, dict):
        return {key: convert_objectids(value) for key, value in obj.items()}
    return obj

# API Endpoint
@app.route('/api/compare', methods=['POST'])
def api_compare():
    start_time = time.time()
    data = request.get_json()
    
    if not data or 'phone1_id' not in data or 'phone2_id' not in data:
        return jsonify({"error": "Missing phone IDs"}), 400
    
    try:
        # Преобразование ID
        phone1_id = parse_phone_id(data['phone1_id'])
        phone2_id = parse_phone_id(data['phone2_id'])
        
        # Получение данных из базы
        phone1 = db.phones.find_one({"_id": phone1_id})
        phone2 = db.phones.find_one({"_id": phone2_id})
        
        if not phone1 or not phone2:
            return jsonify({"error": "Phone not found"}), 404
        
        # Сравнение
        result = compare_two_phones(phone1, phone2)
        return jsonify(convert_objectids(result))
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Comparison failed")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        logger.info(f"API request processed in {time.time() - start_time:.2f}s")
