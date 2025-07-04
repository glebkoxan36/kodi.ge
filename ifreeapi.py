import os
import re
import requests
import logging
from bs4 import BeautifulSoup

API_URL = os.getenv('API_URL', "https://api.ifreeicloud.co.uk")
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')

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
    
    # Новые Android сервисы из Ifreeandroidservice.pdf
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
    """Проверяет корректность формата IMEI"""
    return len(imei) == 15 and imei.isdigit()

def parse_free_json(data: dict) -> dict:
    """Парсит JSON-ответ бесплатной проверки IMEI для Android устройств"""
    # Словарь для перевода ключей на грузинский язык
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
    
    # Обработка и перевод ключей
    for key, value in data.items():
        # Переводим ключ если он есть в словаре, иначе оставляем оригинальный
        georgian_key = key_mapping.get(key, key)
        result[georgian_key] = value

    return result

def parse_free_html(html_content: str) -> dict:
    """Парсит HTML-ответ бесплатной проверки IMEI"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {}
        
        # 1. Парсинг табличных данных
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(':', '').replace(' ', '_').lower()
                    value = cols[1].get_text(strip=True)
                    result[key] = value

        # 2. Парсинг всех возможных пар ключ-значение
        pattern = re.compile(
            r'(Device|Model|Serial|IMEI|ICCID|FMI|Activation Status|'
            r'Blacklist Status|Sim Lock|MDM Status|Google Account Status|'
            r'Carrier|Purchase Date|Warranty Status|Activation Policy|'
            r'Network Lock|Coverage|Find My iPhone|iCloud Status|'
            r'Activation Lock|Last Restore|Factory Unlocked|Refurbished|'
            r'Replaced|Loaner|AppleCare|Blocked Status|Restore Status|'
            r'Activation Date|Purchase Country|Next Tether Policy|Sim Lock Policy)'
            r'[\s:]*', 
            re.IGNORECASE
        )
        
        for element in soup.find_all(string=pattern):
            match = pattern.search(element)
            if match:
                label = match.group(1).strip()
                key = label.replace(' ', '_').lower()
                
                # Поиск значения в структуре документа
                value = ""
                parent = element.parent
                
                # Случай 1: Значение в том же элементе после двоеточия
                if ':' in element:
                    value = element.split(':', 1)[1].strip()
                
                # Случай 2: Значение в соседнем элементе
                elif parent and parent.find_next_sibling():
                    value = parent.find_next_sibling().get_text(strip=True)
                
                # Случай 3: Значение в следующем текстовом узле
                elif element.next_sibling:
                    value = element.next_sibling.strip()
                
                if value:
                    result[key] = value

        # 3. Дополнительный сбор данных из заголовков и значений
        for header in soup.find_all(['h3', 'h4', 'strong', 'b']):
            text = header.get_text(strip=True)
            if ':' in text:
                key, value = text.split(':', 1)
                key = key.strip().replace(' ', '_').lower()
                result[key] = value.strip()
            elif header.next_sibling:
                key = text.replace(':', '').replace(' ', '_').lower()
                result[key] = header.next_sibling.strip()

        return result
    
    except Exception as e:
        logging.error(f"Advanced HTML parsing error: {str(e)}")
        return None

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
        
        # Для бесплатной проверки
        if service_type == 'free':
            try:
                # Пробуем обработать как JSON (Android устройства)
                json_data = response.json()
                if isinstance(json_data, dict) and 'status' in json_data:
                    return parse_free_json(json_data)
            except:
                pass
            
            # Если не JSON, обрабатываем как HTML (Apple устройства)
            return parse_free_html(response.text)
    
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
