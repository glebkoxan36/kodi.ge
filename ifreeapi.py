import os
import re
import requests
import logging
import time
import threading
from bs4 import BeautifulSoup
import json

API_URL = os.getenv('API_URL', "https://api.ifreeicloud.co.uk")
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')

# Семафор для ограничения одновременных запросов
REQUEST_SEMAPHORE = threading.Semaphore(3)  # Максимум 3 одновременных запроса

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
    
    # Новые Android сервисы
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
    """Универсальный парсер с расширенной обработкой данных"""
    result = {}
    # Расширенный список ключей, которые мы хотим извлечь
    target_keys = {
        'model', 'model name', 'brand', 'manufacturer', 'imei number',
        'status', 'success', 'sim lock', 'blacklist status', 'fmi status',
        'activation status', 'carrier', 'warranty status', 'device type',
        'product type', 'carrier name', 'network status', 'purchase date',
        'technical support', 'telephone support', 'repairs coverage',
        'replacement coverage', 'estimated expiration date'
    }
    
    # Попробуем обработать как JSON
    try:
        data = json.loads(response_content)
        
        # Если ответ содержит объект 'response', извлекаем из него данные
        if 'response' in data and isinstance(data['response'], dict):
            for key, value in data['response'].items():
                normalized_key = key.strip().lower()
                if normalized_key in target_keys:
                    result[normalized_key.replace(' ', '_')] = value
                    
        # Также обрабатываем корневой уровень
        for key, value in data.items():
            if key.lower() == 'response':
                continue  # Уже обработали
                
            normalized_key = key.strip().lower()
            if normalized_key in target_keys:
                result[normalized_key.replace(' ', '_')] = value
                
        # Если нашли данные, возвращаем их
        if result:
            # Добавляем технические поля, если они есть
            if 'status' not in result and 'Status' in data:
                result['status'] = data['Status']
            if 'success' not in result and 'Success' in data:
                result['success'] = data['Success']
                
            return result
    except Exception as e:
        # В случае ошибки JSON парсинга продолжим обработку как текст
        pass
    
    # Если не JSON или парсинг не удался - обрабатываем как текст
    try:
        # Разбиваем на строки и обрабатываем каждую строку
        lines = response_content.splitlines()
        current_key = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Пропускаем технические строки
            if line.lower().startswith('object') or line.lower().startswith('success'):
                continue
                
            # Обрабатываем строки с разделителем табуляции
            if '\t' in line:
                parts = line.split('\t')
                # Обрабатываем пары ключ-значение
                if len(parts) >= 2:
                    key = parts[0].strip().lower()
                    value = parts[1].strip()
                    
                    if key in target_keys:
                        result[key.replace(' ', '_')] = value
                        current_key = key
                    elif key == 'response':
                        # Обрабатываем вложенные данные в response
                        if ':' in value:
                            sub_parts = value.split(':', 1)
                            if len(sub_parts) == 2:
                                sub_key = sub_parts[0].strip().lower()
                                sub_value = sub_parts[1].strip()
                                if sub_key in target_keys:
                                    result[sub_key.replace(' ', '_')] = sub_value
            # Обрабатываем строки с разделителем двоеточие
            elif ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower()
                    value = parts[1].strip()
                    
                    if key in target_keys:
                        result[key.replace(' ', '_')] = value
                        current_key = key
            # Продолжение предыдущего значения
            elif current_key:
                result[current_key.replace(' ', '_')] += ' ' + line
    except Exception as e:
        # Логируем ошибку, но продолжаем работу
        logging.error(f"Error parsing response: {str(e)}")
        result['error'] = f'პარსინგის შეცდომა: {str(e)}'
    
    # Добавляем технические поля, если они есть
    if 'status' not in result:
        for line in response_content.splitlines():
            if 'status' in line.lower() and ('\t' in line or ':' in line):
                separator = '\t' if '\t' in line else ':'
                parts = line.split(separator, 1)
                if len(parts) > 1:
                    result['status'] = parts[1].strip()
                    break
    
    if 'success' not in result:
        for line in response_content.splitlines():
            if 'success' in line.lower() and ('\t' in line or ':' in line):
                separator = '\t' if '\t' in line else ':'
                parts = line.split(separator, 1)
                if len(parts) > 1:
                    result['success'] = parts[1].strip()
                    break
    
    # Определение типа устройства
    brand = result.get('brand', '').lower()
    model = result.get('model', '').lower()
    
    if 'apple' in brand or 'iphone' in brand or 'ipad' in brand or 'mac' in brand:
        result['device_type'] = 'Apple'
    elif 'samsung' in brand or 'xiaomi' in brand or 'huawei' in brand or 'oppo' in brand or 'motorola' in brand:
        result['device_type'] = 'Android'
    elif 'sm-' in model or 'galaxy' in model or 'redmi' in model or 'pixel' in model:
        result['device_type'] = 'Android'
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
                return {'error': f'შემოწმების უცნობი ტიპი: {service_type}'}
            
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
                    'error': f'სერვერის შეცდომა: {response.status_code}',
                    'status_code': response.status_code,
                    'raw_response': response.text[:2000] + '...' if len(response.text) > 2000 else response.text
                }
            
            # Логируем сырой ответ для отладки
            logging.debug(f"Raw API response for IMEI {imei}, service {service_type}:\n{response.text}")
            
            # Всегда используем универсальный парсер
            parsed_data = parse_universal_response(response.text)
            
            # Добавляем сырой ответ для отладки
            parsed_data['raw_response'] = response.text[:500] + '...' if len(response.text) > 500 else response.text
            
            return parsed_data
    
    except requests.exceptions.RequestException as e:
        return {'error': f'ქსელის შეცდომა: {str(e)}'}
    except Exception as e:
        return {'error': f'გაუთვალისწინებელი შეცდომა: {str(e)}'}

# Для обратной совместимости
parse_free_html = parse_universal_response
