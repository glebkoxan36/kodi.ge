import re
from bson import ObjectId
from datetime import datetime
from db import client, comparisons_collection

# Балловая система для характеристик
SCORE_SYSTEM = {
    'Процессор': 5,
    'GPU': 5,
    'ОЗУ (ГБ)': 4,
    'ПЗУ (ГБ)': 3,
    'Оценка AnTuTu': 3,
    'Geekbench (одиночное ядро)': 3,
    'Geekbench (многоядерное)': 3,
    'Основная камера (Мп)': 1,
    'Емкость батареи (mAh)': 2,
    'Время работы от батареи (ч)': 2
}

def extract_numeric_value(value):
    """Извлекает числовое значение из строки"""
    if isinstance(value, (int, float)):
        return value
        
    # Ищем числа в строке (включая десятичные)
    numbers = re.findall(r'\d+\.?\d*', str(value))
    if numbers:
        return float(numbers[0])
    return 0

def calculate_score(phone_specs):
    """Рассчитывает баллы для телефона на основе характеристик"""
    score = 0
    for spec, weight in SCORE_SYSTEM.items():
        value = phone_specs.get(spec, '')
        num_value = extract_numeric_value(value)
        score += num_value * weight
    return round(score, 2)

def compare_phones(phone1_specs, phone2_specs):
    """Сравнивает два телефона и возвращает результаты"""
    # Рассчитываем баллы
    score1 = calculate_score(phone1_specs)
    score2 = calculate_score(phone2_specs)
    
    # Определяем победителя
    winner = 0
    if score1 > score2:
        winner = 1
    elif score2 > score1:
        winner = 2
    
    # Сравнение по отдельным характеристикам
    comparison_details = []
    for spec, weight in SCORE_SYSTEM.items():
        value1 = phone1_specs.get(spec, '-')
        value2 = phone2_specs.get(spec, '-')
        
        num1 = extract_numeric_value(value1)
        num2 = extract_numeric_value(value2)
        
        # Определяем преимущество
        advantage = 0
        if num1 > num2:
            advantage = 1
        elif num2 > num1:
            advantage = 2
        
        comparison_details.append({
            'spec': spec,
            'value1': value1,
            'value2': value2,
            'advantage': advantage
        })
    
    return {
        'score1': score1,
        'score2': score2,
        'winner': winner,
        'details': comparison_details,
        'timestamp': datetime.utcnow()
    }

def save_comparison(user_id, phone1_id, phone2_id, result):
    """Сохраняет результаты сравнения в базу данных"""
    if not client:
        return None
    
    comparison_data = {
        'user_id': ObjectId(user_id) if user_id else None,
        'phone1_id': ObjectId(phone1_id),
        'phone2_id': ObjectId(phone2_id),
        'score1': result['score1'],
        'score2': result['score2'],
        'winner': result['winner'],
        'details': result['details'],
        'timestamp': result['timestamp']
    }
    
    inserted = comparisons_collection.insert_one(comparison_data)
    return inserted.inserted_id
