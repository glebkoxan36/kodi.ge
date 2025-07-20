import requests
import logging
import re
from flask import current_app

logger = logging.getLogger(__name__)

class UnlockAPI:
    BASE_URL = "https://pro.imei24.com/apii.php"
    
    def __init__(self, email, api_key):
        self.email = email
        self.api_key = api_key
    
    def get_services(self):
        """Получает список доступных сервисов разблокировки"""
        params = {
            'login': self.email,
            'apikey': self.api_key,
            'action': 'instantservicelist'
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            api_response = response.json()
            
            logger.info(f"API response: {api_response}")
            
            # Обработка основного формата ответа API
            if isinstance(api_response, dict):
                services_dict = {}
                
                # Вариант 1: сервисы находятся в ключе 'LIST'
                if 'LIST' in api_response and isinstance(api_response['LIST'], dict):
                    services_dict = api_response['LIST']
                    logger.info(f"Found services in 'LIST' key: {len(services_dict)} items")
                
                # Вариант 2: весь ответ - это словарь сервисов
                else:
                    for key, value in api_response.items():
                        # Пропускаем системные поля
                        if key in ['STATUS', 'MESSAGE']:
                            continue
                        if isinstance(value, dict):
                            services_dict[key] = value
                    logger.info(f"Extracted services from root: {len(services_dict)} items")
                
                # Обработка сервисов
                service_list = []
                for service_id, service_data in services_dict.items():
                    # Пропускаем не-словари
                    if not isinstance(service_data, dict):
                        logger.warning(f"Skipping non-dict service data: {service_data}")
                        continue
                    
                    # Извлекаем данные сервиса с использованием фактических ключей из API
                    name = service_data.get('SERVICENAME', 'Unnamed Service')
                    price = service_data.get('CREDIT', '0')
                    description = service_data.get('INFO', 'No description available')
                    
                    # Очистка HTML-тегов из описания
                    description = re.sub(r'<[^>]+>', ' ', description).strip()
                    description = re.sub(r'\s+', ' ', description)
                    
                    # Форматируем цену
                    try:
                        price_value = float(price)
                        formatted_price = f"{price_value:.2f}"
                    except (ValueError, TypeError):
                        formatted_price = "0.00"
                    
                    # Определяем время обработки на основе названия
                    time_info = self.determine_processing_time(name)
                    
                    # Создаем объект сервиса
                    service_list.append({
                        'id': str(service_id),
                        'name': name,
                        'price': formatted_price,
                        'description': description,
                        'time': time_info
                    })
                
                return service_list
            
            # Обработка формата ответа в виде списка
            elif isinstance(api_response, list):
                logger.info(f"Received list of services: {len(api_response)} items")
                service_list = []
                
                for service in api_response:
                    if not isinstance(service, dict):
                        continue
                    
                    # Извлекаем данные сервиса
                    service_id = service.get('id') or service.get('ID') or service.get('SERVICEID')
                    name = service.get('name') or service.get('Name') or service.get('SERVICENAME')
                    price = service.get('price') or service.get('Price') or service.get('CREDIT')
                    description = service.get('description') or service.get('Description') or service.get('INFO')
                    
                    # Очистка HTML-тегов из описания
                    if description:
                        description = re.sub(r'<[^>]+>', ' ', description).strip()
                        description = re.sub(r'\s+', ' ', description)
                    
                    # Форматируем цену
                    try:
                        price_value = float(price)
                        formatted_price = f"{price_value:.2f}"
                    except (ValueError, TypeError):
                        formatted_price = "0.00"
                    
                    # Определяем время обработки
                    time_info = self.determine_processing_time(name)
                    
                    # Создаем объект сервиса
                    service_list.append({
                        'id': str(service_id) if service_id else "0",
                        'name': name or "Unlock Service",
                        'price': formatted_price,
                        'description': description or "No description available",
                        'time': time_info
                    })
                
                return service_list
            
            else:
                logger.error(f"Unexpected API response format: {type(api_response)}")
                return []
        
        except Exception as e:
            logger.exception(f"API services error: {str(e)}")
            return []
    
    def determine_processing_time(self, name):
        """Определяет время обработки на основе названия сервиса"""
        if not name:
            return '1-3 days'
            
        name_lower = name.lower()
        
        if 'instant' in name_lower:
            return 'Instant'
        elif 'fast' in name_lower:
            return '24 hours'
        elif 'standard' in name_lower:
            return '3-5 days'
        else:
            # Попытка извлечь время из названия
            match = re.search(r'(\d+[\s-]*hours?)', name_lower)
            if match:
                return match.group(0).title()
            
            match = re.search(r'(\d+[\s-]*days?)', name_lower)
            if match:
                return match.group(0).title()
            
            return '1-3 days'
    
    def place_order(self, imei, service_id):
        """Отправляет заказ на разблокировку"""
        params = {
            'login': self.email,
            'apikey': self.api_key,
            'action': 'placeorder',
            'imei': imei,
            'id': service_id
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"API place order error: {str(e)}")
            return {'STATUS': 'error', 'MESSAGE': 'API connection failed'}
    
    def get_order_status(self, refid):
        """Проверяет статус заказа по REFID"""
        params = {
            'login': self.email,
            'apikey': self.api_key,
            'action': 'getimeiorder',
            'refid': refid
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"API order status error: {str(e)}")
            return {'STATUS': 'error', 'MESSAGE': 'API connection failed'}


def init_unlock_service():
    """Инициализирует сервис разблокировки"""
    email = current_app.config.get('UNLOCK_API_EMAIL', 'glebkoxan36@gmail.com')
    api_key = current_app.config.get('UNLOCK_API_KEY', 'YHN-H96-H1F-OA1-AF7-3HX-9BV-MXF')
    return UnlockAPI(email, api_key)
