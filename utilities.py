# utilities.py
import re
import secrets
import hashlib
import requests
import hmac
import json
import logging
import numpy as np
from functools import lru_cache
from datetime import datetime
from PIL import Image, ImageEnhance
import easyocr
from unlockimei24 import init_unlock_service  # Исправленный импорт
from price import get_current_prices
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
import io

# Настройка логгера для модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('logs/utilities.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Настройка Cloudinary
cloudinary.config( 
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'dqhnkwgvo'),
    api_key=os.getenv('CLOUDINARY_API_KEY', '886581942952565'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', '8PKil_iXRy2Ggpi60Ihwm84Fa3A'),
    secure=True
)

# ======================================
# Функции для работы с Cloudinary
# ======================================
def upload_avatar_to_cloudinary(image_bytes, public_id):
    """
    Загружает изображение в Cloudinary
    :param image_bytes: BytesIO объект с изображением
    :param public_id: Публичный ID для изображения
    :return: URL загруженного изображения
    """
    try:
        upload_result = cloudinary.uploader.upload(
            image_bytes,
            public_id=public_id,
            unique_filename=False,
            overwrite=True,
            folder="user_avatars",
            transformation=[
                {'width': 200, 'height': 200, 'crop': "fill"},
                {'quality': "auto:best"},
                {'fetch_format': "auto"}
            ]
        )
        return upload_result['secure_url']
    except Exception as e:
        logger.error(f"Cloudinary upload error: {str(e)}")
        return None

# ======================================
# 1. Вспомогательные функции
# ======================================
def validate_imei(imei):
    """Валидация формата IMEI"""
    if not imei:
        return False
    imei = str(imei).strip()
    return re.match(r'^\d{15,17}$', imei) is not None

# ======================================
# 2. Функции генерации данных
# ======================================
@lru_cache(maxsize=512)
def generate_avatar_color(name):
    """Генерирует HEX-цвет на основе хеша имени пользователя"""
    if not name:
        return "#{:06x}".format(secrets.randbelow(0xFFFFFF))
    
    hash_obj = hashlib.md5(name.encode('utf-8'))
    return '#' + hash_obj.hexdigest()[:6]

# ======================================
# 3. Функции для сервисов Apple/Android
# ======================================
def get_apple_services_data():
    """Генерация данных для сервисов Apple"""
    prices = get_current_prices()
    return {
        'free': 'უფასო',
        'fmi': f"{prices['fmi'] / 100:.2f}₾",
        'blacklist': f"{prices['blacklist'] / 100:.2f}₾",
        'sim_lock': f"{prices['sim_lock'] / 100:.2f}₾",
        'activation': f"{prices['activation'] / 100:.2f}₾",
        'carrier': f"{prices['carrier'] / 100:.2f}₾",
        'mdm': f"{prices['mdm'] / 100:.2f}₾"
    }

def get_android_services_data():
    """Генерация данных для сервисов Android"""
    prices = get_current_prices()
    return {
        'samsung_v1': f"{prices['samsung_v1'] / 100:.2f}₾",
        'samsung_v2': f"{prices['samsung_v2'] / 100:.2f}₾",
        'samsung_knox': f"{prices['samsung_knox'] / 100:.2f}₾",
        'xiaomi': f"{prices['xiaomi'] / 100:.2f}₾",
        'google_pixel': f"{prices['google_pixel'] / 100:.2f}₾",
        'huawei_v1': f"{prices['huawei_v1'] / 100:.2f}₾",
        'huawei_v2': f"{prices['huawei_v2'] / 100:.2f}₾",
        'motorola': f"{prices['motorola'] / 100:.2f}₾",
        'oppo': f"{prices['oppo'] / 100:.2f}₾",
        'frp': f"{prices['frp'] / 100:.2f}₾",
        'sim_lock_android': f"{prices['sim_lock_android'] / 100:.2f}₾",
    }

# ======================================
# 4. Функции для сервиса разблокировки
# ======================================
# Удалена локальная init_unlock_service - теперь используется импортированная

def get_unlock_services():
    """Получение списка сервисов разблокировки"""
    unlock_service = init_unlock_service()  # Используем импортированную функцию
    return unlock_service.get_services()

def place_unlock_order(imei, service_id):
    """Создание заказа на разблокировку"""
    unlock_service = init_unlock_service()  # Используем импортированную функцию
    return unlock_service.place_order(imei, service_id)

def check_unlock_status(refid):
    """Проверка статуса заказа на разблокировку"""
    unlock_service = init_unlock_service()  # Используем импортированную функцию
    return unlock_service.get_order_status(refid)

# ======================================
# 5. Вспомогательные функции для вебхуков
# ======================================
def send_webhook_event(event_type, payload, webhooks_collection):
    """Отправка события вебхука"""
    active_webhooks = webhooks_collection.find({
        'active': True,
        'events': event_type
    })
    
    for webhook in active_webhooks:
        try:
            headers = {'Content-Type': 'application/json'}
            if webhook.get('secret'):
                signature = hmac.new(
                    webhook['secret'].encode(),
                    json.dumps(payload).encode(),
                    'sha256'
                ).hexdigest()
                headers['X-Webhook-Signature'] = signature
            
            response = requests.post(
                webhook['url'],
                json=payload,
                headers=headers,
                timeout=5
            )
            
            webhooks_collection.update_one(
                {'_id': webhook['_id']},
                {'$set': {
                    'last_delivery': datetime.utcnow(),
                    'last_status': response.status_code
                }}
            )
            return True
        except Exception:
            return False

# ======================================
# 6. Функции для сканирования IMEI
# ======================================
def preprocess_image(image_bytes):
    """Улучшает качество изображения для распознавания текста"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Увеличение контраста
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Увеличение резкости
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Преобразование в оттенки серого
        image = image.convert('L')
        
        # Преобразование в массив numpy для EasyOCR
        return np.array(image)
    except Exception as e:
        logger.error(f"Image preprocessing error: {str(e)}")
        return None

def extract_imei_from_image(image_bytes):
    """Извлекает IMEI из изображения с помощью OCR"""
    try:
        # Инициализация EasyOCR (делаем один раз)
        if not hasattr(extract_imei_from_image, 'reader'):
            extract_imei_from_image.reader = easyocr.Reader(['en'])
        
        # Предобработка изображения
        processed_image = preprocess_image(image_bytes)
        if processed_image is None:
            return None
        
        # Распознавание текста
        results = extract_imei_from_image.reader.readtext(
            processed_image,
            detail=0,
            paragraph=False,
            allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        )
        
        # Поиск IMEI в распознанных строках
        for text in results:
            # Удаление невалидных символов
            cleaned = re.sub(r'[^0-9A-Z]', '', text.upper())
            
            # Проверка на IMEI (14-17 цифр)
            imei_match = re.search(r'(?<!\d)(\d{14,17})(?!\d)', cleaned)
            if imei_match:
                return imei_match.group(1)
        
        return None
    except Exception as e:
        logger.error(f"IMEI extraction error: {str(e)}")
        return None
