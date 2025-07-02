import re
from collections import defaultdict

SPEC_CATEGORIES = {
    "Общие характеристики": [
        "Бренд", "Модель", "Год выпуска", "Квартал выпуска", "ОС", "Версия ОС", 
        "Оболочка ОС", "Политика обновлений", "Последний патч безопасности"
    ],
    "Дисплей": [
        "Размер дисплея (дюймы)", "Разрешение дисплея", "Тип дисплея", 
        "Частота обновления (Гц)", "Пиковая яркость (нит)", "Поддержка HDR",
        "Защитное стекло", "Соотношение экран/корпус", "Плотность пикселей (PPI)"
    ],
    "Производительность": [
        "Процессор", "Архитектура CPU", "GPU", "Архитектура GPU", "NPU", "ISP", 
        "Модем", "ОЗУ (ГБ)", "Тип ОЗУ", "Частота ОЗУ (МГц)", "ПЗУ (ГБ)", 
        "Тип ПЗУ", "Скорость ПЗУ", "Система охлаждения", "Площадь охлаждения (мм²)",
        "Оценка AnTuTu", "Geekbench (одиночное ядро)", "Geekbench (многоядерное)"
    ],
    "Камера": [
        "Основная камера (Мп)", "Сверхширокоугольная камера (Мп)", "Телефото 1 (Мп)", 
        "Телефото 2 (Мп)", "Фронтальная камера (Мп)", "Размер сенсора (основной)",
        "Размер пикселя (основной)", "Возможности зума", "Видеозапись", 
        "Замедленная съемка", "Функции камеры"
    ],
    "Батарея": [
        "Емкость батареи (mAh)", "Тип батареи", "Быстрая зарядка", 
        "Беспроводная зарядка", "Обратная беспроводная зарядка", "Интерфейс зарядки",
        "Время работы от батареи (ч)", "Потребление в режиме ожидания", "Пиковая мощность"
    ],
    "Дизайн": [
        "Вес (г)", "Габариты (мм)", "Материал корпуса", "Защита от воды", 
        "Защита от пыли", "Сертификат защиты", "Материал рамки",
        "Материал задней панели", "Цвета"
    ],
    "Связь": [
        "Поддержка 5G", "Диапазоны 5G", "Поддержка mmWave", "Слоты SIM", "Тип SIM",
        "Wi-Fi", "Особенности Wi-Fi", "Bluetooth", "Кодеки Bluetooth", "NFC", 
        "ИК-порт", "Версия USB", "GPS", "Спутниковая связь"
    ],
    "Мультимедиа": [
        "Динамики", "Аудионастройка", "Микрофоны", "Аудиоразъем", "Пространственный звук"
    ],
    "Безопасность": [
        "Сканер отпечатков", "Разблокировка по лицу"
    ],
    "Датчики": [
        "Акселерометр", "Гироскоп", "Датчик приближения", "Компас", "Барометр",
        "Датчик освещенности", "Датчик Холла", "LiDAR", "Термометр", "Датчик SpO2"
    ],
    "Дополнительные функции": [
        "Поддержка стилуса", "Тип стилуса", "Режим рабочего стола", "Поддержка VR",
        "ИИ-функции", "Игровые функции", "Безопасный чип"
    ],
    "Комплектация": [
        "Зарядное устройство в комплекте", "Тип кабеля", "Адаптер в комплекте",
        "Наушники в комплекте", "Чехол в комплекте"
    ],
    "Экология": [
        "Переработанные материалы", "Упаковка", "Экосертификаты", 
        "Индекс ремонтопригодности", "Циклы батареи"
    ],
    "Безопасность (SAR)": [
        "SAR (голова)", "SAR (тело)"
    ],
    "Цена и гарантия": [
        "Стартовая цена (руб)", "Текущая цена (руб)", "Доступность", "Гарантия (мес)"
    ]
}

SPEC_RULES = {
    "numeric": [
        "Год выпуска", "Размер дисплея (дюймы)", "Плотность пикселей (PPI)", 
        "Частота обновления (Гц)", "Пиковая яркость (нит)", "ОЗУ (ГБ)", 
        "Частота ОЗУ (МГц)", "ПЗУ (ГБ)", "Скорость ПЗУ", "Площадь охлаждения (мм²)", 
        "Оценка AnTuTu", "Geekbench (одиночное ядро)", "Geekbench (многоядерное)", 
        "Основная камера (Мп)", "Сверхширокоугольная камера (Мп)", "Телефото 1 (Мп)", 
        "Телефото 2 (Мп)", "Фронтальная камера (Мп)", "Возможности зума", 
        "Емкость батареи (mAh)", "Быстрая зарядка", "Беспроводная зарядка", 
        "Обратная беспроводная зарядка", "Время работы от батареи (ч)", 
        "Гарантия (мес)"
    ],
    "numeric_reverse": [
        "Вес (г)", "Потребление в режиме ожидания", "Пиковая мощность", 
        "SAR (голова)", "SAR (тело)"
    ],
    "boolean": [
        "Поддержка HDR", "Поддержка 5G", "Поддержка mmWave", "NFC", "ИК-порт", 
        "Спутниковая связь", "Пространственный звук", "Разблокировка по лицу", 
        "Поддержка стилуса", "Режим рабочего стола", "Поддержка VR", 
        "Зарядное устройство в комплекте", "Наушники в комплекте", 
        "Чехол в комплекте", "Переработанные материалы"
    ]
}

def try_parse_number(value):
    if isinstance(value, (int, float)):
        return value
    try:
        cleaned = re.sub(r'[^\d.,-]', '', value)
        cleaned = cleaned.replace(',', '.')
        return float(cleaned)
    except:
        return None

def compare_values(rule, value1, value2):
    if rule == "numeric":
        num1 = try_parse_number(value1)
        num2 = try_parse_number(value2)
        if num1 is not None and num2 is not None:
            if num1 > num2:
                return 'phone1'
            elif num1 < num2:
                return 'phone2'
        return None
    elif rule == "numeric_reverse":
        num1 = try_parse_number(value1)
        num2 = try_parse_number(value2)
        if num1 is not None and num2 is not None:
            if num1 < num2:
                return 'phone1'
            elif num1 > num2:
                return 'phone2'
        return None
    elif rule == "boolean":
        true_values = ['да', 'yes', 'есть', '+', 'е', 'y', 'true', 'supported', 'есть', 'присутствует']
        false_values = ['нет', 'no', 'отсутствует', '-', 'н', 'n', 'false', 'unsupported', 'не поддерживается']
        val1 = str(value1).strip().lower()
        val2 = str(value2).strip().lower()
        if val1 in true_values and val2 in false_values:
            return 'phone1'
        elif val1 in false_values and val2 in true_values:
            return 'phone2'
        return None
    return None

def compare_two_phones(phone1, phone2):
    ignore_fields = ['_id', 'ID', 'image_url']
    phone1_clean = {k: v for k, v in phone1.items() if k not in ignore_fields}
    phone2_clean = {k: v for k, v in phone2.items() if k not in ignore_fields}
    
    all_keys = set(phone1_clean.keys()) | set(phone2_clean.keys())
    categories = defaultdict(list)
    
    for key in all_keys:
        category_name = "Другие"
        for cat, fields in SPEC_CATEGORIES.items():
            if key in fields:
                category_name = cat
                break
        categories[category_name].append(key)
    
    ordered_categories = []
    for cat in SPEC_CATEGORIES.keys():
        if cat in categories:
            ordered_categories.append(cat)
    if "Другие" in categories and categories["Другие"]:
        ordered_categories.append("Другие")
    
    comparison = []
    overall_scores = {'phone1': 0, 'phone2': 0}

    for category in ordered_categories:
        specs_list = []
        for key in categories[category]:
            val1 = phone1_clean.get(key, "N/A")
            val2 = phone2_clean.get(key, "N/A")
            
            rule = None
            for rule_type, fields in SPEC_RULES.items():
                if key in fields:
                    rule = rule_type
                    break
            
            winner = None
            if rule:
                winner = compare_values(rule, val1, val2)
                if winner:
                    overall_scores[winner] += 1

            specs_list.append({
                'name': key,
                'phone1_value': val1,
                'phone2_value': val2,
                'winner': winner
            })
        
        comparison.append({
            'category': category,
            'specs': specs_list
        })
    
    overall_winner = None
    if overall_scores['phone1'] > overall_scores['phone2']:
        overall_winner = 'phone1'
    elif overall_scores['phone1'] < overall_scores['phone2']:
        overall_winner = 'phone2'
    
    return {
        'phone1': phone1,
        'phone2': phone2,
        'comparison': comparison,
        'overall_winner': overall_winner
    }

def generate_image_path(brand, model):
    """Генерирует путь к изображению телефона"""
    brand_normalized = brand.lower().replace(' ', '_').replace('-', '_')
    model_normalized = model.lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('\\', '_')
    return f"/static/img/phones/{brand_normalized}/{model_normalized}.jpg"
