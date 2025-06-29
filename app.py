import os
import json
import logging
import re
import hmac
import secrets
import hashlib
import requests
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, current_app, Blueprint
from flask_cors import CORS
from pymongo import MongoClient
import stripe
from functools import wraps
from bs4 import BeautifulSoup
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from urllib.parse import quote_plus

# Импорт функций из модуля API
from ifreeapi import validate_imei, perform_api_check, SERVICE_TYPES
from stripepay import StripePayment
from image_search import search_phone_image  # Обновленный импорт

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Функция для генерации цвета аватара
def generate_avatar_color(name):
    """Генерирует HEX-цвет на основе хеша имени пользователя"""
    if not name:
        return "#{:06x}".format(secrets.randbelow(0xFFFFFF))
    
    hash_obj = hashlib.md5(name.encode('utf-8'))
    return '#' + hash_obj.hexdigest()[:6]

# Регистрируем функцию в контексте шаблонов
@app.context_processor
def inject_utils():
    return {
        'generate_avatar_color': generate_avatar_color
    }

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

log_handler = RotatingFileHandler(
    'app.log', 
    maxBytes=1024 * 1024 * 5,
    backupCount=3
)
log_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(log_handler)

# Конфигурация
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
MONGODB_URI = os.getenv('MONGODB_URI')

# Данные для PHP API
API_URL = "https://api.ifreeicloud.co.uk"
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PLACEHOLDER = '/static/placeholder.jpg'

# MongoDB - безопасная инициализация
def init_mongodb():
    max_retries = 5
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            client = MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=15000
            )
            # Проверка подключения
            client.admin.command('ismaster')
            app.logger.info("Successfully connected to MongoDB")
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            app.logger.warning(f"MongoDB connection attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    app.logger.error("Could not connect to MongoDB after multiple attempts")
    return None

client = init_mongodb()
if client is None:
    app.logger.critical("Fatal error: MongoDB connection failed")
else:
    db = client['imei_checker']
    checks_collection = db['results']
    prices_collection = db['prices']
    comparisons_collection = db['comparisons']
    phones_collection = db['phones']
    parser_logs_collection = db['parser_logs']
    admin_users_collection = db['admin_users']
    regular_users_collection = db['users']
    audit_logs_collection = db['audit_logs']
    api_keys_collection = db['api_keys']
    webhooks_collection = db['webhooks']
    payments_collection = db['payments']
    failed_logins_collection = db['failed_logins']
    techspecs_collection = db['techspecs']

    # Отложенная инициализация индексов
    try:
        # Удаление проблемного индекса
        techspecs_collection.drop_index('slug_1')
        app.logger.info("Dropped problematic slug index")
    except Exception as e:
        app.logger.warning(f"Error dropping slug index: {str(e)}")

    try:
        # Создание текстового индекса
        techspecs_collection.create_index([('search_text', 'text')], name='search_text_index')
        app.logger.info("Created text index for techspecs collection")
    except Exception as e:
        app.logger.error(f"Error creating index: {str(e)}")

# Инициализация StripePayment
stripe_payment = StripePayment(
    stripe_api_key=stripe.api_key,
    webhook_secret=STRIPE_WEBHOOK_SECRET,
    users_collection=regular_users_collection,
    payments_collection=payments_collection
)

# Создаем администратора по умолчанию
def init_admin_user():
    try:
        if client and not admin_users_collection.find_one({'username': 'admin'}):
            admin_password = os.getenv('ADMIN_PASSWORD', 'securepassword')
            admin_users_collection.insert_one({
                'username': 'admin',
                'password': generate_password_hash(admin_password),
                'role': 'superadmin',
                'created_at': datetime.utcnow()
            })
            app.logger.info("Default admin user created")
    except Exception as e:
        app.logger.error(f"Error creating admin user: {str(e)}")

# Инициализация цен
DEFAULT_PRICES = {
    'paid': 499,
    'premium': 999
}

def init_prices():
    try:
        if client and prices_collection.count_documents({}) == 0:
            prices_collection.insert_one({
                'type': 'current',
                'prices': DEFAULT_PRICES,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            app.logger.info("Default prices initialized")
    except Exception as e:
        app.logger.error(f"Error initializing prices: {str(e)}")

# Вызов функций инициализации
if client:
    init_admin_user()
    init_prices()

def get_current_prices():
    if not client:
        return DEFAULT_PRICES
        
    try:
        price_doc = prices_collection.find_one({'type': 'current'})
        if price_doc:
            return price_doc['prices']
        return DEFAULT_PRICES
    except Exception as e:
        app.logger.error(f"Error getting prices: {str(e)}")
        return DEFAULT_PRICES

# ======================================
# AI Phone Comparison System (Fixed)
# ======================================

def ai_search_phones(query):
    """Использует Gemini для поиска телефонов по запросу"""
    if not client:
        return []
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        შექმენით JSON სია 10 ყველაზე პოპულარული სმარტფონის შესახებ, რომლებიც შეესაბამება შემდეგ მოთხოვნას: '{query}'.
        თითოეული ტელეფონისთვის მიუთითეთ შემდეგი ველები:
        - brand: ბრენდი (მაგ: Apple, Samsung, Xiaomi)
        - model: მოდელის სახელი (მაგ: iPhone 15 Pro, Galaxy S24 Ultra)
        - release_year: გამოშვების წელი
        - display: ეკრანის დიაგონალი და ტიპი (მაგ: 6.7-inch OLED)
        - processor: პროცესორი (მაგ: Snapdragon 8 Gen 3)
        - ram: ოპერატიული მეხსიერება (მაგ: 8GB)
        - storage: შიდა მეხსიერება (მაგ: 256GB)
        - camera: კამერის სპეციფიკაცია (მაგ: 50MP main + 12MP ultra-wide)
        - battery: ბატარეის ტევადობა (მაგ: 5000mAh)
        - os: ოპერაციული სისტემა (მაგ: Android 14)
        
        გამოიტანეთ მხოლოდ JSON მასივი, სადაც თითოეული ობიექტი აღწერს ერთ ტელეფონს.
        JSON პასუხი უნდა იყოს სწორად ფორმატირებული და არ შეიცავდეს დამატებით ტექსტს ან კომენტარებს.
        """

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Удаляем возможные markdown коды
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        # Логируем для отладки
        app.logger.info(f"Gemini response: {response_text[:500]}...")
        
        # Парсим JSON из ответа
        phones = json.loads(response_text)
        
        # Ищем изображения для каждого телефона
        for phone in phones:
            # Убедимся, что все обязательные поля присутствуют
            required_fields = ['brand', 'model', 'release_year', 'display', 
                              'processor', 'ram', 'storage', 'camera', 
                              'battery', 'os']
            for field in required_fields:
                if field not in phone:
                    phone[field] = "N/A"  # Значение по умолчанию
            
            # Поиск изображения
            image_url = search_phone_image(f"{phone['brand']} {phone['model']}")
            phone['image_url'] = image_url if image_url else PLACEHOLDER
            
            # Генерация уникального ID
            phone_id = f"{phone['brand']}_{phone['model']}" \
                .replace(' ', '_') \
                .replace('/', '_') \
                .replace('.', '') \
                .replace("'", "") \
                .lower()
            
            # Сохраняем в базу
            phone['_id'] = phone_id
            phone['slug'] = phone_id  # Добавляем поле slug
            phone['search_text'] = f"{phone['brand']} {phone['model']}"
            phone['last_updated'] = datetime.utcnow()
            
            techspecs_collection.update_one(
                {'_id': phone_id},
                {'$set': phone},
                upsert=True
            )
        
        return phones
    
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error: {str(e)}")
        app.logger.error(f"Raw response: {response.text[:500] if 'response' in locals() else 'No response'}")
        return []
    except Exception as e:
        app.logger.error(f"AI search error: {str(e)}")
        return []

def ai_compare_phones(phone1_id, phone2_id):
    """Сравнивает два телефона с помощью AI"""
    if not client:
        return {"error": "Database unavailable"}
    
    try:
        # Получаем данные из базы
        phone1 = techspecs_collection.find_one({'_id': phone1_id})
        phone2 = techspecs_collection.find_one({'_id': phone2_id})
        
        if not phone1 or not phone2:
            return {"error": "Phone data not available"}
        
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Формируем промпт для сравнения
        prompt = f"""
        შეადარეთ ორი სმარტფონი: 
        Phone 1: {phone1['brand']} {phone1['model']} 
        Phone 2: {phone2['brand']} {phone2['model']}
        
        გთხოვთ მოგვაწოდოთ დეტალური შედარება შემდეგი კატეგორიების მიხედვით:
        1. დიზაინი და აგებულება
        2. ეკრანის ხარისხი და ზომა
        3. პროდუქტიულობა (პროცესორი, RAM)
        4. კამერის შესაძლებლობები
        5. ბატარეის ხანგრძლივობა
        6. ოპერაციული სისტემა და განახლებები
        7. დამატებითი ფუნქციები
        8. ფასი და ღირებულება
        
        დასასრულს მიუთითეთ რომელი ტელეფონი უკეთესია თითოეულ კატეგორიაში და საერთო ჯამში.
        
        გთხოვთ გამოიტანოთ პასუხი STRICTLY JSON ფორმატში შემდეგი სტრუქტურით:
        {{
            "comparison": [
                {{
                    "category": "დიზაინი",
                    "phone1_advantage": "მოკლე აღწერა რატომ არის ტელეფონი 1 უკეთესი",
                    "phone2_advantage": "მოკლე აღწერა რატომ არის ტელეფონი 2 უკეთესი",
                    "winner": "phone1" ან "phone2"
                }},
                // ... სხვა კატეგორიები
            ],
            "overall_winner": "phone1" ან "phone2",
            "summary": "მოკლე დასკვნა"
        }}
        
        მნიშვნელოვანია: გამოიტანეთ მხოლოდ JSON ობიექტი, ყოველგვარი დამატებითი ტექსტის გარეშე.
        """

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Очистка ответа от markdown
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        app.logger.info(f"Gemini comparison response: {response_text[:500]}...")
        
        comparison = json.loads(response_text)
        
        # Сохраняем результат сравнения
        comparisons_collection.insert_one({
            'phone1_id': phone1_id,
            'phone2_id': phone2_id,
            'phone1_name': f"{phone1['brand']} {phone1['model']}",
            'phone2_name': f"{phone2['brand']} {phone2['model']}",
            'comparison': comparison,
            'timestamp': datetime.utcnow(),
            'user_id': ObjectId(session.get('user_id')) if 'user_id' in session else None
        })
        
        return comparison
    
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error in comparison: {str(e)}")
        app.logger.error(f"Raw response: {response_text}")
        return {"error": "Invalid JSON response from AI"}
    except Exception as e:
        app.logger.error(f"Gemini comparison error: {str(e)}")
        return {"error": "AI service unavailable"}

# ======================================
# API Endpoints for Phone Comparison
# ======================================

@app.route('/api/search', methods=['GET'])
def api_search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Search query required'}), 400
    
    results = ai_search_phones(query)
    return jsonify(results)

@app.route('/api/phone_details/<phone_id>', methods=['GET'])
def api_phone_details(phone_id):
    if not client:
        return jsonify({'error': 'Database unavailable'}), 500
    
    phone = techspecs_collection.find_one({'_id': phone_id})
    if not phone:
        return jsonify({'error': 'Phone not found'}), 404
    
    # Удаляем поля, которые не нужны на клиенте
    phone.pop('_id', None)
    phone.pop('search_text', None)
    phone.pop('last_updated', None)
    return jsonify(phone)

@app.route('/api/compare', methods=['POST'])
def api_compare_phones():
    data = request.json
    phone1_id = data.get('phone1_id')
    phone2_id = data.get('phone2_id')
    
    if not phone1_id or not phone2_id:
        return jsonify({'error': 'Both phone IDs are required'}), 400
    
    comparison = ai_compare_phones(phone1_id, phone2_id)
    if 'error' in comparison:
        return jsonify(comparison), 500
    return jsonify(comparison)

# ======================================
# Аудит и логирование
# ======================================

def log_audit_event(action, details, user_id=None, username=None):
    """Логирование действий администратора"""
    if not client:
        return
        
    event = {
        'action': action,
        'details': details,
        'user_id': user_id,
        'username': username,
        'timestamp': datetime.utcnow(),
        'ip_address': request.remote_addr
    }
    try:
        audit_logs_collection.insert_one(event)
    except Exception as e:
        app.logger.error(f"Audit log error: {str(e)}")

# ======================================
# Декораторы
# ======================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or session['role'] not in ['admin', 'superadmin']:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# ======================================
# Основные маршруты приложения
# ======================================

@app.route('/')
def index():
    prices = get_current_prices()
    user_data = None
    
    if 'user_id' in session:
        user_id = session['user_id']
        if client:
            user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
                user_data = {
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0.0),
                    'avatar_color': avatar_color
                }

    return render_template('index.html', 
                         stripe_public_key=STRIPE_PUBLIC_KEY,
                         paid_price=prices['paid'] / 100,
                         premium_price=prices['premium'] / 100,
                         user=user_data)

@app.route('/contacts')
def contacts_page():
    """Страница контактов"""
    user_data = None
    if 'user_id' in session:
        user_id = session['user_id']
        if client:
            user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
                user_data = {
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0.0),
                    'avatar_color': avatar_color
                }
    
    return render_template('contacts.html', user=user_data)

@app.route('/knowledge-base')
def knowledge_base():
    """База знаний"""
    user_data = None
    if 'user_id' in session:
        user_id = session['user_id']
        if client:
            user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
                user_data = {
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0.0),
                    'avatar_color': avatar_color
                }
    
    return render_template('knowledge-base.html', user=user_data)

# ======================================
# Роут для страницы проверки Apple IMEI
# ======================================

@app.route('/applecheck')
def apple_check():
    # Определяем тип услуги из параметра URL
    service_type = request.args.get('type', 'free')
    
    # Получаем текущие цены и конвертируем в лари
    prices = get_current_prices()
    paid_price_gel = prices['paid'] / 100.0
    premium_price_gel = prices['premium'] / 100.0
    
    # Создаем словарь цен для каждого типа услуги
    service_prices = {
        'free': 'უფასო',
        'fmi': f"{paid_price_gel:.2f}₾",
        'blacklist': f"{paid_price_gel:.2f}₾",
        'sim_lock': f"{premium_price_gel:.2f}₾",
        'activation': f"{paid_price_gel:.2f}₾",
        'carrier': f"{paid_price_gel:.2f}₾",
        'mdm': f"{premium_price_gel:.2f}₾"
    }

    # Данные пользователя (если авторизован)
    user_data = None
    if 'user_id' in session:
        user_id = session['user_id']
        if client:
            user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
                user_data = {
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0.0),
                    'avatar_color': avatar_color
                }

    # Создаем список услуг с данными для передачи в шаблон
    services_data = [
        { 
            'id': 'free', 
            'title': 'ძირითადი შემოწმება', 
            'icon': 'fa-mobile-screen', 
            'description': 'მოწყობილობის აქტივაციის სტატუსისა და მოდელის შემოწმება', 
            'price': service_prices['free'] 
        },
        { 
            'id': 'fmi', 
            'title': 'FMI სტატუსი', 
            'icon': 'fa-lock', 
            'description': 'მოწყობილობის "მოძებნე" სტატუსის შემოწმება', 
            'price': service_prices['fmi'] 
        },
        { 
            'id': 'blacklist', 
            'title': 'შავი სია', 
            'icon': 'fa-ban', 
            'description': 'მოწყობილობის შავ სიაში მოხვედრის შემოწმება', 
            'price': service_prices['blacklist'] 
        },
        { 
            'id': 'sim_lock', 
            'title': 'SIM-ლოკი', 
            'icon': 'fa-sim-card', 
            'description': 'ოპერატორის მიერ დაბლოკვის შემოწმება', 
            'price': service_prices['sim_lock'] 
        },
        { 
            'id': 'activation', 
            'title': 'აქტივაციის სტატუსი', 
            'icon': 'fa-bolt', 
            'description': 'მოწყობილობის აქტივაციის სტატუსის შემოწმება', 
            'price': service_prices['activation'] 
        },
        { 
            'id': 'carrier', 
            'title': 'ოპერატორი', 
            'icon': 'fa-tower-cell', 
            'description': 'ოპერატორის დადასტურება, რომელსაც მოწყობილობა უკავშირდება', 
            'price': service_prices['carrier'] 
        },
        { 
            'id': 'mdm', 
            'title': 'MDM ბლოკირება', 
            'icon': 'fa-building-shield', 
            'description': 'კორპორატიული ბლოკირების შემოწმება', 
            'price': service_prices['mdm'] 
        }
    ]

    return render_template(
        'applecheck.html',
        service_type=service_type,
        services_data=services_data,  # Передаем готовый список услуг
        stripe_public_key=STRIPE_PUBLIC_KEY,
        user=user_data
    )

# ======================================
# Роут для страницы проверки Android IMEI
# ======================================

@app.route('/androidcheck')
def android_check():
    """Страница проверки Android устройств"""
    service_type = request.args.get('type', '')
    prices = get_current_prices()
    paid_price_gel = prices['paid'] / 100.0
    premium_price_gel = prices['premium'] / 100.0

    service_prices = {
        'samsung_v1': f"{paid_price_gel:.2f}₾",
        'samsung_v2': f"{paid_price_gel:.2f}₾",
        'samsung_knox': f"{premium_price_gel:.2f}₾",
        'xiaomi': f"{paid_price_gel:.2f}₾",
        'google_pixel': f"{paid_price_gel:.2f}₾",
        'huawei_v1': f"{paid_price_gel:.2f}₾",
        'huawei_v2': f"{paid_price_gel:.2f}₾",
        'motorola': f"{paid_price_gel:.2f}₾",
        'oppo': f"{paid_price_gel:.2f}₾",
        'frp': f"{paid_price_gel:.2f}₾",
        'sim_lock_android': f"{paid_price_gel:.2f}₾",
    }

    # Данные сервисов
    services_data = [
        { 
            'id': 'samsung', 
            'title': 'Samsung', 
            'icon': 'fa-mobile', 
            'description': 'Samsung მოწყობილობების შემოწმება',
            'versions': [
                {'id': 'samsung_v1', 'name': 'სერვისი V1', 'price': service_prices['samsung_v1']},
                {'id': 'samsung_v2', 'name': 'სერვისი V2', 'price': service_prices['samsung_v2']},
                {'id': 'samsung_knox', 'name': 'Knox სტატუსი', 'price': service_prices['samsung_knox']}
            ]
        },
        { 
            'id': 'xiaomi', 
            'title': 'Xiaomi', 
            'icon': 'fa-mobile', 
            'description': 'Xiaomi მოწყობილობების შემოწმება', 
            'price': service_prices['xiaomi'] 
        },
        { 
            'id': 'google_pixel', 
            'title': 'Google Pixel', 
            'icon': 'fa-mobile', 
            'description': 'Google Pixel მოწყობილობების შემოწმება', 
            'price': service_prices['google_pixel'] 
        },
        { 
            'id': 'huawei', 
            'title': 'Huawei', 
            'icon': 'fa-mobile', 
            'description': 'Huawei მოწყობილობების შემოწმება',
            'versions': [
                {'id': 'huawei_v1', 'name': 'სერვისი V1', 'price': service_prices['huawei_v1']},
                {'id': 'huawei_v2', 'name': 'სერვისი V2', 'price': service_prices['huawei_v2']}
            ]
        },
        { 
            'id': 'motorola', 
            'title': 'Motorola', 
            'icon': 'fa-mobile', 
            'description': 'Motorola მოწყობილობების შემოწმება', 
            'price': service_prices['motorola'] 
        },
        { 
            'id': 'oppo', 
            'title': 'Oppo', 
            'icon': 'fa-mobile', 
            'description': 'Oppo მოწყობილობების შემოწმება', 
            'price': service_prices['oppo'] 
        },
        { 
            'id': 'frp', 
            'title': 'FRP Lock', 
            'icon': 'fa-google', 
            'description': 'Google ანგარიშის ბლოკირების შემოწმება', 
            'price': service_prices['frp'] 
        },
        { 
            'id': 'sim_lock_android', 
            'title': 'SIM Lock Status', 
            'icon': 'fa-sim-card', 
            'description': 'ოპერატორის მიერ დაბლოკვის შემოწმება', 
            'price': service_prices['sim_lock_android'] 
        }
    ]

    user_data = None
    if 'user_id' in session:
        user_id = session['user_id']
        if client:
            user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
                user_data = {
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0.0),
                    'avatar_color': avatar_color
                }

    return render_template(
        'androidcheck.html',
        service_type=service_type,
        services_data=services_data,
        stripe_public_key=STRIPE_PUBLIC_KEY,
        user=user_data
    )

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        imei = data.get('imei')
        service_type = data.get('service_type')
        use_balance = data.get('use_balance', False)
        
        if not validate_imei(imei):
            return jsonify({'error': 'არასწორი IMEI'}), 400
        
        # Маппинг типов услуг на цены
        price_mapping = {
            'fmi': 'paid',
            'blacklist': 'paid',
            'sim_lock': 'premium',
            'activation': 'paid',
            'carrier': 'paid',
            'mdm': 'premium',
            'samsung_v1': 'paid',
            'samsung_v2': 'paid',
            'samsung_knox': 'premium',
            'xiaomi': 'paid',
            'google_pixel': 'paid',
            'huawei_v1': 'paid',
            'huawei_v2': 'paid',
            'motorola': 'paid',
            'oppo': 'paid',
            'frp': 'paid',
            'sim_lock_android': 'paid'
        }
        
        if service_type not in price_mapping:
            return jsonify({'error': 'არასწორი სერვისის ტიპი'}), 400
        
        prices = get_current_prices()
        price_key = price_mapping[service_type]
        amount = prices[price_key]  # в центах
        
        # Для бесплатной проверки не создаем сессию
        if service_type == 'free':
            return jsonify({'error': 'უფასო შემოწმება არ საჭიროებს გადახდას'}), 400
        
        # Если пользователь авторизован и выбрал оплату с баланса
        if use_balance and 'user_id' in session:
            user_id = session['user_id']
            # Проверяем достаточно ли средств
            if client:
                user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
                amount_usd = amount / 100  # Конвертация в доллары
                
                if user and user.get('balance', 0) >= amount_usd:
                    # Списание средств с баланса
                    if stripe_payment.deduct_balance(user_id, amount_usd):
                        # Создаем запись о проверке
                        session_id = f"balance_{ObjectId()}"
                        record = {
                            'session_id': session_id,
                            'imei': imei,
                            'service_type': service_type,
                            'paid': True,
                            'payment_status': 'succeeded',
                            'payment_method': 'balance',
                            'amount': amount_usd,
                            'currency': 'usd',
                            'timestamp': datetime.utcnow(),
                            'user_id': ObjectId(user_id)
                        }
                        if client:
                            checks_collection.insert_one(record)
                        
                        return jsonify({
                            'id': session_id,
                            'payment_method': 'balance'
                        })
                    else:
                        return jsonify({'error': 'ბალანსიდან გადახდა ვერ მოხერხდა'}), 500
                else:
                    # Недостаточно средств, переходим к оплате картой
                    use_balance = False
        
        # Если не используем баланс (неавторизован или недостаточно средств)
        if not use_balance:
            # Используем StripePayment для создания сессии
            success_url = url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}&imei=' + imei + '&service_type=' + service_type
            cancel_url = url_for('android_check', _external=True) + f'?type={service_type}'
            
            stripe_session = stripe_payment.create_checkout_session(
                imei=imei,
                service_type=service_type,
                amount=amount,  # в центах
                success_url=success_url,
                cancel_url=cancel_url
            )
            
            return jsonify({'id': stripe_session.id, 'payment_method': 'stripe'})
    
    except Exception as e:
        app.logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/perform_balance_check', methods=['POST'])
def perform_balance_check():
    """Выполнение проверки при оплате балансом"""
    try:
        data = request.json
        imei = data.get('imei')
        service_type = data.get('service_type')
        session_id = data.get('session_id')
        
        if not validate_imei(imei):
            return jsonify({'error': 'არასწორი IMEI'}), 400
        
        result = perform_api_check(imei, service_type)
        
        if not result or 'error' in result:
            error_msg = result.get('error', 'ამ IMEI-სთვის მონაცემები ხელმიუწვდომელია')
            return jsonify({'error': error_msg}), 400
        
        # Обновляем запись в базе
        if client:
            checks_collection.update_one(
                {'session_id': session_id},
                {'$set': {'result': result}}
            )
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Balance check error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    imei = request.args.get('imei')
    service_type = request.args.get('service_type')
    
    if not session_id or not imei or not service_type:
        return render_template('error.html', error="არასაკმარისი პარამეტრები"), 400
    
    try:
        # Для Stripe получаем сессию
        stripe_session = stripe.checkout.Session.retrieve(session_id)
        
        result = perform_api_check(imei, service_type)
        
        if not result or 'error' in result:
            error_msg = result.get('error', 'ამ IMEI-სთვის მონაცემები ხელმიუწვდომელია')
            return render_template('error.html', error=error_msg)
        
        # Для сервисов, возвращающих HTML
        if 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            if parsed_data:
                result = parsed_data
            else:
                result = {'error': 'HTML პასუხის დამუშავება ვერ მოხერხდა'}
        
        record = {
            'stripe_session_id': session_id,
            'imei': imei,
            'service_type': service_type,
            'paid': True,
            'payment_status': stripe_session.payment_status,
            'amount': stripe_session.amount_total / 100,
            'currency': stripe_session.currency,
            'timestamp': datetime.utcnow(),
            'result': result
        }
        if 'user_id' in session:
            record['user_id'] = ObjectId(session['user_id'])
        if client:
            checks_collection.insert_one(record)
        
        # Перенаправляем на страницу сервиса с параметрами для отображения результата
        return redirect(url_for('android_check', type=service_type, imei=imei, session_id=session_id))
    
    except Exception as e:
        app.logger.error(f"Payment success error: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/get_check_result')
def get_check_result():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'სესიის ID არის მითითებული'}), 400
    
    if not client:
        return jsonify({'error': 'Database unavailable'}), 500
    
    # Ищем как по session_id (баланс), так и по stripe_session_id (Stripe)
    record = checks_collection.find_one({
        '$or': [
            {'session_id': session_id},
            {'stripe_session_id': session_id}
        ]
    })
    if not record:
        return jsonify({'error': 'შედეგი ვერ მოიძებნა'}), 404
    
    return jsonify({
        'imei': record['imei'],
        'result': record['result']
    })

def parse_free_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {}
        
        # 1. Парсинг табличных данных
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(':', '').replace(' ', '_').lower()
                    value = cols[1].get_text(strip=True)
                    result[key] = value

        # 2. Парсинг всех возможных пар ключ-значение
        pattern = re.compile(
            r'(Device|Model|Serial|IMEI|ICCID|FMI|Activation Status|'
            r'Blacklist Status|Sim Lock|MDM Status|Google Account Status|'
            r'Carrier|Purchase Date|Warranty Status|Activation Policy|'
            r'Network Lock|Coverage|Find My iPhone|iCloud Status|'
            r'Activation Lock|Last Restore|Factory Unlocked|Refurbished|'
            r'Replaced|Loaner|AppleCare|Blocked Status|Restore Status|'
            r'Activation Date|Purchase Country|Next Tether Policy|Sim Lock Policy)'
            r'[\s:]*', 
            re.IGNORECASE
        )
        
        for element in soup.find_all(string=pattern):
            match = pattern.search(element)
            if match:
                label = match.group(1).strip()
                key = label.replace(' ', '_').lower()
                
                # Поиск значения в структуре документа
                value = ""
                parent = element.parent
                
                # Случай 1: Значение в том же элементе после двоеточия
                if ':' in element:
                    value = element.split(':', 1)[1].strip()
                
                # Случай 2: Значение в соседнем элементе
                elif parent and parent.find_next_sibling():
                    value = parent.find_next_sibling().get_text(strip=True)
                
                # Случай 3: Значение в следующем текстовом узле
                elif element.next_sibling:
                    value = element.next_sibling.strip()
                
                if value:
                    result[key] = value

        # 3. Дополнительный сбор данных из заголовков и значений
        for header in soup.find_all(['h3', 'h4', 'strong', 'b']):
            text = header.get_text(strip=True)
            if ':' in text:
                key, value = text.split(':', 1)
                key = key.strip().replace(' ', '_').lower()
                result[key] = value.strip()
            elif header.next_sibling:
                key = text.replace(':', '').replace(' ', '_').lower()
                result[key] = header.next_sibling.strip()

        return result
    
    except Exception as e:
        current_app.logger.error(f"Advanced HTML parsing error: {str(e)}")
        return None

@app.route('/perform_check', methods=['POST'])
def perform_check():
    try:
        data = request.get_json()
        imei = data.get('imei')
        service_type = data.get('service_type')
        
        if not imei or not service_type:
            return jsonify({'error': 'არასაკმარისი პარამეტრები'}), 400
        
        if not validate_imei(imei):
            return jsonify({'error': 'IMEI-ის არასწორი ფორმატი'}), 400
        
        result = perform_api_check(imei, service_type)
        
        if not result:
            return jsonify({'error': 'API-დან ცარიელი პასუხი'}), 500
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Для сервисов, возвращающих HTML
        if 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            
            if parsed_data:
                # Сохраняем оригинальный HTML как резерв
                parsed_data['original_html'] = result['html_content'][:500] + '...' 
                result = parsed_data
            else:
                # Fallback: возвращаем очищенный текст
                soup = BeautifulSoup(result['html_content'], 'html.parser')
                result = {'server_response': soup.get_text(separator='\n', strip=True)}
        
        if service_type == 'free' and client:
            record = {
                'imei': imei,
                'service_type': service_type,
                'paid': False,
                'timestamp': datetime.utcnow(),
                'result': result
            }
            if 'user_id' in session:
                record['user_id'] = ObjectId(session['user_id'])
            checks_collection.insert_one(record)
        
        if result and 'error' not in result and client:
            send_webhook_event('imei_check_completed', {
                'imei': imei,
                'service_type': service_type,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f'Check error: {str(e)}')
        return jsonify({'error': 'სერვერული შეცდომა'}), 500

@app.route('/reparse_imei')
def reparse_imei():
    imei = request.args.get('imei')
    if not client:
        return jsonify({'error': 'Database unavailable'}), 500
        
    record = checks_collection.find_one({'imei': imei, 'service_type': 'free'})
    
    if not record or 'result' not in record or 'html_content' not in record['result']:
        return jsonify({'error': 'მონაცემები ვერ მოიძებნა'}), 404
    
    html_content = record['result']['html_content']
    parsed_data = parse_free_html(html_content)
    
    if parsed_data:
        parsed_data['reparsed'] = True  # Флаг повторного парсинга
        return jsonify(parsed_data)
    
    return jsonify({
        'error': 'დამუშავება ვერ მოხერხდა',
        'server_response': BeautifulSoup(html_content, 'html.parser').get_text()
    })

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Обработка вебхука через StripePayment
        stripe_payment.handle_webhook(payload, sig_header)
        return jsonify({'status': 'success'})
    
    except ValueError as e:
        return jsonify({'error': 'არასწორი მონაცემები'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'არასწორი ხელმოწერა'}), 400
    except Exception as e:
        app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'error': 'სერვერული შეცდომა'}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        'error.html', 
        code=404,
        message="გვერდი ვერ მოიძებნა"
    ), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        'error.html', 
        code=500,
        message="სერვერზე შეცდომა მოხდა"
    ), 500

# ======================================
# Health Check
# ======================================

@app.route('/health')
def health_check():
    status = {
        'status': 'OK',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # Проверка MongoDB
    if client:
        try:
            db.command('ping')
            status['services']['mongodb'] = 'OK'
        except Exception as e:
            status['services']['mongodb'] = f'ERROR: {str(e)}'
            status['status'] = 'ERROR'
    else:
        status['services']['mongodb'] = 'DISABLED'
        status['status'] = 'DEGRADED'
    
    # Проверка Stripe
    try:
        stripe.Balance.retrieve()
        status['services']['stripe'] = 'OK'
    except Exception as e:
        status['services']['stripe'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    # Проверка внешнего API
    try:
        response = requests.get(API_URL, timeout=5)
        status['services']['external_api'] = 'OK' if response.status_code == 200 else f'HTTP {response.status_code}'
    except Exception as e:
        status['services']['external_api'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    # Проверка Gemini API
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Ping", generation_config=genai.types.GenerationConfig(max_output_tokens=1))
        status['services']['gemini_api'] = 'OK'
    except Exception as e:
        status['services']['gemini_api'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    return jsonify(status), 200 if status['status'] == 'OK' else 500

# ======================================
# Webhook Manager
# ======================================

def send_webhook_event(event_type, payload):
    if not client:
        return
        
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
        except Exception as e:
            app.logger.error(f"Webhook error for {webhook['url']}: {str(e)}")
            webhooks_collection.update_one(
                {'_id': webhook['_id']},
                {'$set': {
                    'last_delivery': datetime.utcnow(),
                    'last_status': 'Error'
                }}
            )

# ======================================
# Carousel Image Upload Endpoints
# ======================================

@app.route('/create-carousel-folder', methods=['POST'])
def create_carousel_folder():
    """Создает папку для изображений карусели"""
    data = request.json
    path = data.get('path', 'static/img/carousel')
    
    try:
        os.makedirs(path, exist_ok=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload-carousel-image', methods=['POST'])
def upload_carousel_image():
    """Загружает изображение для карусели"""
    if 'carouselImage' not in request.files:
        return jsonify({'success': False, 'error': 'ფაილი არ არის ატვირთული'}), 400
    
    file = request.files['carouselImage']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'ფაილი არ არის არჩეული'}), 400
    
    try:
        # Сохраняем в папку carousel
        upload_folder = 'static/img/carousel'
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = f"carousel_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        return jsonify({
            'success': True, 
            'filePath': f'/{file_path}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ======================================
# Comparison Page
# ======================================

@app.route('/compare')
def compare_phones():
    return render_template('compare.html')

# ======================================
# User Blueprint (Личный кабинет пользователя)
# ======================================

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """Личный кабинет пользователя"""
    user_id = session['user_id']
    if not client:
        flash('Database unavailable', 'danger')
        return redirect(url_for('auth.login'))
    
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    # Получение баланса
    balance = user.get('balance', 0)
    
    # Последние 5 проверок
    checks = list(checks_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).limit(5))
    
    # Последние 5 сравнений
    comparisons = list(comparisons_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).limit(5))
    
    # Последние 5 платежей
    payments = list(payments_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).limit(5))
    
    # Общее количество операций
    total_checks = checks_collection.count_documents({'user_id': ObjectId(user_id)})
    total_comparisons = comparisons_collection.count_documents({'user_id': ObjectId(user_id)})
    
    return render_template(
        'user/dashboard.html',
        user=user,
        balance=balance,
        checks=checks,
        comparisons=comparisons,
        payments=payments,
        total_checks=total_checks,
        total_comparisons=total_comparisons,
        STRIPE_PUBLIC_KEY=STRIPE_PUBLIC_KEY
    )

@user_bp.route('/topup', methods=['GET', 'POST'])
@login_required
def topup_balance():
    """Пополнение баланса"""
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        if amount < 1:
            flash('მინიმალური თანხა $1', 'danger')
            return redirect(url_for('user.topup_balance'))
        
        # Используем StripePayment для создания сессии пополнения
        try:
            success_url = url_for('user.topup_success', _external=True)
            cancel_url = url_for('user.topup_balance', _external=True)
            
            stripe_session = stripe_payment.create_topup_session(
                user_id=str(session['user_id']),
                amount=amount,
                success_url=success_url,
                cancel_url=cancel_url
            )
            return redirect(stripe_session.url)
        except Exception as e:
            flash(f'გადახდის სესიის შექმნის შეცდომა: {str(e)}', 'danger')
            return redirect(url_for('user.topup_balance'))
    
    return render_template('user/topup.html', stripe_public_key=STRIPE_PUBLIC_KEY)

@user_bp.route('/topup/success')
@login_required
def topup_success():
    """Успешное пополнение баланса"""
    flash('გადახდა წარმატებით დასრულდა! თქვენი ბალანსი მალე განახლდება.', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/payment-methods')
@login_required
def payment_methods():
    """Управление платежными методами"""
    return render_template('user/payment_methods.html')

@user_bp.route('/history/checks')
@login_required
def history_checks():
    """История проверок IMEI"""
    user_id = session['user_id']
    if not client:
        flash('Database unavailable', 'danger')
        return redirect(url_for('auth.login'))
    
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    checks = list(checks_collection.find({'user_id': ObjectId(user_id)})
        .sort('timestamp', -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    total = checks_collection.count_documents({'user_id': ObjectId(user_id)})
    
    for check in checks:
        check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M')
    
    return render_template(
        'user/history_checks.html',
        user=user,
        balance=balance,
        checks=checks,
        page=page,
        per_page=per_page,
        total=total
    )

@user_bp.route('/history/comparisons')
@login_required
def history_comparisons():
    """История сравнений телефонов"""
    user_id = session['user_id']
    if not client:
        flash('Database unavailable', 'danger')
        return redirect(url_for('auth.login'))
    
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    comparisons = list(comparisons_collection.find({'user_id': ObjectId(user_id)})
        .sort('timestamp', -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    total = comparisons_collection.count_documents({'user_id': ObjectId(user_id)})
    
    for comp in comparisons:
        comp['timestamp'] = comp['timestamp'].strftime('%Y-%m-%d %H:%M')
    
    return render_template(
        'user/history_comparisons.html',
        user=user,
        balance=balance,
        comparisons=comparisons,
        page=page,
        per_page=per_page,
        total=total
    )

# ======================================
# Authentication Blueprint
# ======================================

auth_bp = Blueprint('auth', __name__)

GEORGIAN_LETTERS_REGEX = re.compile(r'^[\u10A0-\u10FF\s]+$')
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$')
PHONE_REGEX = re.compile(r'^\+995\d{9}$')

@auth_bp.route('/register', methods=['GET'])
def show_register_form():
    current_year = datetime.utcnow().year
    return render_template('register.html', current_year=current_year)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.form
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    birth_day = data.get('birth_day')
    birth_month = data.get('birth_month')
    birth_year = data.get('birth_year')
    phone = data.get('phone')
    email = data.get('email', '').strip().lower()
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    errors = []
    
    if not GEORGIAN_LETTERS_REGEX.match(first_name):
        errors.append("სახელი უნდა შეიცავდეს მხოლოდ ქართულ ასოებს")
    
    if not GEORGIAN_LETTERS_REGEX.match(last_name):
        errors.append("გვარი უნდა შეიცავდეს მხოლოდ ქართულ ასოებს")
    
    try:
        birth_date = datetime(int(birth_year), int(birth_month), int(birth_day))
        if birth_date > datetime.utcnow():
            errors.append("დაბადების თარიღი არ შეიძლება იყოს მომავალში")
    except (ValueError, TypeError):
        errors.append("არასწორი დაბადების თარიღი")
    
    if not PHONE_REGEX.match(phone):
        errors.append("არასწორი ტელეფონის ნომრის ფორმატი. გამოიყენეთ +995XXXXXXXXX")
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors.append("არასწორი ელ.ფოსტის მისამართი")
    
    if not PASSWORD_REGEX.match(password):
        errors.append("პაროლი უნდა შედგებოდეს მინიმუმ 12 სიმბოლოსგან, ერთი დიდი ასო, ერთი პატარა ასო, ერთი ციფრი და ერთი სპეციალური სიმბოლო")
    
    if password != confirm_password:
        errors.append("პაროლები არ ემთხვევა")
    
    if client and regular_users_collection.find_one({'$or': [{'username': username}, {'email': email}, {'phone': phone}]}):
        errors.append("მომხმარებელი ასეთი მონაცემებით უკვე არსებობს")
    
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    hashed_pw = generate_password_hash(password)
    user_data = {
        'first_name': first_name,
        'last_name': last_name,
        'birth_date': birth_date,
        'phone': phone,
        'email': email,
        'username': username,
        'password': hashed_pw,
        'role': 'user',
        'balance': 0.0,
        'created_at': datetime.utcnow(),
        'failed_attempts': 0,
        'last_failed_attempt': None
    }
    
    if not client:
        return jsonify({"success": False, "errors": ["Database unavailable"]}), 500
    
    result = regular_users_collection.insert_one(user_data)
    app.logger.info(f"Registered new user: {username}")
    
    session['user_id'] = str(result.inserted_id)
    session['username'] = username
    session['role'] = 'user'
    
    return jsonify({"success": True, "message": "რეგისტრაცია წარმატებით დასრულდა!"}), 201

@auth_bp.route('/login', methods=['GET'])
def show_login_form():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    identifier = request.form.get('identifier', '').strip()
    password = request.form.get('password')
    next_url = request.args.get('next')
    app.logger.info(f"Login attempt for: {identifier}")
    
    ip_address = request.remote_addr
    if client:
        failed_login = failed_logins_collection.find_one({'ip': ip_address})
    else:
        failed_login = None
    
    if failed_login and failed_login.get('blocked_until') and datetime.utcnow() < failed_login['blocked_until']:
        remaining = int((failed_login['blocked_until'] - datetime.utcnow()).total_seconds() / 60)
        return jsonify({
            "success": False,
            "error": f"ანგარიში დროებით დაბლოკილია. სცადეთ {remaining} წუთის შემდეგ"
        }), 429
    
    user = None
    is_admin = False
    
    identifier_lower = identifier.lower()
    if client:
        if '@' in identifier_lower:
            user = regular_users_collection.find_one({'email': identifier_lower})
        elif identifier.startswith('+995'):
            user = regular_users_collection.find_one({'phone': identifier})
        elif identifier.isdigit() and len(identifier) == 9:
            user = regular_users_collection.find_one({'phone': f"+995{identifier}"})
        else:
            user = regular_users_collection.find_one({'username': identifier})
        
        if not user:
            if '@' in identifier_lower:
                user = admin_users_collection.find_one({'email': identifier_lower})
            elif identifier.startswith('+995'):
                user = admin_users_collection.find_one({'phone': identifier})
            elif identifier.isdigit() and len(identifier) == 9:
                user = admin_users_collection.find_one({'phone': f"+995{identifier}"})
            else:
                user = admin_users_collection.find_one({'username': identifier})
            is_admin = True if user else False
    else:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    if user and check_password_hash(user['password'], password):
        if client and failed_login:
            failed_logins_collection.delete_one({'ip': ip_address})
        
        if client:
            collection = admin_users_collection if is_admin else regular_users_collection
            collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
        
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        session['role'] = user['role']
        app.logger.info(f"Successful login for: {user['username']} (Role: {user['role']})")
        
        if next_url:
            redirect_url = next_url
        elif user['role'] in ['admin', 'superadmin']:
            redirect_url = url_for('admin.admin_dashboard')
        else:
            redirect_url = url_for('user.dashboard')
        
        return jsonify({
            "success": True,
            "redirect_url": redirect_url
        }), 200
    
    attempts = 1
    if client:
        if failed_login:
            attempts = failed_login['attempts'] + 1
            update_data = {
                'attempts': attempts,
                'last_attempt': datetime.utcnow()
            }
            failed_logins_collection.update_one(
                {'ip': ip_address},
                {'$set': update_data}
            )
        else:
            failed_logins_collection.insert_one({
                'ip': ip_address,
                'attempts': attempts,
                'last_attempt': datetime.utcnow(),
                'blocked_until': None
            })
    
    if attempts >= 5:
        blocked_until = datetime.utcnow() + timedelta(minutes=10)
        if client:
            failed_logins_collection.update_one(
                {'ip': ip_address},
                {'$set': {'blocked_until': blocked_until}}
            )
        app.logger.warning(f"IP blocked: {ip_address} for 10 minutes")
        return jsonify({
            "success": False,
            "error": "ძალიან ბევრი მცდელობა. ანგარიში დროებით დაბლოკილია 10 წუთით"
        }), 429
    
    app.logger.warning(f"Failed login attempt for: {identifier} from IP: {ip_address}")
    return jsonify({"success": False, "error": "არასწორი მომხმარებლის სახელი ან პაროლი"}), 401

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('თქვენ გამოხვედით სისტემიდან', 'success')
    return redirect(url_for('index'))

# ======================================
# Регистрация блюпринтов
# ======================================

# Импорт админ-панели из отдельного модуля
from admin_routes import admin_bp

app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
