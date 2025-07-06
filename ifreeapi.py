import os
import re
import requests
import logging
import time
import threading
import json
from collections import OrderedDict

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

# Настройки повторных попыток
MAX_RETRIES = 2
RETRY_DELAY = 3  # секунды между попытками

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
        'device_not_found': 'მოწყობილობის იდენტიფიკაცია ვერ მოხერხდა',
        'empty_response': 'API-მ ცარიელი პასუხი დააბრუნა',
        'max_retries_exceeded': 'მოთხოვნის გამეორების ლიმიტი ამოიწურა',
        'incomplete_data': 'მოწყობილობის მონაცემები არასრულია',
        'payment_error': 'გადახდის პროცესში შეცდომა მოხდა',
        'stripe_error': 'ბარათით გადახდის შეცდომა',
        'android_device': 'ამ გვერდზე შეგიძლიათ მხოლოდ Apple მოწყობილობების შემოწმება'
    },
    'free': {
        'limit_exceeded': 'უფასო შემოწმების ლიმიტი ამოიწურა',
        'invalid_serial': 'არასწორი სერიული ნომერი',
        'not_activated': 'მოწყობილობა არ არის აქტივირებული',
        'empty_response': 'უფასო მომსახურება დროებით მიუწვდომელია',
    },
    'paid': {
        'payment_required': 'გადახდა საჭიროა ამ მომსახურებისთვის',
        'payment_failed': 'გადახდა ვერ შესრულდა',
        'already_checked': 'ამ IMEI-ით შემოწმება უკვე გაკეთებულია',
        'empty_response': 'პასუხი ვერ მიიღწა, თანხა დაგიბრუნდებათ',
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
    "Device not found": "device_not_found",
    "Payment required": "payment_required",
    "Payment failed": "payment_failed"
}

# Словарь перевода ключей
KEY_TRANSLATIONS = {
    'Model': 'მოდელი',
    'Model Name': 'მოდელის სახელი',
    'Brand': 'ბრენდი',
    'Manufacturer': 'მწარმოებელი',
    'IMEI Number': 'IMEI ნომერი',
    'Network': 'ქსელი',
    'Purchase Date': 'შეძენის თარიღი',
    'Activation Date': 'აქტივაციის თარიღი',
    'Warranty Expiry': 'გარანტიის ვადის გასვლის თარიღი',
    'Locked Status': 'დაბლოკვის სტატუსი',
    'Find My iPhone': 'Find My iPhone სტატუსი',
    'iCloud Status': 'iCloud სტატუსი',
    'SIM Lock': 'SIM ლოკი',
    'Blacklist Status': 'შავი სიის სტატუსი',
    'FMI Status': 'FMI სტატუსი',
    'Activation Status': 'აქტივაციის სტატუსი',
    'Carrier': 'ოპერატორი',
    'Warranty Status': 'გარანტიის სტატუსი'
}

def validate_imei(imei: str) -> bool:
    """Проверяет валидность IMEI (14 или 15 цифр) с алгоритмом Луна для 15-значных"""
    # Проверка длины
    if len(imei) not in (14, 15):
        return False
    
    # Проверка, что все символы - цифры
    if not imei.isdigit():
        return False
    
    # Для 15-значных IMEI применяем алгоритм Луна
    if len(imei) == 15:
        total = 0
        for i, char in enumerate(imei[:14]):
            digit = int(char)
            # Для четных позиций (начиная с 0 - нечетные в 1-based)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        # Вычисление контрольной цифры
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(imei[14])
    
    # Для 14-значных (серийных номеров) просто возвращаем True
    return True

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

def parse_free_html(html_content: str) -> dict:
    """
    Парсит HTML ответ для бесплатной проверки.
    Возвращает словарь с данными устройства.
    """
    result = {}
    try:
        # Извлекаем данные из текста ответа
        lines = html_content.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Применяем перевод ключей
                translated_key = KEY_TRANSLATIONS.get(key, key)
                result[translated_key] = value
                
                # Сохраняем оригинальный ключ для совместимости
                result[key.replace(' ', '_').lower()] = value
    except Exception as e:
        logging.error(f"HTML parsing error: {str(e)}")
        result['error'] = get_error_message('parsing_error')
        result['details'] = str(e)
    
    return result

def perform_api_check(imei: str, service_type: str) -> dict:
    """
    Выполняет проверку IMEI через внешний API.
    Возвращает чистые данные устройства без технических деталей на грузинском языке.
    Всегда показывает все полученные данные, даже если они неполные.
    """
    retries = 0
    last_response = None
    last_exception = None
    
    # Для платных сервисов делаем только 1 попытку
    max_attempts = MAX_RETRIES
    
    # Проверка: если это сервис для Apple (страница applecheck) и IMEI не начинается с 01 или 35 (Apple), то возвращаем ошибку
    if service_type in ['free', 'fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']:
        if not (imei.startswith('01') or imei.startswith('35')):
            return {
                'error': get_error_message('android_device'),
                'details': 'ეს გვერდი განკუთვნილია მხოლოდ Apple მოწყობილობებისთვის',
                'device_type': 'Android'
            }
    
    while retries <= max_attempts:
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
                    
                    # Для платных сервисов сразу возвращаем ошибку
                    if service_type != 'free':
                        return {
                            'error': get_error_message('server_error'),
                            'status_code': response.status_code,
                            'service_type': service_type,
                            'server_response': response.text[:500] + '...'
                        }
                    
                    # Для бесплатных сервисов пробуем повторить
                    if response.status_code >= 500 and retries < max_attempts:
                        retries += 1
                        logging.info(f"Retrying ({retries}/{max_attempts}) for IMEI {imei}")
                        time.sleep(RETRY_DELAY)
                        continue
                    
                    return {
                        'error': get_error_message('server_error'),
                        'status_code': response.status_code,
                        'service_type': service_type,
                        'server_response': response.text[:500] + '...'
                    }
                
                # Сохраняем последний ответ для анализа
                last_response = response.text
                
                # Проверка на пустой ответ
                if not last_response.strip():
                    logging.warning(f"Empty API response for IMEI: {imei}")
                    
                    # Для платных сервисов сразу возвращаем ошибку
                    if service_type != 'free':
                        return {
                            'error': get_error_message('empty_response', service_type),
                            'service_type': service_type,
                            'server_response': 'Empty response'
                        }
                    
                    if retries < max_attempts:
                        retries += 1
                        logging.info(f"Retrying ({retries}/{max_attempts}) for empty response")
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        return {
                            'error': get_error_message('empty_response', service_type),
                            'service_type': service_type,
                            'server_response': 'Empty response after retries'
                        }
                
                # Логируем факт запроса
                logging.info(f"API check for IMEI {imei}, service {service_type}. Time: {request_time:.2f}s")
                
                # Парсим ответ
                if service_type == 'free':
                    parsed_data = parse_free_html(last_response)
                else:
                    # Для платных сервисов просто возвращаем текст ответа
                    parsed_data = {'server_response': last_response[:500] + '...'}
                
                # Добавляем IMEI для отслеживания
                parsed_data['imei'] = imei
                parsed_data['service_type'] = service_type
                
                return parsed_data
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error for IMEI {imei}: {str(e)}")
            last_exception = str(e)
            
            # Для платных сервисов сразу возвращаем ошибку
            if service_type != 'free':
                return {
                    'error': get_error_message('network_error'),
                    'details': last_exception,
                    'service_type': service_type
                }
            
            if retries < max_attempts:
                retries += 1
                # Увеличиваем задержку с каждой попыткой
                current_delay = RETRY_DELAY * (retries + 1)
                logging.info(f"Retrying ({retries}/{max_attempts}) after network error. Delay: {current_delay}s")
                time.sleep(current_delay)
                continue
            else:
                return {
                    'error': get_error_message('network_error'),
                    'details': last_exception,
                    'service_type': service_type
                }
                
        except Exception as e:
            logging.error(f"Unexpected error for IMEI {imei}: {str(e)}")
            last_exception = str(e)
            return {
                'error': get_error_message('unknown_error'),
                'details': last_exception,
                'service_type': service_type,
                'server_response': last_response[:500] + '...' if last_response else "No response"
            }
    
    # Если превышено количество попыток
    logging.error(f"Max retries exceeded for IMEI: {imei}")
    return {
        'error': get_error_message('max_retries_exceeded'),
        'details': f'After {max_attempts} retries',
        'service_type': service_type,
        'server_response': last_response[:500] + '...' if last_response else "No response"
                      }
