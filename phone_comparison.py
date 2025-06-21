import os
import re
import requests
import logging
from bson import ObjectId
from pymongo import MongoClient
from flask import jsonify
from datetime import datetime

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Конфигурация
MONGODB_URI = os.getenv('MONGODB_URI')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
PLACEHOLDER = '/static/placeholder.jpg'

# Подключение к MongoDB с использованием стандартного URI
try:
    client = MongoClient(MONGODB_URI)
    phone_db = client.get_database()
    phones_collection = phone_db['phones']
    logger.info("Connected to MongoDB using MONGODB_URI")
except Exception as e:
    logger.error(f"DB connection failed: {str(e)}")
    # Fallback на локальную базу
    try:
        client = MongoClient()
        phone_db = client['imei_checker']
        phones_collection = phone_db['phones']
        logger.info("Using local database for phone specs")
    except Exception as e2:
        logger.error(f"Local DB connection failed: {str(e2)}")
        # Создаем пустую коллекцию, чтобы избежать ошибок выполнения
        from pymongo import MongoClient
        client = MongoClient()
        phone_db = client['dummy_phone_db']
        phones_collection = phone_db['dummy_phones']
        logger.info("Using dummy in-memory collection for phone specs")

# Подключение к базе для истории сравнений
try:
    history_client = MongoClient(MONGODB_URI)
    history_db = history_client.get_database()
    comparisons_collection = history_db['comparisons']
    logger.info("Connected to history DB")
except Exception as e:
    logger.error(f"History DB connection failed: {str(e)}")
    comparisons_collection = None
    logger.info("Using in-memory storage for comparisons")

def search_phones(query):
    """Поиск телефонов по названию, бренду или модели"""
    try:
        regex_query = {'$regex': f'.*{re.escape(query)}.*', '$options': 'i'}
        results = list(phones_collection.find({
            '$or': [
                {'brand': regex_query},
                {'model': regex_query},
                {'Name': regex_query}
            ]
        }, {'_id': 1, 'Name': 1, 'brand': 1, 'model': 1}).limit(10))
        
        normalized = []
        for phone in results:
            name = phone.get('Name', '')
            if not name:
                name = f"{phone.get('brand', '')} {phone.get('model', '')}".strip()
                
            normalized.append({
                '_id': str(phone['_id']),
                'name': name or 'Unknown Phone',
                'image_url': PLACEHOLDER
            })
        
        return normalized
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return []

def get_phone_details(phone_id):
    """Получение детальной информации о телефоне"""
    try:
        phone = phones_collection.find_one({'_id': ObjectId(phone_id)})
        if not phone:
            return None
        
        name = phone.get('Name', '')
        if not name:
            name = f"{phone.get('brand', '')} {phone.get('model', '')}".strip()
        
        specs = {}
        for key, value in phone.items():
            if key not in ['_id', 'Name', 'brand', 'model']:
                if isinstance(value, ObjectId):
                    value = str(value)
                elif isinstance(value, list):
                    value = ', '.join(map(str, value))
                elif isinstance(value, float) and value.is_integer():
                    value = int(value)
                
                specs[key] = value
        
        return {
            '_id': str(phone['_id']),
            'name': name or 'Unknown Phone',
            'image_url': PLACEHOLDER,
            'specs': specs
        }
    
    except Exception as e:
        logger.error(f"Details error: {str(e)}")
        return None

def perform_ai_comparison(phone1, phone2):
    """Выполнение AI-сравнения двух телефонов"""
    try:
        phone1_name = phone1.get('name', 'Unknown Phone 1')
        phone2_name = phone2.get('name', 'Unknown Phone 2')
        
        phone1_specs = "\n".join([f"{key}: {value}" for key, value in phone1.get('specs', {}).items()])
        phone2_specs = "\n".join([f"{key}: {value}" for key, value in phone2.get('specs', {}).items()])
        
        prompt = f"""
            შედარება: {phone1_name} vs {phone2_name}
            
            {phone1_name} მახასიათებლები:
            {phone1_specs}
            
            {phone2_name} მახასიათებლები:
            {phone2_specs}
            
            გთხოვთ შეადაროთ შემდეგი კატეგორიები:
            - პროდუქტიულობა
            - ეკრანის ხარისხი
            - კამერა
            - ბატარეის ხანგრძლივობა
            - დიზაინი
            - ფასი და ღირებულება
            
            გთხოვთ მოგვაწოდოთ დეტალური ანალიზი ქართულ ენაზე.
        """
        
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=30
        )
        response.raise_for_status()
        
        ai_response = response.json()
        content = ai_response['choices'][0]['message']['content']
        
        if comparisons_collection is not None:
            try:
                comparisons_collection.insert_one({
                    'phone1': phone1_name,
                    'phone2': phone2_name,
                    'timestamp': datetime.utcnow(),
                    'ai_response': content
                })
            except Exception as e:
                logger.error(f"Failed to save comparison: {str(e)}")
        
        return content
    
    except requests.exceptions.RequestException as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        return "AI service unavailable"
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        return "Internal server error"
