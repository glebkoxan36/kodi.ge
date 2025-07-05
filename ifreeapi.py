import os
import re
import requests
import logging
import time
import threading
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_URL = os.getenv('API_URL', "https://api.ifreeicloud.co.uk")
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')

# Семафор для ограничения одновременных запросов
REQUEST_SEMAPHORE = threading.Semaphore(3)

SERVICE_TYPES = {
    # Apple сервисы
    'free': 0,
    'fmi': 4,
    'blacklist': 9,
    'sim_lock': 255,
    'activation': 247,
    'carrier': 204,
    'mdm': 204,
    'paid': 205,
    'premium': 242,
    'full': 999,
    'macbook': 349,
    
    # Android сервисы
    'xiaomi': 196,
    'samsung_v1': 11,
    'samsung_v2': 190,
    'samsung_knox': 302,
    'oppo': 317,
    'operius': 233,
    'motorola': 246,
    'ig': 160,
    'itel_tecno_infinix': 307,
    'huawei_v1': 158,
    'huawei_v2': 283,
    'google_pixel': 209
}

def validate_imei(imei: str) -> bool:
    """Проверяет валидность IMEI (15 цифр)"""
    return bool(re.fullmatch(r"\d{15}", imei))

def parse_universal_response(response_content: str) -> dict:
    """Универсальный парсер с приоритетом на структурированные данные"""
    result = {}
    
    # Попытка парсинга JSON
    try:
        data = json.loads(response_content)
        
        # Приоритет 1: объект 'object' со структурированными данными
        if 'object' in data and isinstance(data['object'], dict):
            for key, value in data['object'].items():
                # Нормализуем ключ
                normalized_key = key.strip().lower().replace(' ', '_')
                result[normalized_key] = value
        
        # Приоритет 2: строка 'response' с текстовыми данными
        if 'response' in data and isinstance(data['response'], str):
            # Парсим строку response
            lines = data['response'].splitlines()
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    # Добавляем только если ключ еще не существует
                    if key not in result:
                        result[key] = value
        
        # Приоритет 3: корневые поля
        for key in ['model', 'model_name', 'modelName', 'brand', 'manufacturer', 
                    'imei', 'imei_number', 'status', 'success', 
                    'sim_lock', 'blacklist_status', 'fmi_status', 'activation_status',
                    'carrier', 'warranty_status', 'product_type']:
            if key in data and key not in result:
                result[key] = data[key]
        
        # Добавляем технические поля, если они еще не добавлены
        if 'status' not in result and 'status' in data:
            result['status'] = data['status']
        if 'success' not in result and 'success' in data:
            result['success'] = data['success']
            
        return result
        
    except json.JSONDecodeError:
        # Если это не JSON, обрабатываем как текст
        pass
    except Exception as e:
        logging.error(f"JSON parsing error: {str(e)}")
    
    # Обработка текстового формата
    try:
        lines = response_content.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Пропускаем технические строки
            if line.lower().startswith('object') or line.lower().startswith('success'):
                continue
                
            # Обрабатываем строки с разделителем
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                result[key] = value
            elif '\t' in line:
                key, value = line.split('\t', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                result[key] = value
    except Exception as e:
        logging.error(f"Text parsing error: {str(e)}")
        result['error'] = f'Text parsing error: {str(e)}'
    
    # Определение типа устройства
    brand = result.get('brand', '').lower()
    if 'apple' in brand or 'iphone' in brand or 'ipad' in brand:
        result['device_type'] = 'Apple'
    elif 'samsung' in brand or 'xiaomi' in brand or 'huawei' in brand:
        result['device_type'] = 'Android'
    elif 'model' in result:
        model = result['model'].lower()
        if 'sm-' in model or 'galaxy' in model:
            result['device_type'] = 'Android'
        elif 'iphone' in model or 'ipad' in model:
            result['device_type'] = 'Apple'
    else:
        result['device_type'] = 'Unknown'
    
    return result

def perform_api_check(imei: str, service_type: str) -> dict:
    """Выполняет проверку IMEI через внешний API"""
    try:
        with REQUEST_SEMAPHORE:
            if service_type not in SERVICE_TYPES:
                return {'error': f'Unknown service type: {service_type}'}
            
            service_code = SERVICE_TYPES[service_type]
            data = {
                "service": service_code,
                "imei": imei,
                "key": API_KEY
            }
            
            # Задержка перед запросом
            time.sleep(1)
            
            # Выполняем запрос
            response = requests.post(API_URL, data=data, timeout=30)
            
            # Задержка после запрос
            time.sleep(0.5)
            
            # Обрабатываем ответ
            if response.status_code != 200:
                return {
                    'error': f'Server error: {response.status_code}',
                    'status_code': response.status_code,
                    'raw_response': response.text[:500] + '...' if len(response.text) > 500 else response.text
                }
            
            # Логируем сырой ответ для отладки
            logging.info(f"Raw API response for IMEI {imei}, service {service_type}")
            
            # Парсим ответ
            parsed_data = parse_universal_response(response.text)
            
            # Добавляем IMEI для отслеживания
            parsed_data['imei'] = imei
            
            # Добавляем сырой ответ для диагностики
            parsed_data['raw_response'] = response.text[:1000] + '...' if len(response.text) > 1000 else response.text
            
            return parsed_data
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

# Для обратной совместимости
parse_free_html = parse_universal_response
