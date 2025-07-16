import os
import re
import requests
import logging
import time
import threading
import json
import traceback
from collections import OrderedDict

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    handler = logging.FileHandler('logs/api.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

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
        'android_device': 'ამ გვერდზე შეგიძლიათ მხოლოდ Apple მოწყობილობების შემოწმება',
        'invalid_service': 'არასწორი სერვისის ტიპი',
        'rate_limit': 'მოთხოვნების ლიმიტი ამოიწურა',
        'maintenance': 'სისტემა განახლების რეჟიმშია',
        'expired_key': 'API გასაღების ვადა გაუვიდა',
        'banned_device': 'მოწყობილობა შავ სიაშია',
        'restricted_region': 'მომსახურება არ ხელმისაწვდომია თქვენს რეგიონში',
        'invalid_format': 'მონაცემების ფორმატი არასწორია',
    },
    'free': {
        'limit_exceeded': 'უფასო შემოწმების ლიმიტი ამოიწურა',
        'invalid_serial': 'არასწორი სერიული ნომერი',
        'not_activated': 'მოწყობილობა არ არის აქტივირებული',
        'empty_response': 'უფასო მომსახურება დროებით მიუწვდომელია',
        'daily_limit': 'დღიური ლიმიტი ამოიწურა',
        'temp_unavailable': 'უფასო მომსახურება დროებით შეჩერებულია',
    },
    'paid': {
        'payment_required': 'გადახდა საჭიროე ამ მომსახურებისთვის',
        'payment_failed': 'გადახდა ვერ შესრულდა',
        'already_checked': 'ამ IMEI-ით შემოწმება უკვე გაკეთებულია',
        'empty_response': 'პასუხი ვერ მიიღწა, თანხა დაგიბრუნდებათ',
        'refund_required': 'გადახდა დაბრუნებულია',
        'fraud_detected': 'გაუმჯობესებული უსაფრთხოების შემოწმება საჭიროა',
    }
}

# Соответствие ошибок API нашим кодам
API_ERRORS = {
    "Invalid IMEI": "invalid_imei",
    "Invalid Key": "invalid_key",
    "Insufficient Funds": "insufficient_funds",
    "Insufficient funds": "insufficient_funds",
    "insufficient_funds": "insufficient_funds",
    "Not enough funds": "insufficient_funds",
    "Service not available": "unsupported_service",
    "Service not found": "unsupported_service",
    "Server Error": "server_error",
    "Request Timeout": "timeout",
    "Device not found": "device_not_found",
    "Payment required": "payment_required",
    "Payment failed": "payment_failed",
    "balance": "insufficient_funds",
    "funds": "insufficient_funds",
    "credit": "insufficient_funds",
    "Rate Limit Exceeded": "rate_limit",
    "Maintenance Mode": "maintenance",
    "Key Expired": "expired_key",
    "Device Banned": "banned_device",
    "Region Restricted": "restricted_region",
    "Invalid Data Format": "invalid_format",
    "Daily Free Limit": "daily_limit",
    "Temporarily Unavailable": "temp_unavailable",
    "Refund Issued": "refund_required",
    "Fraud Detected": "fraud_detected",
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
    'state': 'მდგომარეობა',
    'network': 'ქსელი',
    'purchase_date': 'შეძენის თარიღი',
    'activation_date': 'აქტივაციის თარიღი',
    'warranty_expiry': 'გარანტიის ვადის გასვლის თარიღი',
    'locked_status': 'დაბლოკვის სტატუსი',
    'find_my_iphone': 'Find My iPhone სტატუსი',
    'icloud_status': 'iCloud სტატუსი',
    'service': 'სერვისი',
    'object': 'ობიექტი'
}

# Список технических полей для удаления
TECHNICAL_FIELDS = [
    'object', 'status', 'success', 'service', 
    'key', 'api_key', 'request_id', 'session_id'
]

def validate_imei(imei: str) -> bool:
    """Проверяет валидность IMEI (14 или 15 цифр) с алгоритмом Луна для 15-значных"""
    logger.debug(f"Validating IMEI: {imei}")
    # Удаление всех нецифровых символов
    clean_imei = re.sub(r'\D', '', imei)
    
    # Проверка длины
    if len(clean_imei) not in (14, 15):
        logger.warning(f"Invalid IMEI length: {len(clean_imei)}")
        return False
    
    # Проверка, что все символы - цифры
    if not clean_imei.isdigit():
        logger.warning(f"IMEI contains non-digit characters: {clean_imei}")
        return False
    
    # Для 15-значных IMEI применяем алгоритм Луна
    if len(clean_imei) == 15:
        total = 0
        for i, char in enumerate(clean_imei[:14]):
            digit = int(char)
            # Для четных позиций (начиная с 0 - нечетные в 1-based)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        # Вычисление контрольной цифры
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(clean_imei[14])
    
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

def filter_technical_fields(response_content: str) -> str:
    """
    Фильтрует технические поля, но сохраняет содержимое 'response'
    и переводит ключи на грузинский язык.
    """
    if not response_content.strip():
        return response_content

    # Словарь перевода ключей
    key_translations = {
        "Model": "მოდელი",
        "Model Name": "მოდელის სახელი",
        "Brand": "ბრენდი",
        "Manufacturer": "მწარმოებელი",
        "IMEI Number": "IMEI ნომერი",
        "Network": "ქსელი",
        "Purchase Date": "შეძენის თარიღი",
        "Activation Date": "აქტივაციის თარიღი",
        "Warranty Expiry": "გარანტიის ვადის გასვლის თარიღი",
        "Locked Status": "დაბლოკვის სტატუსი",
        "Find My iPhone": "Find My iPhone სტატუსი",
        "iCloud Status": "iCloud სტატუსი",
        "SIM Lock": "SIM ლოკი",
        "Blacklist Status": "შავი სიის სტატუსი",
        "FMI Status": "FMI სტატუსი",
        "Activation Status": "აქტივაციის სტატუსი",
        "Carrier": "ოპერატორი",
        "Warranty Status": "გარანტიის სტატუსი"
    }

    try:
        data = json.loads(response_content)
        
        # Если есть поле 'response' и оно строка - переводим ключи в его содержимом
        if 'response' in data and isinstance(data['response'], str):
            response_text = data['response'].strip()
            # Применяем перевод ключей
            for eng_key, geo_key in key_translations.items():
                response_text = response_text.replace(f"{eng_key}:", f"{geo_key}:")
            return response_text
            
        # Удаляем технические поля
        for field in TECHNICAL_FIELDS:
            if field in data:
                del data[field]
                
        # Форматируем оставшиеся данные
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        pass

    # Для не-JSON ответов извлекаем содержимое response
    response_match = re.search(r'"response":\s*"([^"]+)"', response_content)
    if response_match:
        response_text = response_match.group(1).replace('\\n', '\n')
        # Применяем перевод ключей
        for eng_key, geo_key in key_translations.items():
            response_text = response_text.replace(f"{eng_key}:", f"{geo_key}:")
        return response_text
        
    # Для других текстовых ответов также применяем перевод
    translated_text = response_content
    for eng_key, geo_key in key_translations.items():
        translated_text = translated_text.replace(f"{eng_key}:", f"{geo_key}:")
    return translated_text

def parse_universal_response(response_content: str) -> dict:
    """
    Универсальный парсер для ответов API.
    Извлекает только чистые данные устройства, скрывая технические детали.
    Возвращает ключи на грузинском языке.
    """
    result = OrderedDict()
    raw_response = response_content  # Сохраняем оригинальный ответ
    
    # Фильтруем технические поля для отображения
    filtered_response = filter_technical_fields(raw_response)
    
    # Попытка парсинга JSON
    try:
        data = json.loads(response_content)
        
        # Обработка ошибок API
        if 'error' in data and data['error']:
            error_text = data['error'].strip().lower()
            
            # Специальная проверка для ошибок баланса
            if any(keyword in error_text for keyword in ['insufficient', 'funds', 'balance', 'credit']):
                error_code = "insufficient_funds"
            
            # Проверка на техобслуживание
            elif 'maintenance' in error_text:
                error_code = "maintenance"
            
            # Проверка ограничения региона
            elif 'region' in error_text or 'country' in error_text:
                error_code = "restricted_region"
            
            # Проверка блокировки устройства
            elif 'blacklist' in error_text or 'blocked' in error_text or 'banned' in error_text:
                error_code = "banned_device"
            
            # Стандартная обработка
            else:
                error_code = API_ERRORS.get(error_text, 'api_error')
            
            logger.warning(f"API error: {error_text}")
            return OrderedDict([
                ('error', get_error_message(error_code)),
                ('details', error_text),
                ('server_response', filtered_response)
            ])
        
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
                    'product_type', 'manufacture', 'state', 'network', 'purchase_date',
                    'activation_date', 'warranty_expiry', 'locked_status', 
                    'find_my_iphone', 'icloud_status']:
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
                if re.match(r'^(object|success|status|error|service|key|response)\s*:', line, re.I):
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
            logger.error(f"Text parsing error: {str(e)}")
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
    for field in TECHNICAL_FIELDS:
        if field in result:
            del result[field]
    
    # Перевод ключей
    translated_result = OrderedDict()
    for key, value in result.items():
        new_key = KEY_TRANSLATIONS.get(key, key)
        translated_result[new_key] = value
        
    # Сохраняем фильтрованный ответ
    translated_result['server_response'] = filtered_response
    return translated_result

def perform_api_check(imei: str, service_type: str) -> dict:
    """
    Выполняет проверку IMEI через внешний API.
    Возвращает чистые данные устройства без технических деталей на грузинском языке.
    Всегда показывает все полученные данные, даже если они неполные.
    """
    # Генерируем ID запроса для отслеживания
    request_id = secrets.token_hex(8)
    logger.info(f"Starting API check [ID:{request_id}]: IMEI={imei}, service={service_type}")
    
    retries = 0
    last_response = None
    last_exception = None
    
    # Для платных сервисов делаем только 1 попытку
    max_attempts = MAX_RETRIES
    
    while retries <= max_attempts:
        try:
            # Проверка валидности IMEI
            if not validate_imei(imei):
                logger.warning(f"Invalid IMEI: {imei} for service {service_type}")
                return OrderedDict([
                    ('error', get_error_message('invalid_imei')),
                    ('service_type', service_type),
                    ('request_id', request_id)
                ])
            
            # Проверка поддерживаемого типа сервиса
            if service_type not in SERVICE_TYPES:
                logger.error(f"Unsupported service: {service_type}")
                return OrderedDict([
                    ('error', get_error_message('unsupported_service')),
                    ('details', f'Requested service: {service_type}'),
                    ('request_id', request_id)
                ])
            
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
                    logger.error(f"API error [ID:{request_id}]: {response.status_code} for IMEI {imei}")
                    
                    # Специальная проверка для ошибок баланса
                    response_text = response.text.lower()
                    balance_keywords = ['insufficient', 'funds', 'balance', 'credit']
                    if any(keyword in response_text for keyword in balance_keywords):
                        return OrderedDict([
                            ('error', get_error_message('insufficient_funds')),
                            ('status_code', response.status_code),
                            ('service_type', service_type),
                            ('request_id', request_id)
                        ])
                    
                    # Специальные коды ошибок
                    if response.status_code == 402:
                        return OrderedDict([
                            ('error', get_error_message('payment_required')),
                            ('status_code', response.status_code),
                            ('service_type', service_type),
                            ('request_id', request_id)
                        ])
                    elif response.status_code == 403:
                        return OrderedDict([
                            ('error', get_error_message('restricted_region')),
                            ('status_code', response.status_code),
                            ('service_type', service_type),
                            ('request_id', request_id)
                        ])
                    elif response.status_code == 429:
                        return OrderedDict([
                            ('error', get_error_message('rate_limit')),
                            ('status_code', response.status_code),
                            ('service_type', service_type),
                            ('request_id', request_id)
                        ])
                    elif response.status_code == 503:
                        return OrderedDict([
                            ('error', get_error_message('maintenance')),
                            ('status_code', response.status_code),
                            ('service_type', service_type),
                            ('request_id', request_id)
                        ])
                    
                    # Для платных сервисов сразу возвращаем ошибку
                    if service_type != 'free':
                        return OrderedDict([
                            ('error', get_error_message('server_error')),
                            ('status_code', response.status_code),
                            ('service_type', service_type),
                            ('server_response', filter_technical_fields(response.text)),
                            ('request_id', request_id)
                        ])
                    
                    # Для бесплатных сервисов пробуем повторить
                    if response.status_code >= 500 and retries < max_attempts:
                        retries += 1
                        logger.info(f"[ID:{request_id}] Retrying ({retries}/{max_attempts}) for IMEI {imei}")
                        time.sleep(RETRY_DELAY)
                        continue
                    
                    return OrderedDict([
                        ('error', get_error_message('server_error')),
                        ('status_code', response.status_code),
                        ('service_type', service_type),
                        ('server_response', filter_technical_fields(response.text)),
                        ('request_id', request_id)
                    ])
                
                # Сохраняем последний ответ для анализа
                last_response = response.text
                
                # Проверка на пустой ответ
                if not last_response.strip():
                    logger.warning(f"[ID:{request_id}] Empty API response for IMEI: {imei}")
                    
                    # Для платных сервисов сразу возвращаем ошибку
                    if service_type != 'free':
                        return OrderedDict([
                            ('error', get_error_message('empty_response', service_type)),
                            ('service_type', service_type),
                            ('server_response', filter_technical_fields(last_response)),
                            ('request_id', request_id)
                        ])
                    
                    if retries < max_attempts:
                        retries += 1
                        logger.info(f"[ID:{request_id}] Retrying ({retries}/{max_attempts}) for empty response")
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        return OrderedDict([
                            ('error', get_error_message('empty_response', service_type)),
                            ('service_type', service_type),
                            ('server_response', filter_technical_fields(last_response)),
                            ('request_id', request_id)
                        ])
                
                # Логируем факт запроса
                logger.info(f"[ID:{request_id}] API check for IMEI {imei}, service {service_type}. Time: {request_time:.2f}s")
                
                # Парсим ответ
                parsed_data = parse_universal_response(last_response)
                
                # Если в процессе парсинга возникла ошибка
                if 'error' in parsed_data:
                    parsed_data['request_id'] = request_id
                    return parsed_data
                
                # Дополнительная проверка на ошибку баланса
                if 'server_response' in parsed_data:
                    response_text = str(parsed_data['server_response']).lower()
                    balance_keywords = ['insufficient', 'funds', 'balance', 'credit']
                    if any(keyword in response_text for keyword in balance_keywords):
                        return OrderedDict([
                            ('error', get_error_message('insufficient_funds')),
                            ('service_type', service_type),
                            ('server_response', parsed_data['server_response']),
                            ('request_id', request_id)
                        ])
                
                # Добавляем IMEI для отслеживания
                parsed_data['imei'] = imei
                parsed_data['service_type'] = service_type
                parsed_data['request_id'] = request_id
                
                # Проверка на минимальное количество данных
                useful_keys = [k for k in parsed_data.keys() if k not in ['imei', 'server_response', 'service_type', 'request_id']]
                if len(useful_keys) < 2:
                    logger.warning(f"[ID:{request_id}] Incomplete data for IMEI: {imei}. Keys: {useful_keys}")
                    parsed_data['warning'] = get_error_message('incomplete_data')
                
                # Всегда возвращаем все полученные данные
                return parsed_data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"[ID:{request_id}] Network error for IMEI {imei}: {str(e)}")
            last_exception = str(e)
            
            # Специальная проверка для ошибок баланса
            error_msg = str(e).lower()
            balance_keywords = ['insufficient', 'funds', 'balance', 'credit']
            if any(keyword in error_msg for keyword in balance_keywords):
                return OrderedDict([
                    ('error', get_error_message('insufficient_funds')),
                    ('details', last_exception),
                    ('service_type', service_type),
                    ('request_id', request_id)
                ])
            
            # Для платных сервисов сразу возвращаем ошибку
            if service_type != 'free':
                return OrderedDict([
                    ('error', get_error_message('network_error')),
                    ('details', last_exception),
                    ('service_type', service_type),
                    ('request_id', request_id)
                ])
            
            if retries < max_attempts:
                retries += 1
                # Увеличиваем задержку с каждой попыткой
                current_delay = RETRY_DELAY * (retries + 1)
                logger.info(f"[ID:{request_id}] Retrying ({retries}/{max_attempts}) after network error. Delay: {current_delay}s")
                time.sleep(current_delay)
                continue
            else:
                return OrderedDict([
                    ('error', get_error_message('network_error')),
                    ('details', last_exception),
                    ('service_type', service_type),
                    ('request_id', request_id)
                ])
                
        except Exception as e:
            logger.error(f"[ID:{request_id}] Unexpected error for IMEI {imei}: {str(e)}")
            last_exception = str(e)
            
            # Специальная проверка для ошибок баланса
            error_msg = str(e).lower()
            balance_keywords = ['insufficient', 'funds', 'balance', 'credit']
            if any(keyword in error_msg for keyword in balance_keywords):
                return OrderedDict([
                    ('error', get_error_message('insufficient_funds')),
                    ('details', last_exception),
                    ('service_type', service_type),
                    ('request_id', request_id)
                ])
            
            return OrderedDict([
                ('error', get_error_message('unknown_error')),
                ('details', last_exception),
                ('service_type', service_type),
                ('server_response', filter_technical_fields(last_response) if last_response else "No response"),
                ('request_id', request_id)
            ])
    
    # Если превышено количество попыток
    logger.error(f"[ID:{request_id}] Max retries exceeded for IMEI: {imei}")
    return OrderedDict([
        ('error', get_error_message('max_retries_exceeded')),
        ('details', f'After {max_attempts} retries'),
        ('service_type', service_type),
        ('server_response', filter_technical_fields(last_response) if last_response else "No response"),
        ('request_id', request_id)
    ])

# Для обратной совместимости
parse_free_html = parse_universal_response
