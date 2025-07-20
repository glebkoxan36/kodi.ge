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
            
            # Список целевых сервисов
            target_services = ['748', '749', '750']
            service_list = []
            
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
                
                # Обработка только целевых сервисов
                for service_id in target_services:
                    if service_id in services_dict:
                        service_data = services_dict[service_id]
                        
                        # Пропускаем не-словари
                        if not isinstance(service_data, dict):
                            logger.warning(f"Skipping non-dict service data for ID {service_id}: {service_data}")
                            continue
                        
                        # Извлекаем данные сервиса
                        name = service_data.get('SERVICENAME', f'Service {service_id}')
                        price = service_data.get('CREDIT', '0')
                        info = service_data.get('INFO', '')
                        
                        # Форматируем цену
                        try:
                            price_value = float(price)
                            formatted_price = f"{price_value:.2f}"
                        except (ValueError, TypeError):
                            formatted_price = "0.00"
                        
                        # Определяем время обработки
                        time_info = "1-3 days"
                        if 'TIME' in service_data:
                            time_info = service_data['TIME'].title()
                        
                        # Очищаем описание от HTML-тегов
                        clean_info = re.sub(r'<[^>]+>', ' ', info).strip()
                        clean_info = re.sub(r'\s+', ' ', clean_info)
                        
                        # Создаем объект сервиса с полным описанием
                        service_list.append({
                            'id': service_id,
                            'name': name,
                            'price': formatted_price,
                            'description': clean_info,  # Полное описание
                            'time': time_info
                        })
                    else:
                        logger.warning(f"Target service ID {service_id} not found in API response")
            
            # Если целевые сервисы не найдены, используем первые 3 доступных
            if not service_list and services_dict:
                logger.warning("Target services not found, using first 3 available services")
                for i, (service_id, service_data) in enumerate(services_dict.items()):
                    if i >= 3:
                        break
                    
                    if not isinstance(service_data, dict):
                        continue
                    
                    name = service_data.get('SERVICENAME', f'Service {service_id}')
                    price = service_data.get('CREDIT', '0')
                    info = service_data.get('INFO', '')
                    
                    try:
                        formatted_price = f"{float(price):.2f}"
                    except (ValueError, TypeError):
                        formatted_price = "0.00"
                    
                    time_info = service_data.get('TIME', '1-3 days').title()
                    
                    clean_info = re.sub(r'<[^>]+>', ' ', info).strip()
                    clean_info = re.sub(r'\s+', ' ', clean_info)
                    
                    service_list.append({
                        'id': service_id,
                        'name': name,
                        'price': formatted_price,
                        'description': clean_info,
                        'time': time_info
                    })
            
            return service_list
        
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
