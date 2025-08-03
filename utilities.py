# utilities.py
import re
import secrets
import hashlib
import requests
import hmac
import json
import logging
from functools import lru_cache
from datetime import datetime
from PIL import Image, ImageEnhance
from price import get_current_prices
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
import io
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import time

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

def upload_carousel_image(image_bytes):
    """
    Загружает изображение для карусели в Cloudinary
    :param image_bytes: BytesIO объект с изображением
    :return: URL загруженного изображения и public_id
    """
    try:
        # Убрана обрезка (crop: fill) и изменены параметры для сохранения пропорций 16:9
        upload_result = cloudinary.uploader.upload(
            image_bytes,
            folder="carousel",
            transformation=[
                # Сохранение пропорций 16:9 без обрезки
                {'width': 1200, 'height': 675, 'crop': "scale"},
                {'quality': "auto:best"}
            ]
        )
        return upload_result['secure_url'], upload_result['public_id']
    except Exception as e:
        logger.error(f"Cloudinary carousel upload error: {str(e)}")
        return None, None

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
# 6. Функции для верификации по email
# ======================================

BREVO_API_KEY = os.getenv('BREVO_API_KEY', 'xkeysib-...')  # Ваш API-ключ

def send_verification_email(email, verification_code):
    """Отправляет email с кодом верификации через Brevo"""
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    subject = "შეამოწმეთ თქვენი ელ. ფოსტა"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            <h2 style="color: #333;">ელ. ფოსტის დადასტურება</h2>
            <p style="color: #555; font-size: 16px;">გამარჯობა,</p>
            <p style="color: #555; font-size: 16px;">გმადლობთ რომ დარეგისტრირდით ჩვენს სერვისზე. გთხოვთ გამოიყენოთ ქვემოთ მოცემული კოდი თქვენი ელ. ფოსტის დასადასტურებლად:</p>
            
            <div style="background: #f8f9fa; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
                <h1 style="margin: 0; font-size: 32px; letter-spacing: 3px; color: #333;">{verification_code}</h1>
            </div>
            
            <p style="color: #555; font-size: 16px;">ეს კოდი 5 წუთის განმავლობაში იქნება მოქმედი.</p>
            <p style="color: #555; font-size: 16px;">პატივისცემით,<br>IMEI Checker გუნდი</p>
        </div>
    </body>
    </html>
    """
    
    sender = {"name": "Kodi", "email": "daxmareba@kodi.ge"}
    to = [{"email": email}]
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        html_content=html_content,
        sender=sender,
        subject=subject
    )
    
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Verification email sent to {email}: {api_response}")
        return True
    except ApiException as e:
        logger.error(f"Exception when sending email: {e}")
        return False

def generate_verification_code(length=6):
    """Генерирует случайный цифровой код"""
    return ''.join(secrets.choice('0123456789') for _ in range(length))

def store_verification_data(email, code, storage):
    """Сохраняет данные верификации"""
    storage[email] = {
        'code': code,
        'timestamp': time.time(),
        'attempts': 0
    }
    logger.info(f"Stored verification data for {email}")

def verify_code(email, code, storage):
    """Проверяет код верификации"""
    data = storage.get(email)
    if not data:
        logger.warning(f"No verification data for {email}")
        return False, "კოდი ვერ მოიძებნა ან ვადა გაუვიდა"
    
    # Проверяем время действия (5 минут)
    if time.time() - data['timestamp'] > 300:
        logger.warning(f"Verification code expired for {email}")
        return False, "კოდის ვადა გაუვიდა"
    
    # Проверяем попытки
    if data['attempts'] >= 3:
        logger.warning(f"Too many attempts for {email}")
        return False, "ძალიან ბევრი მცდელობა"
    
    # Увеличиваем счетчик попыток
    storage[email]['attempts'] += 1
    
    if data['code'] == code:
        logger.info(f"Verification successful for {email}")
        return True, "ვერიფიკაცია წარმატებით დასრულდა"
    
    logger.warning(f"Invalid code for {email}")
    return False, "არასწორი კოდი"

# ======================================
# 7. Telegram Support Functions
# ======================================

def get_telegram_config():
    """Получает конфигурацию Telegram из базы данных"""
    try:
        from db import db
        config = db.telegram_config.find_one()
        if config:
            return {
                'bot_token': config.get('bot_token'),
                'chat_id': config.get('chat_id'),
                'enabled': config.get('enabled', False)
            }
        return None
    except Exception as e:
        logger.error(f"Error getting Telegram config: {str(e)}")
        return None

def send_telegram_message(message):
    """Отправляет сообщение в Telegram через бота"""
    config = get_telegram_config()
    
    if not config or not config['enabled']:
        logger.warning("Telegram notifications are disabled")
        return False
    
    bot_token = config.get('bot_token')
    chat_id = config.get('chat_id')
    
    if not bot_token or not chat_id:
        logger.error("Telegram bot token or chat ID not configured")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        })
        
        if response.status_code == 200:
            logger.info("Message sent to Telegram successfully")
            return True
        else:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return False

def format_support_message(data):
    """Форматирует сообщение поддержки для Telegram"""
    return (
        f"<b>📩 ახალი შეტყობინება ლაივ მხარდაჭერიდან</b>\n\n"
        f"<b>👤 სახელი:</b> {data.get('name', 'N/A')}\n"
        f"<b>📧 Email:</b> {data.get('email', 'N/A')}\n"
        f"<b>📞 ტელეფონი:</b> {data.get('phone', 'N/A')}\n"
        f"<b>💬 შეტყობინება:</b>\n{data.get('message', 'N/A')}"
    )

# ======================================
# 8. Функции для работы со счетчиками проверок
# ======================================

def increment_counters():
    """Увеличивает все счетчики проверок на 1"""
    try:
        from db import counters_collection
        if counters_collection:
            counters_collection.update_one(
                {},
                {'$inc': {'daily': 1, 'weekly': 1, 'monthly': 1},
                 '$set': {'last_updated': datetime.utcnow()}}
            )
            return True
        return False
    except Exception as e:
        logger.error(f"Error incrementing counters: {str(e)}")
        return False

def get_counters():
    """Возвращает текущие значения счетчиков"""
    try:
        from db import counters_collection
        if counters_collection:
            counters = counters_collection.find_one({})
            if counters:
                return {
                    'daily': counters.get('daily', 125),
                    'weekly': counters.get('weekly', 875),
                    'monthly': counters.get('monthly', 3750)
                }
        return {
            'daily': 125,
            'weekly': 875,
            'monthly': 3750
        }
    except Exception as e:
        logger.error(f"Error getting counters: {str(e)}")
        return {
            'daily': 125,
            'weekly': 875,
            'monthly': 3750
        }

def reset_counters():
    """Сбрасывает счетчики к начальным значениям"""
    try:
        from db import counters_collection
        if counters_collection:
            counters_collection.update_one(
                {},
                {'$set': {
                    'daily': 125,
                    'weekly': 875,
                    'monthly': 3750,
                    'last_updated': datetime.utcnow()
                }}
            )
            return True
        return False
    except Exception as e:
        logger.error(f"Error resetting counters: {str(e)}")
        return False
