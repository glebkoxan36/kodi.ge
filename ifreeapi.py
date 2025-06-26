import os
import re
import requests
import logging
from bs4 import BeautifulSoup

API_URL = os.getenv('API_URL', "https://api.ifreeicloud.co.uk")
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')

SERVICE_TYPES = {
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
    'android_paid': 399,
    'android_premium': 799,
    'google_account': 299,
    'frp_lock': 199,
    'android_full': 799
}

def validate_imei(imei: str) -> bool:
    return len(imei) == 15 and imei.isdigit()

def parse_html_response(html_content: str) -> dict:
    result = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        tables = soup.find_all('table')
        for table in tables:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(':', '').lower().replace(' ', '_')
                    value = cols[1].get_text(strip=True)
                    result[key] = value
        
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
        return {'error': 'Ошибка обработки ответа сервера'}

def perform_api_check(imei: str, service_type: str) -> dict:
    if service_type not in SERVICE_TYPES:
        return {'error': f'Неизвестный тип проверки: {service_type}'}
    
    if not validate_imei(imei):
        return {'error': 'Неверный формат IMEI. Должно быть 15 цифр.'}
    
    service_code = SERVICE_TYPES[service_type]
    data = {
        "service": service_code,
        "imei": imei,
        "key": API_KEY
    }
    
    try:
        response = requests.post(API_URL, data=data, timeout=30)
        
        if response.status_code != 200:
            return {
                'error': f'Ошибка сервера: {response.status_code}',
                'details': response.text[:200] + '...' if len(response.text) > 200 else response.text
            }
        
        if service_type == 'free':
            return parse_html_response(response.text)
        
        try:
            json_data = response.json()
            
            if not json_data.get('success'):
                error_msg = json_data.get('error', 'Неизвестная ошибка API')
                return {'error': f'Ошибка проверки: {error_msg}'}
                
            return json_data.get('data', {})
            
        except ValueError:
            return parse_html_response(response.text)
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Ошибка сети: {str(e)}'}
    except Exception as e:
        return {'error': f'Неожиданная ошибка: {str(e)}'}
