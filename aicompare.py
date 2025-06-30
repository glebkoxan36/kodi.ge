import os
import json
import logging
import re
import hashlib
import secrets
from datetime import datetime
from bson import ObjectId
from image_search import search_phone_image
import cohere

# Инициализация логгера модуля
logger = logging.getLogger(__name__)

# Глобальная ссылка на коллекцию
techspecs_collection = None
PLACEHOLDER = '/static/placeholder.jpg'

# Инициализация API клиентов
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    GEMINI_AVAILABLE = True
except Exception as e:
    logger.warning(f"Gemini initialization failed: {str(e)}")
    GEMINI_AVAILABLE = False

try:
    cohere_client = cohere.Client(os.getenv('COHERE_API_KEY'))
    COHERE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Cohere initialization failed: {str(e)}")
    COHERE_AVAILABLE = False

def init_techspecs_collection(collection):
    global techspecs_collection
    techspecs_collection = collection
    logger.info("Techspecs collection initialized in aicompare")

def generate_avatar_color(name):
    if not name:
        return "#{:06x}".format(secrets.randbelow(0xFFFFFF))
    hash_obj = hashlib.md5(name.encode('utf-8'))
    return '#' + hash_obj.hexdigest()[:6]

def ai_search_phones(query):
    """Поиск телефонов с приоритетом кэша MongoDB (максимум 3 результата)"""
    if techspecs_collection is None:
        logger.error("Techspecs collection not initialized")
        return []

    # Очистка и нормализация запроса
    clean_query = re.sub(r'[^\w\s]', '', query).strip().lower()
    if not clean_query or len(clean_query) < 3:
        return []

    try:
        # Объединенный поиск (бренд + модель + текст) с лимитом 3
        results = list(techspecs_collection.find(
            {
                "$or": [
                    {"brand": {"$regex": f"^{clean_query}$", "$options": "i"}},
                    {"model": {"$regex": clean_query, "$options": "i"}},
                    {"$text": {"$search": clean_query}}
                ]
            },
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(3))

        if results:
            logger.info(f"Found {len(results)} cached results for: {clean_query}")
            return format_cached_results(results)

        # Если в кеше нет - используем AI (запрашиваем 3 модели)
        return search_with_ai(clean_query)
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return []

def format_cached_results(cached_results):
    """Форматирование результатов из MongoDB (только необходимые поля)"""
    return [{
        'brand': phone.get('brand', 'N/A'),
        'model': phone.get('model', 'N/A'),
        'image_url': phone.get('image_url', PLACEHOLDER),
        '_id': phone['_id']
    } for phone in cached_results]

def search_with_ai(query):
    """Поиск телефонов через API с fallback"""
    try:
        # Сначала пытаемся использовать Cohere
        if COHERE_AVAILABLE:
            return search_with_cohere(query)
        
        # Если Cohere недоступен, используем Gemini
        if GEMINI_AVAILABLE:
            return search_with_gemini(query)
        
        # Если оба API недоступны
        logger.error("Both Cohere and Gemini APIs are unavailable")
        return []
    
    except Exception as e:
        logger.error(f"AI search error: {str(e)}")
        return []

def search_with_gemini(query):
    """Поиск через Gemini API (3 модели)"""
    try:
        logger.info(f"Searching with Gemini: {query}")
        prompt = f"""
        შექმენით JSON სია 3 ყველაზე პოპულარული სმარტფონის შესახებ, რომლებიც შეესაბამება: '{query}'.
        ველები თითოეული ტელეფონისთვის:
        - brand: ბრენდი
        - model: მოდელის სახელი
        - release_year: გამოშვების წელი
        - display: ეკრანის დიაგონალი და ტიპი
        - processor: პროცესორი
        - ram: ოპერატიული მეხსიერება
        - storage: შიდა მეხსიერება
        - camera: კამერის სპეციფიკაცია
        - battery: ბატარეის ტევადობა
        - os: ოპერაციული სისტემა
        
        გამოიტანეთ მხოლოდ JSON მასივი.
        """

        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Очистка ответа
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        phones = json.loads(response_text)
        return cache_and_format_results(phones)
    
    except json.JSONDecodeError as e:
        logger.error(f"Gemini JSON decode error: {str(e)}")
        logger.debug(f"Raw Gemini response: {response_text[:500]}")
        return []
    except Exception as e:
        logger.error(f"Gemini search error: {str(e)}")
        return []

def search_with_cohere(query):
    """Поиск через Cohere API (3 модели)"""
    try:
        logger.info(f"Searching with Cohere: {query}")
        prompt = f"""
        შექმენით JSON სია 3 ყველაზე პოპულარული სმარტფონის შესახებ, რომლებიც შეესაბამება: '{query}'.
        ველები თითოეული ტელეფონისთვის:
        - brand: ბრენდი
        - model: მოდელის სახელი
        - release_year: გამოშვების წელი
        - display: ეკრანის დიაგონალი და ტიპი
        - processor: პროცესორი
        - ram: ოპერატიული მეხსიერება
        - storage: შიდა მეხსიერება
        - camera: კამერის სპეციფიკაცია
        - battery: ბატარეის ტევადობა
        - os: ოპერაციული სისტემა
        
        გამოიტანეთ მხოლოდ JSON მასივი.
        """
        
        response = cohere_client.generate(
            model='command',
            prompt=prompt,
            max_tokens=2000,
            temperature=0.5,
            stop_sequences=["\n\n"]
        )
        
        response_text = response.generations[0].text.strip()
        
        # Очистка ответа
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        # Удаление возможных префиксов
        if response_text.startswith('JSON:'):
            response_text = response_text[5:].strip()
        
        phones = json.loads(response_text)
        return cache_and_format_results(phones)
        
    except json.JSONDecodeError as e:
        logger.error(f"Cohere JSON decode error: {str(e)}")
        logger.debug(f"Raw Cohere response: {response_text[:500]}")
        return []
    except Exception as e:
        logger.error(f"Cohere search error: {str(e)}")
        return []

def cache_and_format_results(phones):
    """Кэширование результатов в MongoDB и форматирование (максимум 3 модели)"""
    formatted = []
    for phone in phones[:3]:  # Ограничиваем до 3 моделей
        # Генерация ID
        phone_id = f"{phone['brand']}_{phone['model']}" \
            .replace(' ', '_') \
            .replace('/', '_') \
            .replace('.', '') \
            .replace("'", "") \
            .lower()
        
        # Проверяем, есть ли уже такой телефон в базе
        if techspecs_collection is not None:
            existing = techspecs_collection.find_one({'_id': phone_id})
            if existing:
                # Используем существующий
                formatted.append({
                    'brand': existing.get('brand', 'N/A'),
                    'model': existing.get('model', 'N/A'),
                    'image_url': existing.get('image_url', PLACEHOLDER),
                    '_id': existing['_id']
                })
                continue
        
        # Поиск изображения
        image_url = search_phone_image(f"{phone['brand']} {phone['model']}")
        
        # Подготовка документа
        doc = {
            '_id': phone_id,
            'brand': phone.get('brand', 'N/A'),
            'model': phone.get('model', 'N/A'),
            'release_year': phone.get('release_year', 'N/A'),
            'display': phone.get('display', 'N/A'),
            'processor': phone.get('processor', 'N/A'),
            'ram': phone.get('ram', 'N/A'),
            'storage': phone.get('storage', 'N/A'),
            'camera': phone.get('camera', 'N/A'),
            'battery': phone.get('battery', 'N/A'),
            'os': phone.get('os', 'N/A'),
            'image_url': image_url if image_url else PLACEHOLDER,
            'search_text': f"{phone['brand']} {phone['model']}",
            'last_updated': datetime.utcnow()
        }
        
        # Сохранение в MongoDB
        if techspecs_collection is not None:
            techspecs_collection.update_one(
                {'_id': phone_id},
                {'$set': doc},
                upsert=True
            )
        
        # Форматирование для ответа
        formatted.append({
            'brand': doc['brand'],
            'model': doc['model'],
            'image_url': doc['image_url'],
            '_id': phone_id
        })
    
    return formatted

def ai_compare_phones(phone1_id, phone2_id, user_id=None):
    """Сравнение двух телефонов с помощью AI"""
    if techspecs_collection is None:
        return {"error": "Database unavailable"}
    
    try:
        # Сначала пытаемся использовать Cohere
        if COHERE_AVAILABLE:
            return compare_with_cohere(phone1_id, phone2_id, user_id)
        
        # Если Cohere недоступен, используем Gemini
        if GEMINI_AVAILABLE:
            return compare_with_gemini(phone1_id, phone2_id, user_id)
        
        # Если оба API недоступны
        return {"error": "Both AI services are unavailable"}
    
    except Exception as e:
        logger.error(f"Comparison error: {str(e)}")
        return {"error": "AI service unavailable"}

def compare_with_gemini(phone1_id, phone2_id, user_id):
    """Сравнение через Gemini API"""
    phone1 = techspecs_collection.find_one({'_id': phone1_id})
    phone2 = techspecs_collection.find_one({'_id': phone2_id})
    
    if not phone1 or not phone2:
        return {"error": "Phone data not available"}
    
    try:
        logger.info(f"Comparing with Gemini: {phone1_id} vs {phone2_id}")
        # Формируем промпт для сравнения
        prompt = f"""
        შეადარეთ ორი სმარტფონი: 
        Phone 1: {phone1['brand']} {phone1['model']} 
        Phone 2: {phone2['brand']} {phone2['model']}
        
        დეტალური შედარება კატეგორიების მიხედვით:
        1. დიზაინი
        2. ეკრანი
        3. პროდუქტიულობა
        4. კამერა
        5. ბატარეა
        6. ოპერაციული სისტემა
        7. დამატებითი ფუნქციები
        8. ფასი
        
        JSON ფორმატი:
        {{
            "comparison": [
                {{
                    "category": "კატეგორია",
                    "phone1_advantage": "უპირატესობა 1",
                    "phone2_advantage": "უპირატესობა 2",
                    "winner": "phone1/phone2"
                }}
            ],
            "overall_winner": "phone1/phone2",
            "summary": "დასკვნა"
        }}
        """

        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Очистка ответа
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        comparison = json.loads(response_text)
        save_comparison(phone1, phone2, comparison, user_id)
        return comparison
    except json.JSONDecodeError as e:
        logger.error(f"Gemini comparison JSON error: {str(e)}")
        logger.debug(f"Raw Gemini response: {response_text[:500]}")
        return {"error": "Invalid response format"}
    except Exception as e:
        logger.error(f"Gemini comparison error: {str(e)}")
        return {"error": "AI service failed"}

def compare_with_cohere(phone1_id, phone2_id, user_id):
    """Сравнение через Cohere API"""
    phone1 = techspecs_collection.find_one({'_id': phone1_id})
    phone2 = techspecs_collection.find_one({'_id': phone2_id})
    
    if not phone1 or not phone2:
        return {"error": "Phone data not available"}
    
    try:
        logger.info(f"Comparing with Cohere: {phone1_id} vs {phone2_id}")
        prompt = f"""
        შეადარეთ ორი სმარტფონი: 
        Phone 1: {phone1['brand']} {phone1['model']} 
        Phone 2: {phone2['brand']} {phone2['model']}
        
        დეტალური შედარება კატეგორიების მიხედვით:
        1. დიზაინი
        2. ეკრანი
        3. პროდუქტიულობა
        4. კამერა
        5. ბატარეა
        6. ოპერაციული სისტემა
        7. დამატებითი ფუნქციები
        8. ფასი
        
        JSON ფორმატი:
        {{
            "comparison": [
                {{
                    "category": "კატეგორია",
                    "phone1_advantage": "უპირატესობა 1",
                    "phone2_advantage": "უპირატესობა 2",
                    "winner": "phone1/phone2"
                }}
            ],
            "overall_winner": "phone1/phone2",
            "summary": "დასკვნა"
        }}
        """
        
        response = cohere_client.generate(
            model='command',
            prompt=prompt,
            max_tokens=3000,
            temperature=0.3,
            stop_sequences=["\n\n"]
        )
        
        response_text = response.generations[0].text.strip()
        
        # Очистка ответа
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        # Удаление возможных префиксов
        if response_text.startswith('JSON:'):
            response_text = response_text[5:].strip()
        
        comparison = json.loads(response_text)
        save_comparison(phone1, phone2, comparison, user_id)
        return comparison
        
    except json.JSONDecodeError as e:
        logger.error(f"Cohere comparison JSON error: {str(e)}")
        logger.debug(f"Raw Cohere response: {response_text[:500]}")
        return {"error": "Invalid response format"}
    except Exception as e:
        logger.error(f"Cohere comparison error: {str(e)}")
        return {"error": "Comparison service failed"}

def save_comparison(phone1, phone2, comparison, user_id):
    """Сохранение результатов сравнения в базу"""
    from app import comparisons_collection
    
    if comparisons_collection is None:
        return
        
    comparisons_collection.insert_one({
        'phone1_id': phone1['_id'],
        'phone2_id': phone2['_id'],
        'phone1_name': f"{phone1['brand']} {phone1['model']}",
        'phone2_name': f"{phone2['brand']} {phone2['model']}",
        'comparison': comparison,
        'timestamp': datetime.utcnow(),
        'user_id': ObjectId(user_id) if user_id else None
    })
