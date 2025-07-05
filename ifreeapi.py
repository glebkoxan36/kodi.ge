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
    """Проверяет валидность IMEI (15 цифр)"""
    return bool(re.fullmatch(r"\d{15}", imei))

def parse_universal_response(response_content: str) -> dict:
    """Универсальный парсер для обработки любых ответов сервера"""
    # Сначала пробуем распарсить как JSON
    try:
        import json
        return json.loads(response_content)
    except:
        pass
    
    # Если не JSON - обрабатываем как HTML/текст
    result = {}
    
    # Попытка парсинга через BeautifulSoup
    try:
        soup = BeautifulSoup(response_content, 'html.parser')
        
        # Парсинг таблиц
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True).replace(':', '')
                    value = cols[1].get_text(strip=True)
                    if key and value:
                        result[key] = value
        
        # Парсинг списков
        for list_tag in soup.find_all(['ul', 'ol']):
            for item in list_tag.find_all('li'):
                text = item.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        result[key] = value
        
        # Парсинг div с ключ-значение
        for div in soup.find_all('div'):
            if ':' in div.get_text():
                parts = div.get_text(strip=True).split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        result[key] = value
    except:
        pass
    
    # Если BeautifulSoup не нашел данных - парсим построчно
    if not result:
        lines = response_content.splitlines()
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    result[key] = value
    
    # Если вообще ничего не найдено - возвращаем исходный текст
    if not result:
        return {'raw_response': response_content}
    
    return result

def parse_free_html(html_content: str) -> dict:
    """Специальный парсер для бесплатных отчетов Apple"""
    return parse_universal_response(html_content)

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
            
            # Всегда используем универсальный парсер
            return parse_universal_response(response.text)
    
    except requests.exceptions.RequestException as e:
        return {'error': f'ქსელის შეცდომა: {str(e)}'}
    except Exception as e:
        return {'error': f'გაუთვალისწინებელი შეცდომა: {str(e)}'}
