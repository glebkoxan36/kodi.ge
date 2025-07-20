import requests
import logging
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
            
            # Логируем тип ответа для диагностики
            logger.info(f"API response type: {type(api_response)}")
            
            # Обработка словарного ответа API
            if isinstance(api_response, dict):
                # Ищем вложенный словарь с сервисами
                services_dict = None
                
                # Вариант 1: ключ 'LIST' содержит сервисы
                if 'LIST' in api_response and isinstance(api_response['LIST'], dict):
                    services_dict = api_response['LIST']
                # Вариант 2: весь ответ - это словарь сервисов (исключая системные поля)
                else:
                    services_dict = {}
                    for key, value in api_response.items():
                        # Пропускаем системные поля
                        if key in ['STATUS', 'MESSAGE']:
                            continue
                        if isinstance(value, dict):
                            services_dict[key] = value
                
                if not services_dict:
                    logger.error("No services found in API response")
                    return []
                
                logger.info(f"Processing {len(services_dict)} services")
                service_list = []
                
                for service_id, service_data in services_dict.items():
                    # Пропускаем не-словари
                    if not isinstance(service_data, dict):
                        continue
                    
                    # Форматируем цену
                    try:
                        price = float(service_data.get('price', 0))
                        formatted_price = f"{price:.2f}"
                    except (ValueError, TypeError):
                        formatted_price = "0.00"
                    
                    # Определяем время обработки
                    name = service_data.get('name', 'Unnamed Service')
                    if 'fast' in name.lower():
                        time_info = '24 hours'
                    elif 'standard' in name.lower():
                        time_info = '3-5 days'
                    else:
                        time_info = '1-3 days'
                    
                    service_list.append({
                        'id': str(service_id),
                        'name': name,
                        'price': formatted_price,
                        'description': service_data.get('description', ''),
                        'time': time_info
                    })
                
                return service_list
            
            # Обработка списка сервисов (если API вернет список)
            elif isinstance(api_response, list):
                service_list = []
                for service in api_response:
                    if not isinstance(service, dict):
                        continue
                    
                    # Форматируем цену
                    try:
                        price = float(service.get('price', 0))
                        formatted_price = f"{price:.2f}"
                    except (ValueError, TypeError):
                        formatted_price = "0.00"
                    
                    # Определяем время обработки
                    name = service.get('name', 'Unnamed Service')
                    if 'fast' in name.lower():
                        time_info = '24 hours'
                    elif 'standard' in name.lower():
                        time_info = '3-5 days'
                    else:
                        time_info = '1-3 days'
                    
                    service_list.append({
                        'id': str(service.get('id', '0')),
                        'name': name,
                        'price': formatted_price,
                        'description': service.get('description', ''),
                        'time': time_info
                    })
                
                return service_list
            
            else:
                logger.error(f"Unexpected API response format: {type(api_response)}")
                return []
        
        except Exception as e:
            logger.exception(f"API services error: {str(e)}")
            return []
    
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
