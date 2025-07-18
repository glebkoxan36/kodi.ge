import os
import logging
from datetime import datetime
from pymongo.errors import PyMongoError
from bson import ObjectId

# Импортируем глобальные коллекции из db
from db import prices_collection

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

def init_prices():
    """Инициализирует цены для всех сервисов если не существуют"""
    logger.info("Initializing service prices")
    try:
        if prices_collection and prices_collection.count_documents({}) == 0:
            prices_collection.insert_one({
                'type': 'current',
                'prices': DEFAULT_PRICES,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            logger.info("Default service prices initialized")
    except PyMongoError as e:
        logger.error(f"MongoDB error initializing prices: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error initializing prices: {str(e)}")

def get_current_prices():
    """Возвращает текущие цены для всех сервисов"""
    logger.info("Fetching current service prices")
    try:
        # Если коллекция цен недоступна, используем значения по умолчанию
        if prices_collection is None:
            logger.warning("Prices collection not available, using default prices")
            return DEFAULT_PRICES
            
        price_doc = prices_collection.find_one({'type': 'current'})
        
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
                try:
                    prices_collection.update_one(
                        {'_id': price_doc['_id']},
                        {'$set': {
                            'prices': current_prices,
                            'updated_at': datetime.utcnow()
                        }}
                    )
                    logger.info("Service prices structure updated")
                except PyMongoError as e:
                    logger.error(f"Error updating prices: {str(e)}")
                
            return current_prices
        return DEFAULT_PRICES
    except PyMongoError as e:
        logger.error(f"MongoDB error getting service prices: {str(e)}")
        return DEFAULT_PRICES
    except Exception as e:
        logger.error(f"Unexpected error getting service prices: {str(e)}")
        return DEFAULT_PRICES

def get_service_price(service_type):
    """Возвращает цену для конкретного сервиса"""
    try:
        prices = get_current_prices()
        return prices.get(service_type, 0)
    except Exception as e:
        logger.error(f"Error getting service price: {str(e)}")
        # Возвращаем безопасное значение по умолчанию
        return DEFAULT_PRICES.get(service_type, 0)
