import os
import json
import logging
from logging.handlers import RotatingFileHandler
import re
import hmac
import secrets
import hashlib
import requests
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, current_app, g
from flask_cors import CORS
import stripe
from functools import wraps, lru_cache
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from flask_session import Session
from flask_caching import Cache
from bs4 import BeautifulSoup

# Импорт модулей
from auth import auth_bp
from user_dashboard import user_bp
from ifreeapi import validate_imei, perform_api_check, parse_free_html
from db import client, regular_users_collection, checks_collection, payments_collection, refunds_collection, phonebase_collection, prices_collection, admin_users_collection, parser_logs_collection, audit_logs_collection, api_keys_collection, webhooks_collection
from stripepay import StripePayment
from admin_routes import admin_bp  # Импорт админских роутов

# Создаем папку для логов
if not os.path.exists('logs'):
    os.makedirs('logs')

# Настройка корневого логгера
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Обработчик для записи в файл
file_handler = RotatingFileHandler(
    'logs/app.log', 
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=3
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
root_logger.addHandler(file_handler)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
root_logger.addHandler(console_handler)

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Логгер для app.py
logger = logging.getLogger(__name__)
logger.info("Application starting")

# Настройка кеширования
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Обновленная конфигурация сессии
app.config.update(
    SESSION_TYPE='mongodb',
    SESSION_MONGODB=client,
    SESSION_MONGODB_DB='imeicheck',
    SESSION_MONGODB_COLLECT='sessions',
    SESSION_COOKIE_NAME='imeicheck_session',
    SESSION_COOKIE_DOMAIN=os.getenv('SESSION_DOMAIN', None),
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=True
)
Session(app)

# Инициализация CSRF защиты
csrf = CSRFProtect(app)

# Семафор для ограничения запросов
REQUEST_SEMAPHORE = threading.BoundedSemaphore(3)

# Функция для генерации цвета аватара
def generate_avatar_color(name):
    """Генерирует HEX-цвет на основе хеша имени пользователя"""
    if not name:
        return "#{:06x}".format(secrets.randbelow(0xFFFFFF))
    
    hash_obj = hashlib.md5(name.encode('utf-8'))
    return '#' + hash_obj.hexdigest()[:6]

# Фильтр для форматирования даты в шаблонах Jinja2
@app.template_filter('format_datetime')
def format_datetime_filter(value, format='%d.%m.%Y %H:%M'):
    """Фильтр для форматирования даты в шаблонах Jinja2"""
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        # Попытка преобразовать строку в datetime
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        return dt.strftime(format)
    except:
        return value  # Возвращаем как есть, если не удалось преобразовать

# Кешируемая функция получения цен
@cache.memoize(timeout=300)  # Кеширование на 5 минут
def get_current_prices():
    DEFAULT_PRICES = {
        'paid': 100,  # 1.00 GEL в центах
        'premium': 200  # 2.00 GEL в центах
    }
    
    if not client:
        logger.warning("Using default prices - no MongoDB connection")
        return DEFAULT_PRICES
        
    try:
        price_doc = prices_collection.find_one({'type': 'current'})
        if price_doc:
            return price_doc['prices']
        return DEFAULT_PRICES
    except Exception as e:
        logger.error(f"Error getting prices: {str(e)}")
        return DEFAULT_PRICES

# Контекстный процессор для добавления данных пользователя во все шаблоны
@app.context_processor
def inject_user():
    """Добавляет данные текущего пользователя во все шаблоны"""
    user_data = None
    user_id = session.get('user_id')
    
    if user_id:
        try:
            user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                # Генерируем цвет аватара если его нет
                avatar_color = user.get('avatar_color')
                if not avatar_color:
                    name_part = user.get('first_name') or user.get('email', 'user')
                    avatar_color = generate_avatar_color(name_part)
                
                user_data = {
                    'id': str(user['_id']),
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0),
                    'avatar_color': avatar_color,
                    'avatar_url': user.get('avatar_url')
                }
        except (TypeError, InvalidId):
            # Очищаем невалидную сессию
            session.pop('user_id', None)
            logger.warning("Invalid user ID in session - cleared")
    
    return {'currentUser': user_data}

# Конфигурация
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Данные для PHP API
API_URL = "https://api.ifreeicloud.co.uk"
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')
PLACEHOLDER = '/static/placeholder.jpg'

# Инициализация StripePayment
stripe_payment = StripePayment(
    stripe_api_key=stripe.api_key,
    webhook_secret=STRIPE_WEBHOOK_SECRET,
    users_collection=regular_users_collection,
    payments_collection=payments_collection,
    refunds_collection=refunds_collection
)

# ======================================
# Декораторы
# ======================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or session['role'] not in ['admin', 'superadmin']:
            logger.warning("Unauthorized admin access attempt")
            return redirect(url_for('auth.admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Unauthorized access attempt")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# ======================================
# Вспомогательные функции
# ======================================

def render_common_template(template_name, **kwargs):
    """Общая функция для рендеринга шаблонов без данных пользователя"""
    logger.debug(f"Rendering template: {template_name}")
    return render_template(template_name, **kwargs)

# ======================================
# Основные маршруты приложения
# ======================================

@app.route('/')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session)  # Кеширование для гостей
def index():
    logger.info("Home page access")
    prices = get_current_prices()
    return render_common_template(
        'index.html',
        stripe_public_key=STRIPE_PUBLIC_KEY,
        paid_price=prices['paid'] / 100,
        premium_price=prices['premium'] / 100
    )

@app.route('/contacts')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session)  # Кеширование для гостей
def contacts_page():
    """Страница контактов"""
    logger.info("Contacts page access")
    return render_common_template('contacts.html')

@app.route('/knowledge-base')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session)  # Кеширование для гостей
def knowledge_base():
    """База знаний"""
    logger.info("Knowledge base access")
    return render_common_template('knowledge-base.html')

# ======================================
# Роут для страницы сравнения телефонов
# ======================================

@app.route('/compares')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session)
def compares_page():
    """Страница сравнения спецификаций телефонов"""
    logger.info("Compares page access")
    return render_common_template('compares.html')

# ======================================
# API для сравнения телефонов
# ======================================

@app.route('/compare/search')
def compare_search():
    """Поиск телефонов для сравнения"""
    query = request.args.get('q', '').strip()
    logger.info(f"Phone search: {query}")
    if not query or len(query) < 2:
        logger.debug("Search query too short")
        return jsonify([])

    try:
        # Используем regex для нечеткого поиска
        regex_query = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)
        
        # Ищем по бренду и модели
        results = phonebase_collection.find({
            '$or': [
                {'Бренд': regex_query},
                {'Модель': regex_query},
                {'Brand': regex_query},
                {'Model': regex_query}
            ]
        }).limit(20)
        
        phones = list(results)
        
        # Преобразуем ObjectId в строки
        for phone in phones:
            phone['_id'] = str(phone['_id'])
        
        logger.debug(f"Found {len(phones)} phones for query: {query}")
        return jsonify(phones)
    
    except Exception as e:
        logger.error(f"Phone search error: {str(e)}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/compare/phone/<phone_id>')
def get_phone_details(phone_id):
    """Получение деталей телефона по ID"""
    logger.info(f"Phone details request: {phone_id}")
    try:
        phone = phonebase_collection.find_one({'_id': ObjectId(phone_id)})
        if not phone:
            logger.warning(f"Phone not found: {phone_id}")
            return jsonify({'error': 'Phone not found'}), 404
        
        # Преобразуем ObjectId в строку
        phone['_id'] = str(phone['_id'])
        return jsonify(phone)
    
    except Exception as e:
        logger.error(f"Phone details error: {str(e)}")
        return jsonify({'error': 'Invalid phone ID'}), 400

# ======================================
# Роут для страницы проверки Apple IMEI
# ======================================

@app.route('/applecheck')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session)  # Кеширование для гостей
def apple_check():
    logger.info("Apple check page access")
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

    return render_common_template(
        'applecheck.html',
        service_type=service_type,
        services_data=services_data,
        stripe_public_key=STRIPE_PUBLIC_KEY
    )

# ======================================
# Роут для страницы проверки Android IMEI
# ======================================

@app.route('/androidcheck')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session)  # Кеширование для гостей
def android_check():
    """Страница проверки Android устройств"""
    logger.info("Android check page access")
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

    return render_common_template(
        'androidcheck.html',
        service_type=service_type,
        services_data=services_data,
        stripe_public_key=STRIPE_PUBLIC_KEY
    )

@app.route('/create-checkout-session', methods=['POST'])
@csrf.exempt
def create_checkout_session():
    try:
        data = request.json
        imei = data.get('imei')
        service_type = data.get('service_type')
        use_balance = data.get('use_balance', False)
        idempotency_key = data.get('idempotency_key', secrets.token_hex(16))
        
        logger.info(f"Creating checkout session for IMEI: {imei}, service: {service_type}")
        
        if not validate_imei(imei):
            logger.warning(f"Invalid IMEI: {imei}")
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
            logger.warning(f"Invalid service type: {service_type}")
            return jsonify({'error': 'არასწორი სერვისის ტიპი'}), 400
        
        prices = get_current_prices()
        price_key = price_mapping[service_type]
        amount = prices[price_key]  # в центах
        
        # Для бесплатной проверки не создаем сессию
        if service_type == 'free':
            logger.debug("Free service - no checkout needed")
            return jsonify({'error': 'უფასო შემოწმება არ საჭიროებს გადახდამ'}), 400
        
        # Если пользователь авторизован и выбрал оплату с баланса
        if use_balance and 'user_id' in session:
            user_id = session['user_id']
            # Конвертируем сумму в лари (amount в центах, поэтому делим на 100, чтобы получить лари)
            amount_gel = amount / 100.0
            
            # Генерируем уникальный ключ идемпотентности
            idempotency_key = f"bal_{user_id}_{imei}_{datetime.utcnow().timestamp()}"
            
            # Пытаемся списать средства с баланса
            if stripe_payment.deduct_balance(
                user_id=user_id,
                amount=amount_gel,
                service_type=service_type,
                imei=imei,
                idempotency_key=idempotency_key
            ):
                # Создаем запись о проверке в коллекции checks
                record = {
                    'session_id': idempotency_key,  # используем idempotency_key как session_id для балансовой операции
                    'imei': imei,
                    'service_type': service_type,
                    'paid': True,
                    'payment_status': 'succeeded',
                    'payment_method': 'balance',
                    'amount': amount_gel,
                    'currency': 'gel',
                    'timestamp': datetime.utcnow(),
                    'user_id': ObjectId(user_id),
                    'idempotency_key': idempotency_key,
                    'status': 'pending_verification'  # ожидание выполнения проверки
                }
                if client:
                    checks_collection.insert_one(record)
                    logger.info(f"Balance payment recorded for IMEI: {imei}")
                
                return jsonify({
                    'id': idempotency_key,
                    'payment_method': 'balance'
                })
            else:
                logger.warning(f"Balance deduction failed for user: {user_id}")
                return jsonify({'error': 'ბალანსიდან გადახდა ვერ მოხერხდა'}), 500
        
        # Если не используем баланс (неавторизован или недостаточно средств), создаем сессию Stripe
        base_url = request.host_url.rstrip('/')
        success_url = f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}&imei={imei}&service_type={service_type}"
        
        # Определяем cancel_url в зависимости от типа услуги
        if service_type in ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']:
            cancel_url = f"{base_url}/applecheck?type={service_type}"
        else:
            cancel_url = f"{base_url}/androidcheck?type={service_type}"
        
        # Метаданные для сессии
        metadata = {
            'imei': imei,
            'service_type': service_type,
            'idempotency_key': idempotency_key
        }
        if 'user_id' in session:
            metadata['user_id'] = session['user_id']
        
        # Создаем сессию через StripePayment
        stripe_session = stripe_payment.create_checkout_session(
            imei=imei,
            service_type=service_type,
            amount=amount,  # в центах
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            idempotency_key=idempotency_key
        )
        
        logger.info(f"Stripe session created: {stripe_session.id}")
        return jsonify({
            'id': stripe_session.id,
            'payment_method': 'stripe'
        })
    
    except Exception as e:
        logger.exception(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    imei = request.args.get('imei')
    service_type = request.args.get('service_type')
    
    logger.info(f"Payment success: session_id={session_id}, imei={imei}, service={service_type}")
    
    if not session_id or not imei or not service_type:
        logger.warning("Missing parameters in payment success")
        return render_template('error.html', error="არასაკმარისი პარამეტრები"), 400
    
    # Если session_id начинается с "bal_", то это оплата с баланса
    if session_id.startswith('bal_'):
        # Для балансовой оплаты мы уже создали запись в checks_collection
        # Теперь нужно выполнить проверку и обновить запись
        # Но можно перенаправить сразу на страницу результатов, передав session_id
        # Или отобразить результаты здесь?
        # Пока просто перенаправляем на страницу проверки с параметрами
        apple_services = ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']
        if service_type in apple_services:
            return redirect(url_for('apple_check', type=service_type, imei=imei, session_id=session_id))
        else:
            return redirect(url_for('android_check', type=service_type, imei=imei, session_id=session_id))
    else:
        # Это оплата через Stripe
        try:
            # Получаем сессию Stripe
            stripe_session = stripe.checkout.Session.retrieve(session_id)
            
            # Создаем запись о платеже в коллекции checks
            record = {
                'stripe_session_id': session_id,
                'imei': imei,
                'service_type': service_type,
                'paid': True,
                'payment_status': stripe_session.payment_status,
                'amount': stripe_session.amount_total / 100,  # переводим в лари
                'currency': stripe_session.currency,
                'timestamp': datetime.utcnow(),
                'status': 'pending_verification'  # ожидание выполнения проверки
            }
            if 'user_id' in session:
                record['user_id'] = ObjectId(session['user_id'])
            if client:
                checks_collection.insert_one(record)
                logger.info(f"Payment recorded: {session_id}")
            
            # Перенаправляем на страницу проверки с параметрами
            apple_services = ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']
            if service_type in apple_services:
                return redirect(url_for('apple_check', type=service_type, imei=imei, session_id=session_id))
            else:
                return redirect(url_for('android_check', type=service_type, imei=imei, session_id=session_id))
        
        except Exception as e:
            logger.exception(f"Payment success error: {str(e)}")
            return render_template('error.html', error=str(e)), 500

@app.route('/get_check_result')
def get_check_result():
    session_id = request.args.get('session_id')
    logger.info(f"Check result request: {session_id}")
    if not session_id:
        logger.warning("Missing session_id in check result request")
        return jsonify({'error': 'სესიის ID არის მითითებული'}), 400
    
    if not client:
        logger.error("Database unavailable")
        return jsonify({'error': 'Database unavailable'}), 500
    
    # Ищем как по session_id (баланс), так и по stripe_session_id (Stripe)
    record = checks_collection.find_one({
        '$or': [
            {'session_id': session_id},
            {'stripe_session_id': session_id}
        ]
    })
    if not record:
        logger.warning(f"Check result not found: {session_id}")
        return jsonify({'error': 'შედეგი ვერ მოიძებნა'}), 404
    
    return jsonify({
        'imei': record['imei'],
        'result': record['result']
    })

@app.route('/perform_check', methods=['POST'])
@csrf.exempt
def perform_check():
    try:
        data = request.get_json()
        imei = data.get('imei')
        service_type = data.get('service_type')
        
        logger.info(f"Check request: IMEI={imei}, service={service_type}")
        
        if not imei or not service_type:
            logger.warning("Missing parameters in perform_check")
            return jsonify({'error': 'არასაკმარისი პარამეტრები'}), 400
        
        if not validate_imei(imei):
            logger.warning(f"Invalid IMEI: {imei}")
            return jsonify({'error': 'IMEI-ის არასწორი ფორმატი'}), 400
        
        # Проверяем кеш для бесплатных запросов
        if service_type == 'free':
            cache_key = f"free_check_{imei}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Using cached result for IMEI: {imei}")
                return jsonify(cached_result)
        
        # Пытаемся получить семафор с таймаутом
        acquired = REQUEST_SEMAPHORE.acquire(timeout=15)
        if not acquired:
            logger.warning(f"Semaphore timeout for IMEI: {imei}")
            return jsonify({'error': 'სისტემა დატვირთულია, გთხოვთ სცადოთ მოგვიანებით'}), 503
        
        try:
            # Выполняем проверку
            time.sleep(1)  # Искусственная задержка перед запросом
            
            attempts = 0
            max_attempts = 3
            delay = 2  # seconds
            result = None
            
            while attempts < max_attempts:
                try:
                    result = perform_api_check(imei, service_type)
                    
                    # Искусственная задержка для обработки ответа
                    time.sleep(0.5)
                    
                    if result and 'error' not in result:
                        break
                    
                    # Повторная попытка при ошибках сервера
                    if result and 'error' in result and 'სერვერის' in result['error']:
                        raise Exception(f"Server error: {result['error']}")
                        
                except Exception as e:
                    attempts += 1
                    if attempts < max_attempts:
                        time.sleep(delay)
                        delay *= 2  # Экспоненциальная задержка
                    else:
                        return jsonify({
                            'error': f'Request failed after {max_attempts} attempts',
                            'details': str(e)
                        }), 500
        
            if not result:
                logger.error(f"Empty API response for IMEI: {imei}")
                return jsonify({'error': 'API-დან ცარიელი პასუხი'}), 500
            
            if 'error' in result:
                logger.warning(f"API error for IMEI: {imei} - {result['error']}")
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
            
            # Сохраняем результат для бесплатных проверок
            if service_type == 'free' and client:
                # Извлекаем статус из результата
                status = 'unknown'
                if isinstance(result, dict):
                    status = result.get('status') or result.get('სტატუსი', 'unknown')
                
                record = {
                    'imei': imei,
                    'service_type': service_type,
                    'paid': False,
                    'status': status,   # сохраняем статус
                    'timestamp': datetime.utcnow(),
                    'result': result
                }
                if 'user_id' in session:
                    record['user_id'] = ObjectId(session['user_id'])
                checks_collection.insert_one(record)
                
                # Кешируем результат на 10 минут
                cache.set(f"free_check_{imei}", result, timeout=600)
                logger.debug(f"Free check cached for IMEI: {imei}")
            
            logger.info(f"Check completed for IMEI: {imei}")
            return jsonify(result)
        
        finally:
            REQUEST_SEMAPHORE.release()
    
    except Exception as e:
        logger.exception(f'Check error: {str(e)}')
        return jsonify({'error': 'სერვერული შეცდომა'}), 500

@app.route('/reparse_imei')
def reparse_imei():
    imei = request.args.get('imei')
    logger.info(f"Reparse request: {imei}")
    if not client:
        logger.error("Database unavailable")
        return jsonify({'error': 'Database unavailable'}), 500
        
    # Ищем последнюю запись бесплатной проверки для этого IMEI
    record = checks_collection.find_one(
        {'imei': imei, 'service_type': 'free'},
        sort=[('timestamp', -1)]  # Берем последнюю запись
    )
    
    if not record or 'result' not in record or 'html_content' not in record.get('result', {}):
        logger.warning(f"No free check record found for IMEI: {imei}")
        return jsonify({'error': 'მონაცემები ვერ მოიძებნა'}), 404
    
    html_content = record['result']['html_content']
    parsed_data = parse_free_html(html_content)
    
    if parsed_data:
        parsed_data['reparsed'] = True
        return jsonify(parsed_data)
    
    return jsonify({
        'error': 'დამუშავება ვერ მოხერხდა',
        'server_response': BeautifulSoup(html_content, 'html.parser').get_text()
    })

# ======================================
# Роут для получения баланса пользователя
# ======================================

@app.route('/user/get_balance', methods=['GET'])
@login_required
def get_balance():
    """Возвращает текущий баланс пользователя в формата JSON"""
    user_id = session.get('user_id')
    logger.info(f"Balance request for user: {user_id}")
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Получаем пользователя из базы данных
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            logger.warning(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404

        balance = user.get('balance', 0)
        logger.debug(f"Balance retrieved: {balance}")
        # Возвращаем баланс пользователя
        return jsonify({
            'balance': balance
        })
    except (TypeError, InvalidId) as e:
        logger.error(f"Invalid user ID: {user_id} - {str(e)}")
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        logger.exception(f"Error getting balance: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

# ======================================
# Webhook Manager
# ======================================

def send_webhook_event(event_type, payload):
    if not client:
        logger.warning("Database unavailable for webhook")
        return
        
    # Получаем коллекцию вебхуков
    webhooks_collection = client.imeicheck.webhooks
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
            logger.info(f"Webhook sent to {webhook['url']} - status {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook error for {webhook['url']}: {str(e)}")
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
        logger.info(f"Carousel folder created: {path}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error creating carousel folder: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload-carousel-image', methods=['POST'])
def upload_carousel_image():
    """Загружает изображение для карусели"""
    if 'carouselImage' not in request.files:
        logger.warning("No file in carousel upload")
        return jsonify({'success': False, 'error': 'ფაილი არ არის ატვირთული'}), 400
    
    file = request.files['carouselImage']
    if file.filename == '':
        logger.warning("Empty filename in carousel upload")
        return jsonify({'success': False, 'error': 'ფაილი არ არის არჩეული'}), 400
    
    try:
        # Сохраняем в папку carousel
        upload_folder = 'static/img/carousel'
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = f"carousel_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        logger.info(f"Carousel image uploaded: {file_path}")
        
        return jsonify({
            'success': True, 
            'filePath': f'/{file_path}'
        })
    except Exception as e:
        logger.error(f"Error uploading carousel image: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Регистрация блюпринтов
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

# Установка CSRF-куки для AJAX
@app.after_request
def set_csrf_cookie(response):
    # Не устанавливаем CSRF для статики и API
    if not request.path.startswith(('/static', '/api')):
        secure = app.config['SESSION_COOKIE_SECURE']
        response.set_cookie(
            'csrf_token', 
            generate_csrf(),
            secure=secure,
            httponly=True,
            samesite='Lax'
        )
    return response

# Обработчик ошибок CSRF
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    logger.warning(f"CSRF error: {e.description}")
    return jsonify({'error': f'CSRF token error: {e.description}'}), 400

# Роут для отладки сессии
@app.route('/session-info')
def session_info():
    logger.info("Session info request")
    return jsonify({
        'user_id': session.get('user_id'),
        'role': session.get('role'),
        'session_id': session.sid
    })

@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 error: {request.url}")
    return render_template(
        'error.html', 
        code=404,
        message="გვერდი ვერ მოიძებნა"
    ), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 error: {str(e)}")
    return render_template(
        'error.html', 
        code=500,
        message="სერვერზე შეცდომა მოხდა"
    ), 500

# ======================================
# Health Check
# ======================================

@app.route('/health')
@cache.cached(timeout=30)  # Кеширование health check
def health_check():
    logger.info("Health check request")
    status = {
        'status': 'OK',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # Проверка MongoDB
    if client:
        try:
            db = client.get_database()
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
    
    return jsonify(status), 200 if status['status'] == 'OK' else 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
