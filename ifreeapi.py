import os
import re
import requests
import logging

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
    'service_247': 247,
    'mdm': 204,
    'android_pixel': 209,
    'service_158': 158,
    'lg': 160,
    'oneplus': 233,
    'oppo': 317
}

def validate_imei(imei: str) -> bool:
    """Проверка валидности формата IMEI"""
    return len(imei) == 15 and imei.isdigit()

def perform_api_check(imei: str, service_type: str) -> dict:
    """
    Выполнение запроса к API iFree
    Возвращает:
      - Для бесплатных сервисов: HTML-контент
      - Для платных сервисов: JSON-объект
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
        
        if response.status_code != 200:
            return {'error': f'API returned HTTP code {response.status_code}'}
        
        # Для сервисов, возвращающих HTML
        if service_type in ['free', 'blacklist', 'sim_lock', 'fmi', 
                           'service_247', 'mdm', 'android_pixel',
                           'service_158', 'lg', 'oneplus', 'oppo']:
            return {
                'html_content': response.text,
                'raw_response': response.text
            }
        # Для сервисов, возвращающих JSON
        else:
            try:
                result = response.json()
                if not result.get('success', False):
                    return {'error': result.get('error', 'Unknown API error')}
                return result.get('object', {})
            except ValueError:
                return {'error': 'Invalid JSON response from API'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f"Request error: {str(e)}"}
    except Exception as e:
        return {'error': f"Service error: {str(e)}"}
