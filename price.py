import os
import logging
from datetime import datetime
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Стандартные цены в центах
DEFAULT_PRICES = {
    'fmi': 200,           # 2.00 GEL
    'blacklist': 300,      # 3.00 GEL
    'sim_lock': 250,       # 2.50 GEL
    'activation': 150,     # 1.50 GEL
    'carrier': 200,        # 2.00 GEL
    'mdm': 180,            # 1.80 GEL
    'samsung_v1': 220,
    'samsung_v2': 280,
    'samsung_knox': 320,
    'xiaomi': 240,
    'google_pixel': 260,
    'huawei_v1': 230,
    'huawei_v2': 290,
    'motorola': 210,
    'oppo': 250,
    'frp': 190,
    'sim_lock_android': 220
}

def init_prices():
    """Инициализация цен в базе данных"""
    try:
        if not prices_collection:
            logger.warning("Prices collection not available")
            return
            
        if prices_collection.count_documents({}) == 0:
            price_doc = {
                'prices': DEFAULT_PRICES,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            prices_collection.insert_one(price_doc)
            logger.info("Default prices initialized")
    except Exception as e:
        logger.error(f"Error initializing prices: {str(e)}")

def get_current_prices():
    """Возвращает текущие цены из базы"""
    try:
        if prices_collection:
            prices_doc = prices_collection.find_one(sort=[('updated_at', -1)])
            if prices_doc:
                return prices_doc.get('prices', {})
        return DEFAULT_PRICES
    except Exception as e:
        logger.error(f"Error getting prices: {str(e)}")
        return DEFAULT_PRICES

def get_service_price(service_type):
    """Возвращает цену сервиса в центах"""
    prices = get_current_prices()
    return prices.get(service_type, 200)  # Стандартная цена 2.00 GEL
