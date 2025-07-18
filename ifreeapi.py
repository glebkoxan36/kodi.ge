# ifreeapi.py
import requests
import logging
import re
from collections import OrderedDict

logger = logging.getLogger(__name__)

API_URL = "https://api.ifreeicloud.co.uk"
API_KEY = "4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO"  # Замените на ваш ключ

SERVICE_CODES = {
    'free': 0,
    'fmi': 4,
    'blacklist': 9,
    'sim_lock': 255,
    'activation': 247,
    'carrier': 204,
    'mdm': 204,
    'samsung_v1': 11,
    'samsung_v2': 190,
    'xiaomi': 196,
    'google_pixel': 209,
    'huawei_v1': 158,
    'huawei_v2': 283,
    'motorola': 246,
    'oppo': 317,
    'frp': 160,
    'sim_lock_android': 255
}

ERROR_MESSAGES = {
    'invalid_imei': 'არასწორი IMEI ნომერი',
    'invalid_service': 'არასწორი სერვისის ტიპი',
    'api_error': 'API შეცდომა',
    'network_error': 'ქსელური შეცდომა',
    'server_error': 'სერვერის შეცდომა',
    'insufficient_funds': 'არასაკმარისი თანხა ანგარიშზე',
    'device_not_found': 'მოწყობილობა ვერ მოიძებნა'
}
    
def validate_imei(imei: str) -> bool:
    """Validate IMEI format (14-15 digits)"""
    clean_imei = re.sub(r'\D', '', imei)
    return len(clean_imei) in (14, 15) and clean_imei.isdigit()

def perform_api_check(imei: str, service_type: str) -> dict:
    """Perform API check and return parsed results"""
    if not validate_imei(imei):
        return {
            'success': False,
            'error': ERROR_MESSAGES['invalid_imei'],
            'error_type': 'invalid_input',
            'status': 'Invalid IMEI'
        }
    
    if service_type not in SERVICE_CODES:
        return {
            'success': False,
            'error': ERROR_MESSAGES['invalid_service'],
            'error_type': 'invalid_service',
            'status': 'Invalid Service'
        }
    
    try:
        payload = {
            'key': API_KEY,
            'imei': imei,
            'service': SERVICE_CODES[service_type]
        }
        
        response = requests.post(API_URL, data=payload, timeout=30)
        http_code = response.status_code
        
        # Обработка HTTP ошибок
        if http_code != 200:
            error_msg = f"HTTP Error: {http_code}"
            return {
                'success': False,
                'error': f"API server error: {http_code}",
                'http_code': http_code,
                'error_type': 'server_error',
                'status': 'Server Error'
            }
        
        data = response.json()
        
        if not data.get('success', False):
            error = data.get('error', 'Unknown API error')
            return {
                'success': False,
                'error': error,
                'api_error': error,
                'error_type': 'api_error',
                'status': 'API Error'
            }
        
        # Extract device information
        device_info = data.get('object', {})
        
        # Simplified result structure
        result = {
            'success': True,
            'imei': imei,
            'service': service_type,
            'brand': device_info.get('brand', ''),
            'model': device_info.get('model', ''),
            'status': device_info.get('status', ''),
            'fmi_status': device_info.get('fmi_status', ''),
            'blacklist_status': device_info.get('blacklist_status', ''),
            'sim_lock': device_info.get('sim_lock', ''),
            'activation_status': device_info.get('activation_status', ''),
            'carrier': device_info.get('carrier', ''),
            'mdm_status': device_info.get('mdm_status', ''),
            'warranty_status': device_info.get('warranty_status', ''),
            'full_response': device_info  # Keep full response for debugging
        }
        
        # Determine device type
        brand = result['brand'].lower()
        if 'apple' in brand or 'iphone' in brand or 'ipad' in brand:
            result['device_type'] = 'Apple'
        elif 'samsung' in brand or 'android' in brand or 'google' in brand:
            result['device_type'] = 'Android'
        else:
            result['device_type'] = 'Unknown'
        
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"{ERROR_MESSAGES['network_error']}: {str(e)}",
            'error_type': 'network_error',
            'status': 'Network Error'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"{ERROR_MESSAGES['api_error']}: {str(e)}",
            'error_type': 'processing_error',
            'status': 'Processing Error'
        }
