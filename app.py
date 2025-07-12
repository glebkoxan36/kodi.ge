import os
import json
import logging
import re
import hmac
import secrets
import hashlib
import requests
import time
import threading
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, current_app, Blueprint
from flask_cors import CORS
import stripe
from functools import wraps
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from flask_session import Session
from bs4 import BeautifulSoup

# Импорт модулей
from auth import auth_bp
from ifreeapi import validate_imei, perform_api_check, parse_free_html
from db import client, regular_users_collection, checks_collection, payments_collection, refunds_collection, phonebase_collection, prices_collection, comparisons_collection
from stripepay import StripePayment
from compares import compare_phones, save_comparison  # Добавлен импорт

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Настройки сессии
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
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

# Регистрируем функцию в контексте шаблонов
@app.context_processor
def inject_utils():
    return {
        'generate_avatar_color': generate_avatar_color,
        'csrf_token': generate_csrf
    }

# Контекстный процессор для передачи данных пользователя
@app.context_processor
def inject_user_data():
    if 'user_id' in session and client:
        user = regular_users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if user:
            avatar_color = generate_avatar_color(
                user.get('first_name', '') + ' ' + user.get('last_name', ''))
            return {
                'currentUser': {
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0.0),
                    'avatar_color': avatar_color
                }
            }
    return {'currentUser': None}

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
                avatar_color = generate_avatar_color(
                    user.get('first_name', '') + ' ' + user.get('last_name', ''))
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
                         currentUser=user_data)

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
    
    return render_template('contacts.html', currentUser=user_data)

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
    
    return render_template('knowledge-base.html', currentUser=user_data)

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
        services_data=services_data,
        stripe_public_key=STRIPE_PUBLIC_KEY,
        currentUser=user_data
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
        currentUser=user_data
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
                
                return jsonify({
                    'id': idempotency_key,
                    'payment_method': 'balance'
                })
            else:
                return jsonify({'error': 'ბალანსიდან გადახდა ვერ მოხერხდა'}), 500
        
        # Если не используем баланс (неавторизован или недостаточно средств), создаем сессию Stripe
        base_url = request.host_url.rstrip('/')
        success_url = f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}&imei={imei}&service_type={service_type}"
        
        # Определяем cancel_url в зависимости от типа услуги
        if service_type in ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']:
            cancel_url = f"{base_url}/apple_check?type={service_type}"
        else:
            cancel_url = f"{base_url}/android_check?type={service_type}"
        
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
        
        return jsonify({
            'id': stripe_session.id,
            'payment_method': 'stripe'
        })
    
    except Exception as e:
        app.logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    imei = request.args.get('imei')
    service_type = request.args.get('service_type')
    
    if not session_id or not imei or not service_type:
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
            
            # Перенаправляем на страницу проверки с параметрами
            apple_services = ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']
            if service_type in apple_services:
                return redirect(url_for('apple_check', type=service_type, imei=imei, session_id=session_id))
            else:
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

@app.route('/perform_check', methods=['POST'])
@csrf.exempt
def perform_check():
    try:
        data = request.get_json()
        imei = data.get('imei')
        service_type = data.get('service_type')
        
        app.logger.info(f"Check started for IMEI: {imei}, service: {service_type}")
        
        if not imei or not service_type:
            return jsonify({'error': 'არასაკმარისი პარამეტრები'}), 400
        
        if not validate_imei(imei):
            return jsonify({'error': 'IMEI-ის არასწორი ფორმატი'}), 400
        
        # Пытаемся получить семафор с таймаутом
        acquired = REQUEST_SEMAPHORE.acquire(timeout=15)
        if not acquired:
            app.logger.warning(f"Semaphore timeout for IMEI: {imei}")
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
            
            app.logger.info(f"Check completed for IMEI: {imei}")
            return jsonify(result)
        
        finally:
            REQUEST_SEMAPHORE.release()
    
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
        parsed_data['reparsed'] = True
        return jsonify(parsed_data)
    
    return jsonify({
        'error': 'დამუშავება ვერ მოხერხდა',
        'server_response': BeautifulSoup(html_content, 'html.parser').get_text()
    })

@app.route('/stripe_webhook', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Обработка вебхука через StripePayment
        event = stripe_payment.handle_webhook(payload, sig_header)
        return jsonify({'status': 'success'}), 200
    
    except ValueError as e:
        return jsonify({'error': 'არასწორი მონაცემები'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'არასწორი ხელმოწერა'}), 400
    except Exception as e:
        app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'error': 'სერვერული შეცდომა'}), 500

@app.route('/refund_payment', methods=['POST'])
@csrf.exempt
@login_required
def refund_payment():
    try:
        data = request.json
        payment_id = data.get('payment_id')
        amount = data.get('amount')
        reason = data.get('reason', 'Customer request')
        
        if not payment_id or not amount:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        user_id = session['user_id']
        
        # Проверяем права пользователя на возврат
        payment = payments_collection.find_one({
            '_id': ObjectId(payment_id),
            'user_id': ObjectId(user_id)
        })
        
        if not payment:
            return jsonify({'error': 'Payment not found or access denied'}), 404
        
        # Выполняем возврат через StripePayment
        result = stripe_payment.create_refund(
            payment_id=payment_id,
            amount=amount,
            currency=payment['currency'],
            reason=reason,
            idempotency_key=secrets.token_hex(16)
        )
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Refund error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    last_checks = list(checks_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).limit(5))
    
    # Последние 5 платежей
    last_payments = list(payments_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).limit(5))
    
    # Общее количество проверок
    total_checks = checks_collection.count_documents({'user_id': ObjectId(user_id)})
    
    # Генерируем цвет аватара
    avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
    
    return render_template(
        'user/dashboard.html',
        user=user,
        balance=balance,
        last_checks=last_checks,
        last_payments=last_payments,
        total_checks=total_checks,
        stripe_public_key=STRIPE_PUBLIC_KEY,
        avatar_color=avatar_color  # Передаем цвет аватара
    )

@user_bp.route('/settings')
@login_required
def settings():
    """Страница настроек пользователя"""
    user_id = session['user_id']
    if not client:
        flash('Database unavailable', 'danger')
        return redirect(url_for('auth.login'))
    
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
    
    return render_template(
        'user/settings.html',
        user=user,
        avatar_color=avatar_color
    )

@user_bp.route('/topup', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def topup_balance():
    """Пополнение баланса"""
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        if amount < 1:
            flash('მინიმალური თანხა $1', 'danger')
            return redirect(url_for('user.topup_balance'))
        
        # Используем StripePayment для создания сессии пополнения
        try:
            base_url = request.host_url.rstrip('/')
            success_url = f"{base_url}/user/topup/success"
            cancel_url = f"{base_url}/user/topup"
            idempotency_key = secrets.token_hex(16)
            
            stripe_session = stripe_payment.create_topup_session(
                user_id=str(session['user_id']),
                amount=amount,
                success_url=success_url,
                cancel_url=cancel_url,
                idempotency_key=idempotency_key
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

# Ключевое исправление: добавлен алиас для совместимости
@user_bp.route('/accounts')
@user_bp.route('/payment_history')  # Добавлен алиас для совместимости
@login_required
def payment_history():
    """История платежей"""
    user_id = session['user_id']
    if not client:
        flash('Database unavailable', 'danger')
        return redirect(url_for('auth.login'))
    
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    # Получаем всю историю платежей
    payments = list(payments_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1))
    
    return render_template(
        'user/accounts.html',
        user=user,
        payments=payments
    )

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
    
    # Исправленный запрос с пагинацией
    query = checks_collection.find({'user_id': ObjectId(user_id)})
    query = query.sort('timestamp', -1)
    query = query.skip((page - 1) * per_page).limit(per_page)
    checks = list(query)
    
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

# Новый роут для получения деталей проверки
@user_bp.route('/check-details/<check_id>')
@login_required
def check_details(check_id):
    """Возвращает детали проверки IMEI в формате JSON"""
    try:
        obj_id = ObjectId(check_id)
    except:
        return jsonify({'error': 'Invalid check ID'}), 400

    user_id = ObjectId(session['user_id'])
    check = checks_collection.find_one({'_id': obj_id, 'user_id': user_id})

    if not check:
        return jsonify({'error': 'Check not found'}), 404

    # Определяем статус
    status = 'unknown'
    # Если в записи нет статуса, попробуем взять из результата
    if status == 'unknown' and isinstance(check.get('result'), dict):
        result = check.get('result')
        status = result.get('status') or result.get('სტატუსი', 'unknown')

    # Собираем детали
    details = {
        'imei': check.get('imei', ''),
        'timestamp': check['timestamp'].strftime('%Y-%m-%d %H:%M'),
        'status': status,
        'device_info': '',
        'additional_info': ''
    }

    result = check.get('result')
    if isinstance(result, dict):
        # Получаем модель
        model = result.get('model') or result.get('მოდელი') or result.get('device_model') or ''
        details['device_info'] = model

        # Собираем дополнительные поля, исключая некоторые
        excluded_keys = ['status', 'სტატუსი', 'model', 'მოდელი', 'server_response', 'service_type', 'imei', 'device_model']
        additional_info_parts = []
        for key, value in result.items():
            if key not in excluded_keys:
                additional_info_parts.append(f"{key}: {value}")

        details['additional_info'] = '\n'.join(additional_info_parts) or 'დამატებითი ინფორმაცია არ არის'
    else:
        # Если результат не словарь, то выводим как есть
        details['additional_info'] = str(result) or 'დამატებითი ინფორმაცია არ არის'

    return jsonify(details)

# ======================================
# Compare Blueprint (Сравнение телефонов)
# ======================================

compare_bp = Blueprint('compare', __name__, url_prefix='/compare')

@compare_bp.route('/')
def compare_index():
    """Главная страница сравнения телефонов"""
    return render_template('compares.html')

@compare_bp.route('/search', methods=['GET'])
def search_phones():
    """Поиск телефонов в базе данных"""
    query = request.args.get('q', '')
    results = []
    
    if query:
        # Ищем по бренду или модели (регистронезависимо)
        regex = re.compile(f'.*{query}.*', re.IGNORECASE)
        results = list(phonebase_collection.find({
            "$or": [
                {"Бренд": regex},
                {"Модель": regex},
                {"Brand": regex},  # английские варианты
                {"Model": regex}
            ]
        }).limit(10))
        
        # Преобразуем ObjectId в строку для JSON
        for phone in results:
            phone['_id'] = str(phone['_id'])
    
    return jsonify(results)

@compare_bp.route('/phone/<phone_id>')  # Изменено с /details/ на /phone/
def phone_details(phone_id):
    """Получение деталей конкретного телефона"""
    try:
        phone = phonebase_collection.find_one({"_id": ObjectId(phone_id)})
        if phone:
            # Преобразуем ObjectId и удаляем ненужные поля
            phone['_id'] = str(phone['_id'])
            return jsonify(phone)
        return jsonify({"error": "Phone not found"}), 404
    except:
        return jsonify({"error": "Invalid ID"}), 400

@compare_bp.route('/perform', methods=['POST'])
@csrf.exempt
@login_required
def perform_comparison():
    """Выполняет сравнение двух телефонов"""
    try:
        data = request.json
        phone1_id = data.get('phone1_id')
        phone2_id = data.get('phone2_id')
        
        if not phone1_id or not phone2_id:
            return jsonify({'success': False, 'error': 'Необходимо выбрать два телефона'}), 400
        
        # Получаем данные телефонов
        phone1 = phonebase_collection.find_one({"_id": ObjectId(phone1_id)})
        phone2 = phonebase_collection.find_one({"_id": ObjectId(phone2_id)})
        
        if not phone1 or not phone2:
            return jsonify({'success': False, 'error': 'Один из телефонов не найден'}), 404
        
        # Сравниваем телефоны
        result = compare_phones(phone1, phone2)
        
        # Сохраняем результаты
        user_id = session.get('user_id')
        save_comparison(user_id, phone1_id, phone2_id, result)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        app.logger.error(f"Comparison error: {str(e)}")
        return jsonify({'success': False, 'error': 'Ошибка сравнения', 'details': str(e)}), 500

@compare_bp.route('/history')
@login_required
def comparison_history():
    """История сравнений пользователя"""
    user_id = session['user_id']
    if not client:
        return jsonify({'error': 'Database unavailable'}), 500
        
    comparisons = list(comparisons_collection.find(
        {'user_id': ObjectId(user_id)}
    ).sort('timestamp', -1).limit(10))
    
    # Преобразуем ObjectId в строку
    for comp in comparisons:
        comp['_id'] = str(comp['_id'])
        comp['phone1_id'] = str(comp['phone1_id'])
        comp['phone2_id'] = str(comp['phone2_id'])
        comp['timestamp'] = comp['timestamp'].isoformat()
    
    return jsonify(comparisons)

# ======================================
# Регистрация блюпринтов
# ======================================

# Заглушка для админ-панели
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/admin_dashboard')
def admin_dashboard():
    return "Admin Dashboard"

# Регистрация блюпринтов
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(compare_bp)  # новый блюпринт

# Установка CSRF-куки для AJAX
@app.after_request
def set_csrf_cookie(response):
    if request.path.startswith('/'):
        # Убедитесь что сессия сохранена
        session.modified = True
        response.set_cookie('csrf_token', generate_csrf())
    return response

# Обработчик ошибок CSRF
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    app.logger.warning(f"CSRF error: {e.description}")
    return jsonify({'error': f'CSRF token error: {e.description}'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
