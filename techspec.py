import os
import requests
import re
from flask import jsonify

# Используем значения из примера curl
TECHSPECS_API_ID = os.getenv('TECHSPECS_API_ID', '68625f85b363e86de2ae7e0a')
TECHSPECS_API_KEY = os.getenv('TECHSPECS_API_KEY', '35a39ff6-545c-44e7-9861-f0c3eed6dcb4')
BASE_URL = "https://api.techspecs.io/v5"

# Заголовки в нижнем регистре как в примере curl
headers = {
    "x-api-id": TECHSPECS_API_ID,
    "x-api-key": TECHSPECS_API_KEY,
    "accept": "application/json"
}

def search_phones(query):
    """Поиск телефонов через Techspecs API"""
    params = {'query': query, 'category': 'smartphones'}
    try:
        print(f"Sending request to Techspecs API: {BASE_URL}/products/search")
        response = requests.get(
            f"{BASE_URL}/products/search",
            headers=headers,
            params=params,
            timeout=15
        )
        
        # Отладочная информация
        print(f"Response status: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        results = data.get('data', [])
        
        # Форматируем результаты для фронтенда
        formatted = []
        for item in results[:10]:  # Ограничиваем 10 результатами
            product = item.get('Product', {})
            release_date = item.get('Release Date', '')
            
            # Извлекаем год выпуска из даты
            release_year = ''
            if release_date:
                match = re.search(r'\d{4}', release_date)
                if match:
                    release_year = match.group(0)
            
            formatted.append({
                '_id': product.get('id'),
                'brand': product.get('Brand', ''),
                'model': product.get('Model', ''),
                'image_url': product.get('Thumbnail', ''),
                'release_year': release_year,
                'specs': {}  # Спецификации будем получать через отдельный запрос
            })
        
        print(f"Found {len(formatted)} results")
        return formatted
    except Exception as e:
        print(f"Techspecs search error: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Error response text: {e.response.text}")
            try:
                error_data = e.response.json()
                print(f"Error details: {error_data}")
            except:
                pass
        return []

def get_phone_details(phone_id):
    """Получение детальной информации о телефоне"""
    try:
        print(f"Fetching details for phone: {phone_id}")
        response = requests.get(
            f"{BASE_URL}/products/{phone_id}",
            headers=headers,
            timeout=15
        )
        
        # Отладочная информация
        print(f"Details response status: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        phone = data.get('data', {})
        
        # Извлекаем год выпуска
        release_year = ''
        release_date = phone.get('Key Aspects', {}).get('Release Date', '')
        if not release_date:
            # Если в Key Aspects нет, проверяем корневой уровень
            release_date = phone.get('Release Date', '')
        if release_date:
            match = re.search(r'\d{4}', release_date)
            if match:
                release_year = match.group(0)
        
        # Обработка изображения
        image_url = ''
        thumbnail = phone.get('Thumbnail', {})
        if thumbnail:
            # Пробуем получить первое доступное изображение
            image_url = thumbnail.get('Image_1') or thumbnail.get('Image_2') or ''
        
        # Если нет в Thumbnail, пробуем старые форматы
        if not image_url:
            if 'Product' in phone and 'Thumbnail' in phone['Product']:
                image_url = phone['Product']['Thumbnail']
            else:
                image_url = phone.get('thumbnail', '')
        
        # Бренд и модель
        brand = phone.get('Product', {}).get('Brand', '')
        model = phone.get('Product', {}).get('Model', '')
        
        # Если не найдены в Product, проверяем корневой уровень
        if not brand:
            brand = phone.get('brand', '')
        if not model:
            model = phone.get('model', '')
        
        return {
            'id': phone_id,
            'brand': brand,
            'model': model,
            'image_url': image_url,
            'release_year': release_year,
            'specs': extract_key_specs(phone)
        }
    except Exception as e:
        print(f"Techspecs details error: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Error response text: {e.response.text}")
        return None

def extract_key_specs(phone_data):
    """Извлекаем ключевые характеристики из данных API с новой структурой"""
    specs = {}
    
    # Дисплей
    display = phone_data.get('Display', {})
    if display:
        specs['display'] = {
            'size': display.get('Diagonal', ''),
            'resolution': display.get('Resolution (H x W)', ''),
            'type': display.get('Type', ''),
            'refresh_rate': display.get('Refresh Rate', '')
        }
    
    # Камеры
    camera = phone_data.get('Camera', {})
    if camera:
        # Основная камера
        back_camera = camera.get('Back Camera', {})
        # Вторая задняя камера (если есть)
        back_camera2 = camera.get('Back Camera II', {})
        # Фронтальная камера
        front_camera = camera.get('Front Camera', {})
        
        # Форматируем информацию о камерах
        main_cam_res = back_camera.get('Resolution', '')
        if back_camera2 and back_camera2.get('Resolution'):
            main_cam_res += f", {back_camera2['Resolution']}"
        
        # Если не нашли разрешение, пробуем Key Aspects
        if not main_cam_res:
            key_aspects = phone_data.get('Key Aspects', {})
            if key_aspects:
                cam_desc = key_aspects.get('Camera', '')
                # Пробуем извлечь разрешение из описания
                match = re.search(r'(\d+\.?\d* MP)', cam_desc)
                if match:
                    main_cam_res = match.group(1)
        
        specs['camera'] = {
            'main': main_cam_res,
            'front': front_camera.get('Resolution', '')
        }
    
    # Процессор
    processor = phone_data.get('Inside', {}).get('Processor', {})
    if processor:
        specs['processor'] = {
            'name': processor.get('CPU', ''),
            'cores': processor.get('Number of Cores', '')  # Может отсутствовать
        }
    else:
        # Пробуем взять из Key Aspects
        key_aspects = phone_data.get('Key Aspects', {})
        if key_aspects:
            proc_desc = key_aspects.get('Processor', '')
            if proc_desc:
                specs['processor'] = {
                    'name': proc_desc,
                    'cores': ''  # не знаем количество ядер
                }
    
    # Память
    ram = phone_data.get('Inside', {}).get('RAM', {})
    storage = phone_data.get('Inside', {}).get('Storage', {})
    if ram or storage:
        ram_capacity = ram.get('Capacity', '') if ram else ''
        storage_capacity = storage.get('Capacity', '') if storage else ''
        specs['storage'] = {
            'ram': ram_capacity,
            'internal': storage_capacity
        }
    else:
        # Пробуем взять из Key Aspects
        key_aspects = phone_data.get('Key Aspects', {})
        if key_aspects:
            ram_desc = key_aspects.get('RAM', '')
            storage_desc = key_aspects.get('Storage', '')
            if ram_desc or storage_desc:
                specs['storage'] = {
                    'ram': ram_desc,
                    'internal': storage_desc
                }
    
    # Батарея
    battery = phone_data.get('Inside', {}).get('Battery', {})
    if battery:
        capacity = battery.get('Capacity', '')
        charging = battery.get('Charging Power', '')
        specs['battery'] = {
            'capacity': capacity,
            'charging': charging
        }
    else:
        # Пробуем взять из Key Aspects
        key_aspects = phone_data.get('Key Aspects', {})
        if key_aspects:
            battery_desc = key_aspects.get('Battery', '')
            if battery_desc:
                # Пробуем извлечь емкость
                match = re.search(r'(\d+ mAh)', battery_desc)
                if match:
                    capacity = match.group(1)
                specs['battery'] = {
                    'capacity': capacity or battery_desc,
                    'charging': ''
                }
    
    # Дополнительно: ОС и сеть
    software = phone_data.get('Inside', {}).get('Software', {})
    cellular = phone_data.get('Inside', {}).get('Cellular', {})
    
    os_name = software.get('OS', '') if software else ''
    network_gen = cellular.get('Generation', '') if cellular else ''
    
    # Если не нашли, пробуем Key Aspects
    if not os_name:
        key_aspects = phone_data.get('Key Aspects', {})
        if key_aspects:
            os_name = key_aspects.get('OS', '')
    
    if not network_gen:
        key_aspects = phone_data.get('Key Aspects', {})
        if key_aspects:
            # В Key Aspects может быть поле "Wireless & Cellular"
            wireless = key_aspects.get('Wireless & Cellular', '')
            # Пробуем извлечь поколение сети
            match = re.search(r'(\d+G)', wireless)
            if match:
                network_gen = match.group(1)
    
    specs['os'] = os_name
    specs['network'] = network_gen
    
    return specs

def compare_phones(phone1_id, phone2_id):
    """Сравнение двух телефонов"""
    print(f"Comparing phones: {phone1_id} vs {phone2_id}")
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
        
        # Собираем все ключи характеристик для категории
        keys = set()
        if category in phone1['specs']:
            keys.update(phone1['specs'][category].keys())
        if category in phone2['specs']:
            keys.update(phone2['specs'][category].keys())
        
        for spec_name in keys:
            val1 = phone1['specs'].get(category, {}).get(spec_name, 'N/A')
            val2 = phone2['specs'].get(category, {}).get(spec_name, 'N/A')
            
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
            except Exception as e:
                print(f"Error comparing values: {str(e)}")
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
