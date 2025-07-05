import os
import re
import requests
import logging
import time
import threading
import json
from bs4 import BeautifulSoup

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
    """Универсальный парсер с улучшенной обработкой данных"""
    result = {}
    
    # Список разрешенных ключей
    allowed_keys = {
        'model', 'modelname', 'brand', 'manufacturer', 'imei', 
        'status', 'success', 'sim_lock', 'blacklist_status',
        'fmi_status', 'activation_status', 'carrier', 'warranty_status',
        'device_type', 'activation_status', 'carrier_name', 'product_type',
        'device_name', 'serial_number', 'purchase_date', 'support_status',
        'locked_status', 'find_my_iphone', 'sim_status', 'network_status'
    }
    
    # Пытаемся распарсить как JSON
    try:
        data = json.loads(response_content)
        
        # Если это словарь, извлекаем данные
        if isinstance(data, dict):
            # Ищем вложенные данные в объекте 'response'
            if 'response' in data and isinstance(data['response'], dict):
                for key, value in data['response'].items():
                    normalized_key = key.strip().lower().replace(' ', '_')
                    if normalized_key in allowed_keys:
                        result[normalized_key] = value
            
            # Также обрабатываем корневой уровень
            for key, value in data.items():
                normalized_key = key.strip().lower().replace(' ', '_')
                if normalized_key in allowed_keys and normalized_key != 'response':
                    result[normalized_key] = value
    except:
        # Если не JSON - обрабатываем как текст
        try:
            lines = response_content.splitlines()
            current_key = None
            
            for line in lines:
                # Пропускаем пустые строки
                line = line.strip()
                if not line:
                    continue
                    
                # Обрабатываем строки с разделителем табуляцией
                if '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        if key in allowed_keys:
                            result[key] = value
                            current_key = key
                
                # Обрабатываем строки с разделителем двоеточием
                elif ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        if key in allowed_keys:
                            result[key] = value
                            current_key = key
                
                # Обрабатываем многострочные значения
                elif current_key:
                    result[current_key] += " " + line.strip()
        except Exception as e:
            logging.error(f"Error parsing response: {str(e)}")
            result['raw_response'] = response_content[:1000]  # Сохраняем часть ответа для диагностики
    
    # Если после обработки результат пустой, сохраняем сырой ответ
    if not result:
        result['raw_response'] = response_content[:1000] + '...' if len(response_content) > 1000 else response_content
    
    # Определение типа устройства по бренду
    brand = result.get('brand', '').lower()
    if 'apple' in brand or 'iphone' in brand or 'ipad' in brand:
        result['device_type'] = 'Apple'
    elif brand:
        result['device_type'] = 'Android'
    else:
        # Попробуем определить по другим признакам
        if 'model' in result and ('iphone' in result['model'].lower() or 'ipad' in result['model'].lower()):
            result['device_type'] = 'Apple'
        elif 'model' in result and ('galaxy' in result['model'].lower() or 'pixel' in result['model'].lower()):
            result['device_type'] = 'Android'
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
            
            # Задержка после запроса
            time.sleep(0.5)
            
            # Обрабатываем ответ
            if response.status_code != 200:
                return {
                    'error': f'Server error: {response.status_code}',
                    'status_code': response.status_code,
                    'raw_response': response.text[:2000] + '...' if len(response.text) > 2000 else response.text
                }
            
            # Логируем сырой ответ для отладки
            logging.debug(f"Raw API response for IMEI {imei}, service {service_type}: {response.text[:500]}")
            
            return parse_universal_response(response.text)
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

# Для обратной совместимости
parse_free_html = parse_universal_response
