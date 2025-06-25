import os
import re
import requests
import logging
from bs4 import BeautifulSoup

# Конфигурация API
API_URL = os.getenv('API_URL', "https://api.ifreeicloud.co.uk")
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')

# Все типы сервисов из документации
SERVICE_TYPES = {
    'free': 0,
    'paid': 205,
    'premium': 242,
    'blacklist': 9,
    'sim_lock': 255,
    'fmi': 4,
    'activation': 247,  # Активация
    'carrier': 204,     # Оператор
    'full': 999,        # Полная проверка (специальный код)
    'mdm': 204,
    'macbook': 349,     # Специальный код для MacBook
    'android_paid': 399,
    'android_premium': 799,
    'google_account': 299,
    'frp_lock': 199,
    'android_full': 799
}

def validate_imei(imei: str, allow_macbook: bool = False) -> bool:
    """Проверка валидности формата IMEI/серийного номера"""
    # Стандартный IMEI (15 цифр)
    if len(imei) == 15 and imei.isdigit():
        return True
    
    # Серийный номер MacBook (12 символов буквенно-цифровой)
    if allow_macbook and len(imei) in [12, 17, 18] and re.match(r'^[A-Z0-9]+$', imei):
        return True
    
    return False

def parse_html_response(html_content: str) -> dict:
    """Парсинг HTML-ответа от API в структурированный формат"""
    result = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Универсальный парсинг для табличных данных
        tables = soup.find_all('table')
        for table in tables:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(':', '').lower().replace(' ', '_')
                    value = cols[1].get_text(strip=True)
                    result[key] = value
        
        # Специфичные поля
        fields = {
            'device': ['მოწყობილობა', 'device', 'მოდელი'],
            'model': ['მოდელი', 'model'],
            'serial': ['სერიული ნომერი', 'serial'],
            'imei': ['imei'],
            'fmi_status': ['fmi სტატუსი', 'fmi status'],
            'sim_lock': ['sim ლოკი', 'sim lock'],
            'blacklist': ['შავ სიაშია', 'blacklist'],
            'activation': ['აქტივაციის სტატუსი', 'activation status'],
            'carrier': ['ოპერატორი', 'carrier'],
            'warranty': ['გარანტია', 'warranty'],
            'purchase_date': ['შეძენის თარიღი', 'purchase date']
        }
        
        # Поиск по текстовым меткам
        for field, labels in fields.items():
            for label in labels:
                element = soup.find(string=re.compile(label, re.IGNORECASE))
                if element:
                    value_element = element.find_next()
                    if value_element:
                        result[field] = value_element.get_text(strip=True)
        
        return result
    
    except Exception as e:
        logging.error(f"HTML parsing error: {str(e)}")
        return {'error': 'HTML parsing failed'}

def perform_api_check(imei: str, service_type: str) -> dict:
    """
    Выполнение запроса к API iFree
    Возвращает унифицированный словарь с результатами
    """
    if service_type not in SERVICE_TYPES:
        return {'error': f'Unknown service type: {service_type}'}
    
    service_code = SERVICE_TYPES[service_type]
    data = {
        "service": service_code,
        "imei": imei,
        "key": API_KEY
    }
    
    try:
        response = requests.post(API_URL, data=data, timeout=60)
        response.raise_for_status()
        
        # Обработка HTML-ответов
        if service_type in ['free', 'blacklist', 'sim_lock', 'fmi', 
                           'activation', 'carrier', 'mdm']:
            return parse_html_response(response.text)
        
        # Обработка JSON-ответов
        try:
            json_response = response.json()
            if json_response.get('success', False):
                return json_response.get('data', {})
            return {'error': json_response.get('error', 'Unknown API error')}
        except ValueError:
            # Fallback: попытка обработать как HTML
            return parse_html_response(response.text)
    
    except requests.exceptions.RequestException as e:
        return {'error': f"API request failed: {str(e)}"}
    except Exception as e:
        return {'error': f"Unexpected error: {str(e)}"}
