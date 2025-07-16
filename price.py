import os
import logging
from datetime import datetime
from flask import current_app
from bson import ObjectId

# Логгер
logger = logging.getLogger(__name__)

# Цены по умолчанию для всех сервисов (в центах)
DEFAULT_PRICES = {
    # Apple services
    'fmi': 499,
    'blacklist': 499,
    'sim_lock': 999,
    'activation': 499,
    'carrier': 499,
    'mdm': 999,
    
    # Android services
    'samsung_v1': 499,
    'samsung_v2': 499,
    'samsung_knox': 999,
    'xiaomi': 499,
    'google_pixel': 499,
    'huawei_v1': 499,
    'huawei_v2': 499,
    'motorola': 499,
    'oppo': 499,
    'frp': 499,
    'sim_lock_android': 499,
    
    # Common
    'free': 0
}

def init_prices(db):
    """Инициализирует цены для всех сервисов если не существуют"""
    logger.info("Initializing service prices")
    try:
        if db.prices.count_documents({}) == 0:
            db.prices.insert_one({
                'type': 'current',
                'prices': DEFAULT_PRICES,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            logger.info("Default service prices initialized")
    except Exception as e:
        logger.error(f"Error initializing prices: {str(e)}")

def get_current_prices():
    """Возвращает текущие цены для всех сервисов"""
    logger.info("Fetching current service prices")
    try:
        # Используем контекст приложения для доступа к базе данных
        with current_app.app_context():
            if current_app.config.get('TESTING', False):
                return DEFAULT_PRICES
                
            db = current_app.extensions['pymongo'].db
            price_doc = db.prices.find_one({'type': 'current'})
            
            if price_doc:
                # Обновляем структуру если нужно
                updated = False
                current_prices = price_doc['prices']
                
                # Добавляем отсутствующие сервисы
                for service, default_price in DEFAULT_PRICES.items():
                    if service not in current_prices:
                        current_prices[service] = default_price
                        updated = True
                
                # Удаляем устаревшие сервисы
                for service in list(current_prices.keys()):
                    if service not in DEFAULT_PRICES:
                        del current_prices[service]
                        updated = True
                
                # Сохраняем обновленные цены
                if updated:
                    db.prices.update_one(
                        {'_id': price_doc['_id']},
                        {'$set': {
                            'prices': current_prices,
                            'updated_at': datetime.utcnow()
                        }}
                    )
                    logger.info("Service prices structure updated")
                
                return current_prices
            return DEFAULT_PRICES
    except Exception as e:
        logger.error(f"Error getting service prices: {str(e)}")
        return DEFAULT_PRICES

def get_service_price(service_type):
    """Возвращает цену для конкретного сервиса"""
    prices = get_current_prices()
    return prices.get(service_type, 0)
