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
    """Проверяет корректность формата IMEI"""
    return len(imei) == 15 and imei.isdigit()

def perform_api_check(imei: str, service_type: str) -> dict:
    """Выполняет проверку IMEI через внешний API"""
    if service_type not in SERVICE_TYPES:
        return {'error': f'შემოწმების უცნობი ტიპი: {service_type}'}
    
    if not validate_imei(imei):
        return {'error': 'IMEI-ის არასწორი ფორმატი. უნდა შედგებოდეს 15 ციფრისგან.'}
    
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
                'error': f'სერვერის შეცდომა: {response.status_code}',
                'details': response.text[:200] + '...' if len(response.text) > 200 else response.text
            }
        
        # Для бесплатной проверки возвращаем HTML-контент
        if service_type == 'free':
            return {'html_content': response.text}
        
        try:
            # Пытаемся обработать ответ как JSON
            json_data = response.json()
            
            if not json_data.get('success'):
                error_msg = json_data.get('error', 'API-ის უცნობი შეცდომა')
                return {'error': f'შემოწმების შეცდომა: {error_msg}'}
                
            return json_data.get('data', {})
            
        except ValueError:
            # Если ответ не JSON, возвращаем как HTML
            return {'html_content': response.text}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'ქსელის შეცდომა: {str(e)}'}
    except Exception as e:
        return {'error': f'გაუთვალისწინებელი შეცდომა: {str(e)}'}
