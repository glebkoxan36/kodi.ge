import os
import json
import logging
import re
import hashlib
import secrets
from datetime import datetime
from bson import ObjectId
from image_search import search_phone_image
from app import app  # Для доступа к логгеру и конфигурации

# Глобальная ссылка на коллекцию
techspecs_collection = None
PLACEHOLDER = '/static/placeholder.jpg'

def init_techspecs_collection(collection):
    global techspecs_collection
    techspecs_collection = collection
    app.logger.info("Techspecs collection initialized in aicompare")

def generate_avatar_color(name):
    if not name:
        return "#{:06x}".format(secrets.randbelow(0xFFFFFF))
    hash_obj = hashlib.md5(name.encode('utf-8'))
    return '#' + hash_obj.hexdigest()[:6]

def ai_search_phones(query):
    """Поиск телефонов с приоритетом кэша MongoDB"""
    if not techspecs_collection:
        app.logger.error("Techspecs collection not initialized")
        return []

    try:
        # Поиск в MongoDB (кеше)
        cached_results = list(techspecs_collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(10))

        if cached_results:
            app.logger.info(f"Found {len(cached_results)} cached results for: {query}")
            return format_cached_results(cached_results)

        # Если в кеше нет - используем AI
        return search_with_ai(query)
    
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return []

def format_cached_results(cached_results):
    """Форматирование результатов из MongoDB"""
    formatted = []
    for phone in cached_results:
        formatted.append({
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
            'image_url': phone.get('image_url', PLACEHOLDER),
            '_id': phone['_id']
        })
    return formatted

def search_with_ai(query):
    """Поиск телефонов через Gemini API"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        შექმენით JSON სია 10 ყველაზე პოპულარული სმარტფონის შესახებ, რომლებიც შეესაბამება: '{query}'.
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

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Очистка ответа
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        phones = json.loads(response_text)
        return cache_and_format_results(phones)
    
    except json.JSONDecodeError:
        app.logger.error(f"JSON decode error. Raw response: {response_text[:200]}")
        return []
    except Exception as e:
        app.logger.error(f"AI search error: {str(e)}")
        return []

def cache_and_format_results(phones):
    """Кэширование результатов в MongoDB и форматирование"""
    formatted = []
    for phone in phones:
        # Генерация ID
        phone_id = f"{phone['brand']}_{phone['model']}" \
            .replace(' ', '_') \
            .replace('/', '_') \
            .replace('.', '') \
            .replace("'", "") \
            .lower()
        
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
        if techspecs_collection:
            techspecs_collection.update_one(
                {'_id': phone_id},
                {'$set': doc},
                upsert=True
            )
        
        # Форматирование для ответа
        formatted.append({
            'brand': doc['brand'],
            'model': doc['model'],
            'release_year': doc['release_year'],
            'display': doc['display'],
            'processor': doc['processor'],
            'ram': doc['ram'],
            'storage': doc['storage'],
            'camera': doc['camera'],
            'battery': doc['battery'],
            'os': doc['os'],
            'image_url': doc['image_url'],
            '_id': phone_id
        })
    
    return formatted

def ai_compare_phones(phone1_id, phone2_id, user_id=None):
    """Сравнение двух телефонов с помощью AI"""
    if not techspecs_collection:
        return {"error": "Database unavailable"}
    
    try:
        # Получаем данные из базы
        phone1 = techspecs_collection.find_one({'_id': phone1_id})
        phone2 = techspecs_collection.find_one({'_id': phone2_id})
        
        if not phone1 or not phone2:
            return {"error": "Phone data not available"}
        
        import google.generativeai as genai
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
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

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Очистка ответа
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        comparison = json.loads(response_text)
        save_comparison(phone1, phone2, comparison, user_id)
        return comparison
    
    except Exception as e:
        app.logger.error(f"Comparison error: {str(e)}")
        return {"error": "AI service unavailable"}

def save_comparison(phone1, phone2, comparison, user_id):
    """Сохранение результатов сравнения в базу"""
    from app import comparisons_collection  # Ленивый импорт
    
    if not comparisons_collection:
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
