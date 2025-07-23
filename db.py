import os
import time
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError
from bson import ObjectId
from werkzeug.security import generate_password_hash

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля"""
    if not os.path.exists('logs'):
        os.makedirs('logs', exist_ok=True)
    handler = logging.FileHandler('logs/db.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

def init_mongodb():
    """Инициализирует подключение к MongoDB с повторными попытками"""
    logger.info("Initializing MongoDB connection")
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
            client.admin.command('ismaster')
            logger.info("Successfully connected to MongoDB")
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Connection attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unexpected error during connection: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logger.critical("Could not connect to MongoDB after multiple attempts")
    return None

def init_admin_user(db):
    """Создает администратора по умолчанию если не существует"""
    try:
        logger.info("Checking admin user existence")
        if db is None or db.admin_users is None:
            logger.error("Database or admin_users collection is not available")
            return
            
        if not db.admin_users.find_one({'username': 'admin'}):
            admin_password = os.getenv('ADMIN_PASSWORD', 'securepassword')
            db.admin_users.insert_one({
                'username': 'admin',
                'password': generate_password_hash(admin_password),
                'role': 'superadmin',
                'created_at': datetime.utcnow()
            })
            logger.info("Default admin user created")
    except PyMongoError as e:
        logger.error(f"MongoDB error creating admin user: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating admin user: {str(e)}")

# Инициализация подключения
logger.info("Initializing MongoDB client")
client = init_mongodb()

# Глобальные переменные для коллекций с явной инициализацией None
db = None
regular_users_collection = None
checks_collection = None
payments_collection = None
refunds_collection = None
prices_collection = None
comparisons_collection = None
phonebase_collection = None
admin_users_collection = None
parser_logs_collection = None
audit_logs_collection = None
api_keys_collection = None
webhooks_collection = None

# Инициализация коллекций
try:
    if client is not None:
        db = client['imei_checker']
        
        # Основные коллекции
        regular_users_collection = db['users']
        checks_collection = db['results']
        payments_collection = db['payments']
        refunds_collection = db['refunds']
        prices_collection = db['prices']
        comparisons_collection = db['comparisons']
        phonebase_collection = db['phonebase']
        admin_users_collection = db['admin_users']
        parser_logs_collection = db['parser_logs']
        audit_logs_collection = db['audit_logs']
        api_keys_collection = db['api_keys']
        webhooks_collection = db['webhooks']
        
        # Инициализация данных
        init_admin_user(db)
    else:
        raise Exception("MongoDB connection failed")
        
except PyMongoError as e:
    logger.error(f"MongoDB initialization error: {str(e)}")
    # Явное сохранение None для всех коллекций
    regular_users_collection = None
    checks_collection = None
    payments_collection = None
    refunds_collection = None
    prices_collection = None
    comparisons_collection = None
    phonebase_collection = None
    admin_users_collection = None
    parser_logs_collection = None
    audit_logs_collection = None
    api_keys_collection = None
    webhooks_collection = None
    
except Exception as e:
    logger.error(f"Unexpected initialization error: {str(e)}")
    # Явное сохранение None для всех коллекций
    regular_users_collection = None
    checks_collection = None
    payments_collection = None
    refunds_collection = None
    prices_collection = None
    comparisons_collection = None
    phonebase_collection = None
    admin_users_collection = None
    parser_logs_collection = None
    audit_logs_collection = None
    api_keys_collection = None
    webhooks_collection = None
