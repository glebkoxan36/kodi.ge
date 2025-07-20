import requests
import re
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
            services = response.json()
            
            # Логируем тип ответа для диагностики
            logger.info(f"API response type: {type(services)}")
            
            # Если ответ - список, обрабатываем как список
            if isinstance(services, list):
                logger.info(f"Received {len(services)} services")
                
                # Добавляем время обработки для каждого сервиса
                for service in services:
                    # Проверяем наличие обязательных полей
                    if 'id' not in service or 'name' not in service or 'price' not in service:
                        logger.error(f"Service missing required fields: {service}")
                        continue
                    
                    # Форматируем цену
                    try:
                        service['price'] = f"{float(service['price']):.2f}"
                    except (ValueError, TypeError):
                        service['price'] = "0.00"
                    
                    # Определяем время обработки
                    if 'fast' in service['name'].lower():
                        service['time'] = '24 hours'
                    elif 'standard' in service['name'].lower():
                        service['time'] = '3-5 days'
                    else:
                        service['time'] = '1-3 days'
                
                return services
            
            # Если ответ - словарь, преобразуем его в список
            elif isinstance(services, dict):
                logger.info(f"Received dictionary with {len(services)} services")
                
                service_list = []
                for service_id, service_info in services.items():
                    # Проверяем, что значение - словарь
                    if not isinstance(service_info, dict):
                        logger.warning(f"Invalid service format: {service_info}")
                        continue
                    
                    # Форматируем цену
                    try:
                        price = f"{float(service_info.get('price', 0)):.2f}"
                    except (ValueError, TypeError):
                        price = "0.00"
                    
                    # Определяем время обработки
                    name = service_info.get('name', '')
                    if 'fast' in name.lower():
                        time_info = '24 hours'
                    elif 'standard' in name.lower():
                        time_info = '3-5 days'
                    else:
                        time_info = '1-3 days'
                    
                    service_list.append({
                        'id': service_id,
                        'name': name,
                        'price': price,
                        'description': service_info.get('description', ''),
                        'time': time_info
                    })
                
                return service_list
            
            else:
                logger.error(f"Unexpected API response format: {type(services)}")
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
