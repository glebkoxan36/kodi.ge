import os
import re
import requests
import logging
import time
import threading
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_check.log"),
        logging.StreamHandler()
    ]
)

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

# Словарь ошибок для разных сервисов
ERROR_MESSAGES = {
    'common': {
        'invalid_imei': 'არასწორი IMEI ნომერი',
        'invalid_key': 'არასწორი API გასაღები',
        'insufficient_funds': 'არასაკმარისი თანხა ანგარიშზე',
        'unsupported_service': 'მომსახურების ტიპი არაა მხარდაჭერილი',
        'server_error': 'API სერვერის შეცდომა',
        'timeout': 'მოთხოვნის დამუშავების დრო ამოიწურა',
        'network_error': 'ქსელური შეცდომა',
        'api_error': 'API შეცდომა',
        'unknown_error': 'უცნობი შეცდომა',
        'parsing_error': 'მონაცემების დამუშავების შეცდომა',
        'device_not_found': 'მოწყობილობის იდენტიფიკაცია ვერ მოხერხდა'
    },
    'free': {
        'limit_exceeded': 'უფასო შემოწმების ლიმიტი ამოიწურა',
        'invalid_serial': 'არასწორი სერიული ნომერი',
        'not_activated': 'მოწყობილობა არ არის აქტივირებული'
    },
    'paid': {
        'payment_required': 'გადახდა საჭიროა ამ მომსახურებისთვის',
        'payment_failed': 'გადახდა ვერ შესრულდა',
        'already_checked': 'ამ IMEI-ით შემოწმება უკვე გაკეთებულია'
    }
}

# Соответствие ошибок API нашим кодам
API_ERRORS = {
    "Invalid IMEI": "invalid_imei",
    "Invalid Key": "invalid_key",
    "Insufficient Funds": "insufficient_funds",
    "Service not available": "unsupported_service",
    "Service not found": "unsupported_service",
    "Server Error": "server_error",
    "Request Timeout": "timeout",
    "Device not found": "device_not_found"
}

# Словарь перевода ключей
KEY_TRANSLATIONS = {
    'model': 'მოდელი',
    'model_name': 'მოდელის სახელი',
    'modelName': 'მოდელის სახელი',
    'brand': 'ბრენდი',
    'manufacturer': 'მწარმოებელი',
    'imei': 'IMEI',
    'imei_number': 'IMEI ნომერი',
    'status': 'სტატუსი',
    'sim_lock': 'SIM ლოკი',
    'blacklist_status': 'შავი სიის სტატუსი',
    'fmi_status': 'FMI სტატუსი',
    'activation_status': 'აქტივაციის სტატუსი',
    'carrier': 'ოპერატორი',
    'warranty_status': 'გარანტიის სტატუსი',
    'product_type': 'პროდუქტის ტიპი',
    'device_type': 'მოწყობილობის ტიპი',
    'manufacture': 'წარმოების თარიღი',
    'state': 'მდგომარეობა'
}

def validate_imei(imei: str) -> bool:
    """Проверяет валидность IMEI (15 цифр)"""
    return bool(re.fullmatch(r"\d{15}", imei))

def get_error_message(error_code: str, service_type: str = 'common') -> str:
    """Возвращает локализованное сообщение об ошибке"""
    service_errors = ERROR_MESSAGES.get(service_type, {})
    common_errors = ERROR_MESSAGES['common']
    
    # Сначала проверяем сервис-специфичные ошибки
    if error_code in service_errors:
        return service_errors[error_code]
    
    # Затем общие ошибки
    if error_code in common_errors:
        return common_errors[error_code]
    
    # Возвращаем общее сообщение для неизвестных ошибок
    return common_errors['unknown_error']

def parse_universal_response(response_content: str) -> dict:
    """
    Универсальный парсер для ответов API.
    Извлекает только чистые данные устройства, скрывая технические детали.
    Возвращает ключи на грузинском языке.
    """
    result = {}
    
    # Попытка парсинга JSON
    try:
        data = json.loads(response_content)
        
        # Обработка ошибок API
        if 'error' in data and data['error']:
            error_text = data['error'].strip()
            error_code = API_ERRORS.get(error_text, 'api_error')
            return {
                'error': get_error_message(error_code),
                'details': error_text
            }
        
        # Удаление технических полей
        for field in ['object', 'response', 'status', 'success']:
            if field in data:
                del data[field]
        
        # Обработка объекта данных
        if 'object' in data and isinstance(data['object'], dict):
            for key, value in data['object'].items():
                normalized_key = key.strip().lower().replace(' ', '_')
                result[normalized_key] = value
        
        # Обработка строкового ответа
        if 'response' in data and isinstance(data['response'], str):
            lines = data['response'].splitlines()
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if key not in result:
                        result[key] = value
        
        # Добавление основных полей
        for key in ['model', 'model_name', 'modelName', 'brand', 'manufacturer', 
                    'imei', 'imei_number', 'sim_lock', 'blacklist_status', 
                    'fmi_status', 'activation_status', 'carrier', 'warranty_status', 
                    'product_type', 'manufacture', 'state']:
            if key in data and key not in result:
                result[key] = data[key]
                
    except json.JSONDecodeError:
        # Обработка текстового формата
        try:
            lines = response_content.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Фильтрация технических строк
                if re.match(r'^(object|success|status|error)\s*:', line, re.I):
                    continue
                    
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    result[key] = value
                elif '\t' in line:
                    key, value = line.split('\t', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    result[key] = value
        except Exception as e:
            logging.error(f"Text parsing error: {str(e)}")
            result['შეცდომა'] = f'Text parsing error: {str(e)}'
    
    # Определение типа устройства
    brand = result.get('brand', '').lower()
    model = result.get('model', '').lower()
    
    # Проверяем, является ли устройство Apple
    if ('apple' in brand or 
        'iphone' in brand or 
        'ipad' in brand or 
        'macbook' in brand or
        'iphone' in model or 
        'ipad' in model or 
        'mac' in model):
        result['device_type'] = 'Apple'
    # Проверяем Android устройства
    elif ('samsung' in brand or 
          'xiaomi' in brand or 
          'huawei' in brand or 
          'oppo' in brand or 
          'motorola' in brand or 
          'google' in brand or
          'sm-' in model or 
          'galaxy' in model):
        result['device_type'] = 'Android'
    else:
        result['device_type'] = 'Unknown'
    
    # Удаление технических полей из результата
    for field in ['object', 'response', 'status', 'success']:
        if field in result:
            del result[field]
    
    # Перевод ключей
    translated_result = {}
    for key, value in result.items():
        new_key = KEY_TRANSLATIONS.get(key, key)
        translated_result[new_key] = value
        
    return translated_result

def perform_api_check(imei: str, service_type: str) -> dict:
    """
    Выполняет проверку IMEI через внешний API.
    Возвращает чистые данные устройства без технических деталей на грузинском языке.
    """
    try:
        # Проверка валидности IMEI
        if not validate_imei(imei):
            logging.warning(f"Invalid IMEI: {imei} for service {service_type}")
            return {
                'error': get_error_message('invalid_imei'),
                'service_type': service_type
            }
        
        # Проверка поддерживаемого типа сервиса
        if service_type not in SERVICE_TYPES:
            logging.error(f"Unsupported service: {service_type}")
            return {
                'error': get_error_message('unsupported_service'),
                'details': f'Requested service: {service_type}'
            }
        
        with REQUEST_SEMAPHORE:
            # Подготавливаем данные запроса
            service_code = SERVICE_TYPES[service_type]
            data = {
                "service": service_code,
                "imei": imei,
                "key": API_KEY
            }
            
            # Задержка перед запросом для стабильности API
            time.sleep(1)
            
            # Выполняем запрос с таймаутом
            start_time = time.time()
            response = requests.post(API_URL, data=data, timeout=30)
            request_time = time.time() - start_time
            
            # Обрабатываем HTTP ошибки
            if response.status_code != 200:
                logging.error(f"API error: {response.status_code} for IMEI {imei}, service {service_type}")
                return {
                    'error': get_error_message('server_error'),
                    'status_code': response.status_code,
                    'service_type': service_type
                }
            
            # Логируем факт запроса
            logging.info(f"API check for IMEI {imei}, service {service_type}. Time: {request_time:.2f}s")
            
            # Парсим ответ
            parsed_data = parse_universal_response(response.text)
            
            # Добавляем IMEI для отслеживания
            parsed_data['imei'] = imei
            
            # Фильтрация технических данных
            final_data = {}
            for key, value in parsed_data.items():
                # Пропускаем технические строки
                if isinstance(value, str) and any(
                    p in value for p in [
                        'object":{"model"',
                        '"status":"Successful"',
                        '"success":true',
                        '"response":"Model:'
                    ]
                ):
                    continue
                final_data[key] = value
            
            # Проверка на пустой результат
            if not final_data or len(final_data) < 3:
                logging.warning(f"Empty response for IMEI: {imei}")
                return {
                    'error': get_error_message('device_not_found'),
                    'service_type': service_type,
                    'original_html': response.text
                }
            
            # Сохраняем оригинальный ответ для отладки
            final_data['server_response'] = response.text
            
            return final_data
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error for IMEI {imei}: {str(e)}")
        return {
            'error': get_error_message('network_error'),
            'details': str(e),
            'service_type': service_type
        }
    except Exception as e:
        logging.error(f"Unexpected error for IMEI {imei}: {str(e)}")
        return {
            'error': get_error_message('unknown_error'),
            'details': str(e),
            'service_type': service_type
        }

# Для обратной совместимости
parse_free_html = parse_universal_response
