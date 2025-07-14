import os
import time
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash

# Цены по умолчанию
DEFAULT_PRICES = {
    'paid': 499,
    'premium': 999
}

def init_mongodb():
    """Инициализирует подключение к MongoDB с повторными попытками"""
    max_retries = 5
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            client = MongoClient(
                os.getenv('MONGODB_URI'), 
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=15000,
                retryWrites=True,
                w='majority'
            )
            # Проверка подключения
            client.admin.command('ismaster')
            print("Successfully connected to MongoDB")
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"MongoDB connection attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    print("Could not connect to MongoDB after multiple attempts")
    return None

def init_admin_user(db):
    """Создает администратора по умолчанию если не существует"""
    try:
        if not db.admin_users.find_one({'username': 'admin'}):
            admin_password = os.getenv('ADMIN_PASSWORD', 'securepassword')
            db.admin_users.insert_one({
                'username': 'admin',
                'password': generate_password_hash(admin_password),
                'role': 'superadmin',
                'created_at': datetime.utcnow()
            })
            print("Default admin user created")
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")

def init_prices(db):
    """Инициализирует цены по умолчанию если не существуют"""
    try:
        if db.prices.count_documents({}) == 0:
            db.prices.insert_one({
                'type': 'current',
                'prices': DEFAULT_PRICES,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            print("Default prices initialized")
    except Exception as e:
        print(f"Error initializing prices: {str(e)}")

# Инициализация подключения
client = init_mongodb()

if client:
    db = client['imei_checker']
    
    # Основные коллекции
    regular_users_collection = db['users']
    checks_collection = db['results']
    payments_collection = db['payments']
    refunds_collection = db['refunds']
    prices_collection = db['prices']
    comparisons_collection = db['comparisons']
    phonebase_collection = db['phonebase']
    
    # Инициализация данных
    init_admin_user(db)
    init_prices(db)
else:
    # Заглушки для случая ошибки подключения
    regular_users_collection = None
    checks_collection = None
    payments_collection = None
    refunds_collection = None
    prices_collection = None
    comparisons_collection = None
    phonebase_collection = None

def get_current_prices():
    """Возвращает текущие цены из базы данных"""
    if not client:
        return DEFAULT_PRICES
        
    try:
        price_doc = prices_collection.find_one({'type': 'current'})
        if price_doc:
            return price_doc['prices']
        return DEFAULT_PRICES
    except Exception as e:
        print(f"Error getting prices: {str(e)}")
        return DEFAULT_PRICES
