import os
import re
import requests
import logging
import time
import threading
from bs4 import BeautifulSoup
import json  # Добавляем импорт json

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
    """Универсальный парсер с фильтрацией ключей"""
    result = {}
    
    # Пытаемся распарсить как JSON
    try:
        data = json.loads(response_content)
        if isinstance(data, dict):
            # Фильтруем только нужные ключи
            allowed_keys = {
                'model', 'modelName', 'brand', 'manufacturer', 'imei', 
                'status', 'success', 'sim_lock', 'blacklist_status',
                'fmi_status', 'activation_status', 'carrier', 'warranty_status'
            }
            
            for key, value in data.items():
                # Нормализуем ключ
                normalized_key = key.strip().lower().replace(' ', '_')
                
                # Фильтруем ключи
                if normalized_key in allowed_keys:
                    result[normalized_key] = value
                # Специальная обработка для вложенных объектов
                elif key == 'response' and isinstance(value, dict):
                    for k, v in value.items():
                        nk = k.strip().lower().replace(' ', '_')
                        if nk in allowed_keys:
                            result[nk] = v
            
            return result
    except:
        pass
    
    # Если не JSON - обрабатываем как текст
    try:
        lines = response_content.splitlines()
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Фильтруем ключи
                if key in allowed_keys:
                    result[key] = value
    except:
        pass
    
    # Определение типа устройства по бренду
    brand = result.get('brand', '').lower()
    if 'apple' in brand or 'iphone' in brand or 'ipad' in brand:
        result['device_type'] = 'Apple'
    elif brand:
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
            data = {"service": service_code, "imei": imei, "key": API_KEY}
            
            time.sleep(1)  # Задержка перед запросом
            response = requests.post(API_URL, data=data, timeout=30)
            time.sleep(0.5)  # Задержка после запроса
            
            if response.status_code != 200:
                return {
                    'error': f'Server error: {response.status_code}',
                    'status_code': response.status_code
                }
            
            return parse_universal_response(response.text)
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

# Для обратной совместимости
parse_free_html = parse_universal_response
