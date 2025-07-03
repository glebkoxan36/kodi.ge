import re
from collections import defaultdict

# Обновленные веса характеристик
WEIGHTS = {
    # Процессор
    "Процессор": 4.5,
    "CPU Балл": 5.0,
    "CPU Ядра": 3.8,
    "CPU Частота (ГГц)": 4.0,
    "Оценка AnTuTu": 4.7,
    "Geekbench (одиночное ядро)": 4.2,
    "Geekbench (многоядерное)": 4.5,
    "TDP (Вт)": 3.0,
    
    # Видеокарта
    "GPU": 5.0,
    "GPU Балл": 5.0,
    "3DMark Wild Life": 4.8,
    "GFXBench ES 3.1 (fps)": 4.6,
    "Игры (FPS @ 1080p)": 4.7,
    "Поддержка RT": 3.5,
    
    # Память
    "ОЗУ (ГБ)": 3.2,
    "Тип ОЗУ": 2.0,
    "ПЗУ (ГБ)": 2.5,
    
    # Экран
    "Тип дисплея": 3.5,
    "Частота обновления (Гц)": 4.0,
    "Плотность пикселей (PPI)": 3.0,
    
    # Батарея
    "Емкость батареи (mAh)": 3.8,
    "Время работы (ч)": 4.0
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
    "Память": [
        "ОЗУ (ГБ)", "Тип ОЗУ", "ПЗУ (ГБ)"
    ],
    "Экран": [
        "Тип дисплея", "Частота обновления (Гц)", "Плотность пикселей (PPI)"
    ],
    "Батарея": [
        "Емкость батареи (mAh)", "Время работы (ч)"
    ],
    "Дополнительно": [
        "Поддержка 5G", "NFC", "Вес (г)", "Стартовая цена (руб)"
    ]
}

# Правила сравнения характеристик
SPEC_RULES = {
    "numeric": [
        "CPU Балл", "GPU Балл", "Оценка AnTuTu", "Geekbench (одиночное ядро)", 
        "Geekbench (многоядерное)", "3DMark Wild Life", "GFXBench ES 3.1 (fps)",
        "Игры (FPS @ 1080p)", "ОЗУ (ГБ)", "ПЗУ (ГБ)", "Плотность пикселей (PPI)",
        "Емкость батареи (mAh)", "Время работы (ч)"
    ],
    "numeric_reverse": [
        "TDP (Вт)", "Вес (г)", "Стартовая цена (руб)"
    ],
    "boolean": [
        "Поддержка RT", "Поддержка 5G", "NFC"
    ],
    "gpu_priority": [
        "Apple M4 10-core GPU", "Qualcomm Adreno 840", "ARM Immortalis-G925",
        "Apple A18 Pro GPU", "Samsung Xclipse 940"
    ]
}

# Полный справочник CPU (100+ моделей)
CPU_SCORES = {
    "Dimensity 9300": 100, "Snapdragon 8 Gen 3": 98, "A17 Pro": 95, "Exynos 2400": 92,
    "A16 Bionic": 90, "Dimensity 9200 Plus": 88, "Snapdragon 8 Gen 2": 87, 
    "Dimensity 9200": 85, "Dimensity 8300": 87, "A15 Bionic": 85, 
    "Snapdragon 8+ Gen 1": 82, "Dimensity 9000 Plus": 80, "Tensor G3": 76,
    "Snapdragon 8 Gen 1": 75, "A14 Bionic": 72, "Exynos 2200": 70, 
    "Snapdragon 7+ Gen 2": 78, "Dimensity 9000": 75, "A13 Bionic": 70,
    "Snapdragon 888 Plus": 68, "Kirin 9000": 67, "Tensor G2": 65,
    "Snapdragon 888": 64, "Dimensity 8200": 66, "Exynos 2100": 63,
    "Snapdragon 7 Gen 3": 62, "Dimensity 8100": 60, "Dimensity 1200": 58,
    "Snapdragon 865 Plus": 57, "Kirin 9000S": 65, "Dimensity 1300": 56,
    "Dimensity 1100": 55, "Snapdragon 870": 60, "Dimensity 7200 Ultra": 52,
    "Dimensity 8050": 54, "Dimensity 8020": 53, "Dimensity 7200": 50,
    "Snapdragon 865": 58, "Exynos 990": 52, "A12 Bionic": 48,
    "Kirin 990 (5G)": 50, "Snapdragon 782G": 49, "Snapdragon 7 Gen 1": 47,
    "Snapdragon 860": 45, "Dimensity 1000 Plus": 44, "Snapdragon 778G+": 48,
    "Snapdragon 780G": 46, "Snapdragon 855+": 45, "Exynos 9820": 42,
    "Snapdragon 778G": 46, "Exynos 9825": 43, "Snapdragon 855": 44,
    "Snapdragon 6 Gen 1": 42, "Snapdragon 7s Gen 2": 41, "Exynos 1380": 45,
    "Dimensity 1050": 40, "Dimensity 7050": 55, "Dimensity 1080": 38,
    "Dimensity 920": 37, "Kirin 980": 43, "Dimensity 7030": 39,
    "Dimensity 7020": 36, "Dimensity 930": 35, "Dimensity 900": 40,
    "A11 Bionic": 38, "Dimensity 820": 37, "Unisoc T820": 36,
    "Exynos 1280": 34, "Snapdragon 845": 33, "Dimensity 6080": 32,
    "Snapdragon 4 Gen 2": 31, "Exynos 1330": 33, "Snapdragon 695": 48,
    "Dimensity 800": 30, "Exynos 980": 32, "Dimensity 800U": 31,
    "Kirin 810": 29, "Exynos 9810": 28, "Dimensity 6100+": 30,
    "Dimensity 6020": 29, "Snapdragon 4 Gen 1": 28, "Dimensity 810": 33,
    "Dimensity 720": 31, "Snapdragon 765G": 30, "Helio G99": 35,
    "Snapdragon 480+": 27, "Snapdragon 732G": 29, "Snapdragon 720G": 28,
    "Dimensity 700": 26, "Snapdragon 750G": 25, "Helio G95": 24,
    "Snapdragon 690": 23
}

# Полный справочник GPU (80+ моделей)
GPU_SCORES = {
    "Apple M4 10-core GPU": 100, "Qualcomm Adreno 840": 98, 
    "ARM Immortalis-G925 MC16": 95, "Apple A18 Pro GPU": 92,
    "Qualcomm Adreno 830": 90, "ARM Immortalis-G925 MC12": 88,
    "Qualcomm Adreno 750": 90, "Samsung Xclipse 950": 85,
    "Samsung Xclipse 940": 85, "Qualcomm Adreno 740": 88,
    "ARM Immortalis-G720 MP12": 83, "ARM Immortalis-G715 MP11": 80,
    "Apple A16 GPU 5-Core": 78, "ARM Immortalis-G720 MP7": 75,
    "Qualcomm Adreno 735": 72, "Apple A15 GPU 5-Core": 70,
    "Apple A16 GPU 4-Core": 68, "Qualcomm Adreno 732": 65,
    "Qualcomm Adreno 730": 63, "ARM Mali-G715 MP7": 60,
    "ARM Mali-G615 MP6": 58, "Qualcomm Adreno 725": 55,
    "Qualcomm Adreno 720": 50, "ARM Mali-G710 MP10": 53,
    "Apple A15 GPU 4-Core": 52, "Apple A14 Bionic GPU": 50,
    "HiSilicon Maleoon 920": 48, "Samsung Xclipse 920": 45,
    "Qualcomm Adreno 660": 42, "ARM Mali-G78 MP24": 40,
    "ARM Mali-G710 MP7": 38, "ARM Mali-G78 MP22": 37,
    "Apple A13 Bionic GPU": 35, "Apple A12 Bionic GPU": 32,
    "Qualcomm Adreno 650": 30, "ARM Mali-G78 MP20": 28,
    "ARM Mali-G78 MP14": 25, "Apple A11 Bionic GPU": 23,
    "Apple A10X Fusion GPU": 20, "Apple A9X": 18,
    "NVIDIA Tegra X1 Maxwell GPU": 15, "Apple A10 Fusion GPU": 12,
    "ARM Mali-G77 MP11": 25, "Samsung Xclipse 540": 22,
    "Samsung Xclipse 530": 20, "ARM Mali-G77 MP9": 18,
    "ARM Mali-G76 MP16": 15, "ARM Mali-G610 MP6": 25,
    "ARM Mali-G610 MP4": 22, "Qualcomm Adreno 810": 30,
    "Qualcomm Adreno 644": 28, "Qualcomm Adreno 643": 26,
    "Qualcomm Adreno 642": 24, "ARM Mali-G610 MP3": 20,
    "ARM Mali-G615 MP2": 18, "Qualcomm Adreno 642L": 22,
    "Qualcomm Adreno 710": 25, "Qualcomm Adreno 640": 23
}

def normalize_cpu_name(name):
    """Нормализация названий процессоров"""
    name = name.lower()
    if "dimensity" in name:
        if "9300" in name: return "Dimensity 9300"
        if "9200+" in name: return "Dimensity 9200 Plus"
        if "9200" in name: return "Dimensity 9200"
        if "8300" in name: return "Dimensity 8300"
        if "9000+" in name: return "Dimensity 9000 Plus"
        if "9000" in name: return "Dimensity 9000"
    elif "snapdragon" in name:
        if "8 gen 3" in name: return "Snapdragon 8 Gen 3"
        if "8 gen 2" in name: return "Snapdragon 8 Gen 2"
        if "8+ gen 1" in name: return "Snapdragon 8+ Gen 1"
        if "8 gen 1" in name: return "Snapdragon 8 Gen 1"
        if "7+ gen 2" in name: return "Snapdragon 7+ Gen 2"
        if "7 gen 3" in name: return "Snapdragon 7 Gen 3"
    elif "exynos" in name:
        if "2400" in name: return "Exynos 2400"
        if "2200" in name: return "Exynos 2200"
        if "2100" in name: return "Exynos 2100"
    elif "apple" in name or "a" in name:
        if "a17 pro" in name: return "A17 Pro"
        if "a16 bionic" in name: return "A16 Bionic"
        if "a15 bionic" in name: return "A15 Bionic"
    return name.title()

def normalize_gpu_name(name):
    """Нормализация названий видеокарт"""
    name = name.lower()
    if "adreno" in name:
        if "840" in name: return "Qualcomm Adreno 840"
        if "830" in name: return "Qualcomm Adreno 830"
        if "750" in name: return "Qualcomm Adreno 750"
        if "740" in name: return "Qualcomm Adreno 740"
    elif "immortalis" in name or "mali" in name:
        if "g925 mc16" in name: return "ARM Immortalis-G925 MC16"
        if "g925 mc12" in name: return "ARM Immortalis-G925 MC12"
        if "g720 mp12" in name: return "ARM Immortalis-G720 MP12"
    elif "xclipse" in name:
        if "940" in name: return "Samsung Xclipse 940"
        if "920" in name: return "Samsung Xclipse 920"
    elif "apple" in name:
        if "m4" in name: return "Apple M4 10-core GPU"
        if "a18 pro" in name: return "Apple A18 Pro GPU"
        if "a16" in name: return "Apple A16 GPU 5-Core"
    return name.title()

def enrich_phone_data(phone):
    """Обогащение данных телефона"""
    # Нормализация CPU
    if "Процессор" in phone:
        cpu_name = normalize_cpu_name(phone["Процессор"])
        phone["Процессор"] = cpu_name
        phone["CPU Балл"] = CPU_SCORES.get(cpu_name, 0)
    
    # Нормализация GPU
    if "GPU" in phone:
        gpu_name = normalize_gpu_name(phone["GPU"])
        phone["GPU"] = gpu_name
        phone["GPU Балл"] = GPU_SCORES.get(gpu_name, 0)
    
    # Автоматическое заполнение FPS
    if "GPU" in phone:
        gpu = phone["GPU"]
        if "Adreno 840" in gpu: phone["Игры (FPS @ 1080p)"] = 120
        elif "Immortalis-G925" in gpu: phone["Игры (FPS @ 1080p)"] = 105
        elif "Adreno 830" in gpu: phone["Игры (FPS @ 1080p)"] = 110
        elif "Apple A18" in gpu: phone["Игры (FPS @ 1080p)"] = 78
    
    # Добавление 3DMark Wild Life
    if "GPU Балл" in phone:
        gpu_score = phone["GPU Балл"]
        phone["3DMark Wild Life"] = int(150 * gpu_score)
    
    return phone

def try_parse_number(value):
    """Парсинг числовых значений из строк"""
    if isinstance(value, (int, float)):
        return value
    try:
        cleaned = re.sub(r'[^\d.,-]', '', value)
        cleaned = cleaned.replace(',', '.')
        return float(cleaned)
    except:
        return None

def compare_values(rule, value1, value2):
    """Сравнение значений по заданным правилам"""
    # Сравнение приоритетов GPU
    if rule == "gpu_priority":
        gpu_priority_order = [
            "Apple M4 10-core GPU", "Qualcomm Adreno 840", 
            "ARM Immortalis-G925", "Apple A18 Pro GPU", 
            "Samsung Xclipse 940"
        ]
        idx1 = gpu_priority_order.index(value1) if value1 in gpu_priority_order else len(gpu_priority_order)
        idx2 = gpu_priority_order.index(value2) if value2 in gpu_priority_order else len(gpu_priority_order)
        if idx1 < idx2: return 'phone1'
        elif idx1 > idx2: return 'phone2'
        return None
    
    # Обработка числовых значений
    if rule == "numeric":
        num1 = try_parse_number(value1)
        num2 = try_parse_number(value2)
        if num1 is not None and num2 is not None:
            if num1 > num2: return 'phone1'
            elif num1 < num2: return 'phone2'
        return None
    
    # Обработка обратных числовых значений (меньше = лучше)
    if rule == "numeric_reverse":
        num1 = try_parse_number(value1)
        num2 = try_parse_number(value2)
        if num1 is not None and num2 is not None:
            if num1 < num2: return 'phone1'
            elif num1 > num2: return 'phone2'
        return None
    
    # Обработка булевых значений
    if rule == "boolean":
        true_values = ['да', 'yes', 'есть', '+', 'е', 'y', 'true', 'supported', 'присутствует']
        false_values = ['нет', 'no', 'отсутствует', '-', 'н', 'n', 'false', 'unsupported', 'не поддерживается']
        val1 = str(value1).strip().lower()
        val2 = str(value2).strip().lower()
        if val1 in true_values and val2 in false_values: return 'phone1'
        elif val1 in false_values and val2 in true_values: return 'phone2'
        return None
    
    return None

def compare_two_phones(phone1, phone2):
    """Сравнение двух телефонов"""
    # Обогащение данных
    phone1 = enrich_phone_data(phone1)
    phone2 = enrich_phone_data(phone2)
    
    ignore_fields = ['_id', 'ID', 'image_url']
    phone1_clean = {k: v for k, v in phone1.items() if k not in ignore_fields}
    phone2_clean = {k: v for k, v in phone2.items() if k not in ignore_fields}
    
    all_keys = set(phone1_clean.keys()) | set(phone2_clean.keys())
    categories = defaultdict(list)
    
    # Группировка характеристик по категориям
    for key in all_keys:
        category_name = "Дополнительно"
        for cat, fields in SPEC_CATEGORIES.items():
            if key in fields:
                category_name = cat
                break
        categories[category_name].append(key)
    
    ordered_categories = []
    for cat in SPEC_CATEGORIES.keys():
        if cat in categories: ordered_categories.append(cat)
    if "Дополнительно" in categories: ordered_categories.append("Дополнительно")
    
    comparison = []
    overall_scores = {'phone1': 0, 'phone2': 0}
    category_scores = defaultdict(lambda: {'phone1': 0, 'phone2': 0})

    for category in ordered_categories:
        specs_list = []
        for key in categories[category]:
            val1 = phone1_clean.get(key, "N/A")
            val2 = phone2_clean.get(key, "N/A")
            
            rule = None
            for rule_type, fields in SPEC_RULES.items():
                if key in fields: rule = rule_type
            
            winner = None
            weight = WEIGHTS.get(key, 1.0)
            
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
        
        # Расчет процентов побед для категории
        total_cat = category_scores[category]['phone1'] + category_scores[category]['phone2']
        cat_percent_phone1 = round(category_scores[category]['phone1'] / total_cat * 100, 1) if total_cat > 0 else 0
        cat_percent_phone2 = round(category_scores[category]['phone2'] / total_cat * 100, 1) if total_cat > 0 else 0
        
        comparison.append({
            'category': category,
            'specs': specs_list,
            'category_score_phone1': category_scores[category]['phone1'],
            'category_score_phone2': category_scores[category]['phone2'],
            'category_percent_phone1': cat_percent_phone1,
            'category_percent_phone2': cat_percent_phone2,
        })
    
    # Расчет общего результата
    total_score = overall_scores['phone1'] + overall_scores['phone2']
    
    if total_score > 0:
        percent_phone1 = round(overall_scores['phone1'] / total_score * 100, 1)
        percent_phone2 = round(overall_scores['phone2'] / total_score * 100, 1)
        advantage_percent = round(abs(percent_phone1 - percent_phone2), 1)
    else:
        percent_phone1 = percent_phone2 = 50.0
        advantage_percent = 0.0
    
    overall_winner = None
    if overall_scores['phone1'] > overall_scores['phone2']: overall_winner = 'phone1'
    elif overall_scores['phone1'] < overall_scores['phone2']: overall_winner = 'phone2'
    
    return {
        'phone1': phone1,
        'phone2': phone2,
        'comparison': comparison,
        'overall_winner': overall_winner,
        'total_score_phone1': overall_scores['phone1'],
        'total_score_phone2': overall_scores['phone2'],
        'percent_phone1': percent_phone1,
        'percent_phone2': percent_phone2,
        'advantage_percent': advantage_percent,
        'total_comparable_specs': total_score
    }

def generate_image_path(brand, model):
    """Генерирует путь к изображению телефона"""
    brand_normalized = brand.lower().replace(' ', '_').replace('-', '_')
    model_normalized = model.lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('\\', '_')
    return f"/static/img/phones/{brand_normalized}/{model_normalized}.jpg"
