import os
import requests
import re
from flask import jsonify

TECHSPECS_API_ID = os.getenv('TECHSPECS_API_ID', '68612672b363e86de2ae7d47')
TECHSPECS_API_KEY = os.getenv('TECHSPECS_API_KEY', 'af00bda7-3f9c-4922-83e9-31985640187f')
BASE_URL = "https://api.techspecs.io/v5"

headers = {
    "X-API-ID": TECHSPECS_API_ID,
    "X-API-KEY": TECHSPECS_API_KEY,
    "Accept": "application/json"
}

def search_phones(query):
    """Поиск телефонов через Techspecs API"""
    params = {'query': query, 'category': 'smartphones'}
    try:
        response = requests.get(
            f"{BASE_URL}/products/search",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        results = response.json().get('data', [])
        
        # Форматируем результаты для фронтенда
        formatted = []
        for phone in results[:10]:  # Ограничиваем 10 результатами
            # Извлекаем год выпуска из даты
            release_year = ''
            if phone.get('date') and phone['date'].get('released'):
                match = re.search(r'\d{4}', phone['date']['released'])
                if match:
                    release_year = match.group(0)
            
            formatted.append({
                '_id': phone.get('id'),
                'brand': phone.get('brand'),
                'model': phone.get('model'),
                'image_url': phone.get('thumbnail', ''),
                'release_year': release_year,
                'specs': extract_key_specs(phone)
            })
        return formatted
    except Exception as e:
        print(f"Techspecs search error: {str(e)}")
        return []

def get_phone_details(phone_id):
    """Получение детальной информации о телефоне"""
    try:
        response = requests.get(
            f"{BASE_URL}/products/{phone_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        phone = response.json().get('data', {})
        
        # Извлекаем год выпуска из даты
        release_year = ''
        if phone.get('date') and phone['date'].get('released'):
            match = re.search(r'\d{4}', phone['date']['released'])
            if match:
                release_year = match.group(0)
        
        return {
            'id': phone_id,
            'brand': phone.get('brand'),
            'model': phone.get('model'),
            'image_url': phone.get('thumbnail', ''),
            'release_year': release_year,
            'specs': extract_key_specs(phone)
        }
    except Exception as e:
        print(f"Techspecs details error: {str(e)}")
        return None

def extract_key_specs(phone_data):
    """Извлекаем ключевые характеристики из данных API"""
    specs = {}
    
    # Дисплей
    display = phone_data.get('display', {})
    if display:
        specs['display'] = {
            'size': display.get('diagonal', ''),
            'resolution': display.get('resolution_(h_x_w)', ''),
            'type': display.get('type', ''),
            'refresh_rate': display.get('refresh_rate', '')
        }
    
    # Камеры
    camera = phone_data.get('camera', {})
    if camera:
        specs['camera'] = {
            'main': camera.get('back_camera', {}).get('resolution', ''),
            'front': camera.get('front_camera', {}).get('resolution', '')
        }
    
    # Процессор
    processor = phone_data.get('processor', {})
    if processor:
        specs['processor'] = {
            'name': processor.get('cpu', ''),
            'cores': processor.get('number_of_cores', '')
        }
    
    # Память
    storage = phone_data.get('storage', {})
    if storage:
        specs['storage'] = {
            'ram': storage.get('ram', ''),
            'internal': storage.get('capacity', '')
        }
    
    # Батарея
    battery = phone_data.get('battery', {})
    if battery:
        specs['battery'] = {
            'capacity': battery.get('capacity', ''),
            'charging': battery.get('charging_power', '')
        }
    
    # Дополнительно
    specs['os'] = phone_data.get('software', {}).get('os', '')
    specs['network'] = phone_data.get('cellular', {}).get('generation', '')
    
    return specs

def compare_phones(phone1_id, phone2_id):
    """Сравнение двух телефонов"""
    phone1 = get_phone_details(phone1_id)
    phone2 = get_phone_details(phone2_id)
    
    if not phone1 or not phone2:
        return {'error': 'Phone details not found'}
    
    comparison = []
    categories = ['display', 'camera', 'processor', 'storage', 'battery', 'os', 'network']
    
    for category in categories:
        cat_data = {
            'category': category.capitalize(),
            'specs': []
        }
        
        # Сравнение характеристик в категории
        for spec_name in phone1['specs'].get(category, {}).keys():
            val1 = phone1['specs'][category].get(spec_name, 'N/A')
            val2 = phone2['specs'][category].get(spec_name, 'N/A')
            
            winner = None
            try:
                # Для числовых значений (извлекаем числа из строк)
                num1 = extract_number(val1)
                num2 = extract_number(val2)
                
                if num1 is not None and num2 is not None:
                    if num1 > num2:
                        winner = 'phone1'
                    elif num2 > num1:
                        winner = 'phone2'
            except:
                pass
            
            cat_data['specs'].append({
                'name': spec_name.capitalize(),
                'phone1_value': val1,
                'phone2_value': val2,
                'winner': winner
            })
        
        comparison.append(cat_data)
    
    # Определение общего победителя
    overall_winner = None
    phone1_wins = sum(1 for cat in comparison for spec in cat['specs'] if spec['winner'] == 'phone1')
    phone2_wins = sum(1 for cat in comparison for spec in cat['specs'] if spec['winner'] == 'phone2')
    
    if phone1_wins > phone2_wins:
        overall_winner = 'phone1'
    elif phone2_wins > phone1_wins:
        overall_winner = 'phone2'
    
    return {
        'phone1': {
            'id': phone1_id,
            'brand': phone1['brand'],
            'model': phone1['model'],
            'image_url': phone1['image_url']
        },
        'phone2': {
            'id': phone2_id,
            'brand': phone2['brand'],
            'model': phone2['model'],
            'image_url': phone2['image_url']
        },
        'comparison': comparison,
        'overall_winner': overall_winner
    }

def extract_number(value):
    """Извлекает число из строки, если возможно"""
    if isinstance(value, (int, float)):
        return value
    
    if isinstance(value, str):
        # Ищем числа в строке (включая десятичные)
        match = re.search(r'\d+\.?\d*', value)
        if match:
            try:
                return float(match.group())
            except:
                pass
    
    return None
