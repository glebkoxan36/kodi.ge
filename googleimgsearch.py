import os
import requests
import time
from pymongo import MongoClient
from bson import ObjectId
from urllib.parse import quote
from flask import current_app

# Конфигурация
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')
MONGODB_URI = os.getenv('MONGODB_URI')

# Подключение к MongoDB
client = MongoClient(MONGODB_URI)
db = client['imei_checker']
phone_images_collection = db['phone_images']

def search_phone_image(phone_name):
    """Поиск изображения телефона с кэшированием результатов"""
    try:
        # Проверяем кэш
        cached = phone_images_collection.find_one({'phone_name': phone_name})
        if cached:
            return cached['image_url']

        # Формируем запрос
        query = f"{phone_name} official product photo"
        safe_query = quote(query)
        url = f"https://www.googleapis.com/customsearch/v1?q={safe_query}&cx={GOOGLE_CSE_ID}&key={GOOGLE_API_KEY}&searchType=image&num=3"
        
        # Выполняем запрос
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Ищем подходящее изображение
        best_image = None
        for item in data.get('items', []):
            link = item.get('link', '')
            # Проверяем подходящие форматы и размеры
            if link and link.lower().endswith(('.jpg', '.jpeg', '.png')):
                width = item.get('image', {}).get('width', 0)
                height = item.get('image', {}).get('height', 0)
                # Предпочитаем изображения с соотношением сторон ~0.75
                if 300 < width < 2000 and 300 < height < 2000:
                    aspect_ratio = width / height
                    if 0.6 < aspect_ratio < 0.9:
                        best_image = link
                        break
        
        # Сохраняем в кэш
        if best_image:
            phone_images_collection.insert_one({
                'phone_name': phone_name,
                'image_url': best_image,
                'timestamp': time.time()
            })
            return best_image
        
        # Fallback если ничего не найдено
        return '/static/placeholder.jpg'
    
    except Exception as e:
        current_app.logger.error(f"Image search error for {phone_name}: {str(e)}")
        return '/static/placeholder.jpg'
