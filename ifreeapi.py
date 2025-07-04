import os
import re
import requests
import logging
import time
import threading
from bs4 import BeautifulSoup

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
    """Проверяет корректность формата IMEI с использованием алгоритма Луна"""
    if len(imei) not in (14, 15) or not imei.isdigit():
        return False
    
    # Для IMEI длиной 14 пропускаем проверку Луна
    if len(imei) == 14:
        return True
    
    # Алгоритм Луна для 15-значных IMEI
    total = 0
    for i, char in enumerate(imei[:14]):
        digit = int(char)
        if i % 2 == 1:  # Четные позиции (по индексу, начиная с 0)
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(imei[14])

def parse_free_json(data: dict) -> dict:
    """Парсит JSON-ответ бесплатной проверки IMEI для Android устройств"""
    key_mapping = {
        'brand': 'ბრენდი',
        'model': 'მოდელი',
        'modelName': 'მოდელის სახელი',
        'manufacturer': 'მწარმოებელი',
        'status': 'სტატუსი',
        'activation_status': 'აქტივაციის სტატუსი',
        'fmi_status': 'FMI სტატუსი',
        'sim_lock': 'SIM ლოკი',
        'blacklist_status': 'შავი სიის სტატუსი',
        'carrier': 'ოპერატორი',
        'warranty_status': 'გარანტიის სტატუსი',
        'imei': 'IMEI ნომერი',
        'serial': 'სერიული ნომერი',
        'manufacture_date': 'წარმოების თარიღი',
        'purchase_date': 'შეძენის თარიღი',
        'activation_date': 'აქტივაციის თარიღი',
        'purchase_country': 'შეძენის ქვეყანა',
        'last_restore': 'ბოლო აღდგენა',
        'factory_unlocked': 'ქარხნულად გახსნილი',
        'refurbished': 'რემონტირებული',
        'replaced': 'შეცვლილი',
        'loaner': 'სესხით',
        'applecare': 'AppleCare',
        'blocked_status': 'ბლოკირების სტატუსი',
        'restore_status': 'აღდგენის სტატუსი',
        'next_tether_policy': 'შემდეგი პოლიტიკა',
        'sim_lock_policy': 'SIM ლოკის პოლიტიკა',
    }

    result = {}
    for key, value in data.items():
        georgian_key = key_mapping.get(key, key)
        result[georgian_key] = value

    required_keys = ['imei', 'model', 'status']
    for key in required_keys:
        if key not in result:
            result[key] = 'N/A'
            
    return result

def parse_free_html(html_content: str) -> dict:
    """Универсальный парсер HTML для бесплатной проверки"""
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {}
    
    # 1. Парсинг всех таблиц
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True).replace(':', '').lower()
                value = cols[1].get_text(strip=True)
                result[key] = value
    
    # 2. Парсинг списков (ul/ol)
    for list_tag in soup.find_all(['ul', 'ol']):
        for item in list_tag.find_all('li'):
            text = item.get_text(strip=True)
            if ':' in text:
                key, value = text.split(':', 1)
                key = key.strip().lower()
                result[key] = value.strip()
    
    # 3. Парсинг пар ключ-значение в div/spans
    for div in soup.find_all('div'):
        if ':' in div.get_text():
            parts = div.get_text(strip=True).split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip().lower()
                value = parts[1].strip()
                result[key] = value
                
    # 4. Стандартизация ключей
    key_mapping = {
        'imei': 'imei',
        'serial number': 'serial',
        'model': 'model',
        'status': 'status',
        'activation status': 'activation_status',
        'fmi status': 'fmi_status',
        'sim lock': 'sim_lock',
        'blacklist status': 'blacklist_status',
        'carrier': 'carrier',
        'warranty status': 'warranty_status',
        'purchase date': 'purchase_date',
        'activation date': 'activation_date',
        'purchase country': 'purchase_country',
        'last restore': 'last_restore',
        'factory unlocked': 'factory_unlocked',
        'refurbished': 'refurbished',
        'replaced': 'replaced',
        'loaner': 'loaner',
        'applecare': 'applecare',
        'blocked status': 'blocked_status',
        'restore status': 'restore_status',
        'next tether policy': 'next_tether_policy',
        'sim lock policy': 'sim_lock_policy',
        'mdm status': 'mdm_status',
        'google account status': 'google_account_status'
    }
    
    standardized_result = {}
    for key, value in result.items():
        # Удаляем лишние символы
        clean_key = key.replace('_', ' ').strip()
        
        # Ищем совпадение в маппинге
        matched = False
        for pattern, new_key in key_mapping.items():
            if pattern in clean_key:
                standardized_result[new_key] = value
                matched = True
                break
                
        if not matched:
            standardized_result[clean_key] = value

    # 5. Валидация обязательных полей
    required_keys = ['imei', 'model', 'status']
    for key in required_keys:
        if key not in standardized_result:
            logging.warning(f"Missing required key: {key}")
            standardized_result[key] = 'N/A'
            
    # 6. Проверка полноты данных
    if len(standardized_result) < 3:
        logging.error("Insufficient data in free check response")
        return {'error': 'მონაცემების არასაკმარისი რაოდენობა'}
            
    return standardized_result

def perform_api_check(imei: str, service_type: str) -> dict:
    """Выполняет проверку IMEI через внешний API"""
    try:
        with REQUEST_SEMAPHORE:
            if service_type not in SERVICE_TYPES:
                return {'error': f'შემოწმების უცნობი ტიპი: {service_type}'}
            
            if not validate_imei(imei):
                return {'error': 'IMEI-ის არასწორი ფორმატი. უნდა შედგებოდეს 14 ან 15 ციფრისგან.'}
            
            service_code = SERVICE_TYPES[service_type]
            data = {
                "service": service_code,
                "imei": imei,
                "key": API_KEY
            }
            
            attempts = 0
            max_attempts = 3
            delay = 2
            
            while attempts < max_attempts:
                try:
                    time.sleep(1)  # Задержка перед запросом
                    response = requests.post(API_URL, data=data, timeout=30)
                    time.sleep(0.5)  # Задержка после запроса
                    
                    if response.status_code == 200:
                        break
                    
                    if response.status_code >= 500:
                        raise Exception(f"Server error: {response.status_code}")
                        
                except Exception as e:
                    attempts += 1
                    if attempts < max_attempts:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        return {
                            'error': f'მოთხოვნა ვერ შესრულდა {max_attempts} ცდის შემდეგ',
                            'details': str(e)
                        }
        
            if response.status_code != 200:
                return {
                    'error': f'სერვერის შეცდომა: {response.status_code}',
                    'details': response.text[:200] + '...' if len(response.text) > 200 else response.text
                }
            
            # Для бесплатной проверки
            if service_type == 'free':
                try:
                    json_data = response.json()
                    if isinstance(json_data, dict) and 'status' in json_data:
                        return parse_free_json(json_data)
                except:
                    pass
                
                return parse_free_html(response.text)
        
            try:
                json_data = response.json()
                if not json_data.get('success'):
                    error_msg = json_data.get('error', 'API-ის უცნობი შეცდომა')
                    return {'error': f'შემოწმების შეცდომა: {error_msg}'}
                    
                return json_data.get('data', {})
                
            except ValueError:
                return {'html_content': response.text}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'ქსელის შეცდომა: {str(e)}'}
    except Exception as e:
        return {'error': f'გაუთვალისწინებელი შეცდომა: {str(e)}'}
