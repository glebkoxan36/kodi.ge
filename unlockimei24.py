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
            return response.json()
        except Exception as e:
            logger.error(f"API services error: {str(e)}")
            return {}
    
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
            logger.error(f"API place order error: {str(e)}")
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
            logger.error(f"API order status error: {str(e)}")
            return {'STATUS': 'error', 'MESSAGE': 'API connection failed'}


def init_unlock_service():
    """Инициализирует сервис разблокировки"""
    email = current_app.config.get('UNLOCK_API_EMAIL', 'glebkoxan36@gmail.com')
    api_key = current_app.config.get('UNLOCK_API_KEY', 'YHN-H96-H1F-OA1-AF7-3HX-9BV-MXF')
    return UnlockAPI(email, api_key)
