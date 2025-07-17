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
from pymongo.errors import PyMongoError

# Импорт модулей
from auth import auth_bp
from user_dashboard import user_bp
from ifreeapi import validate_imei, perform_api_check
from db import client, regular_users_collection, checks_collection, payments_collection, refunds_collection, phonebase_collection, prices_collection, admin_users_collection, parser_logs_collection, audit_logs_collection, api_keys_collection, webhooks_collection, db
from stripepay import StripePayment
from admin_routes import admin_bp  # Импорт админских роутов
from test import test_bp  # Импорт тестового модуля
from price import get_current_prices, get_service_price  # Добавлено

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

# Обновленная конфигурация сессии
app.config.update(
    SESSION_TYPE='mongodb',
    SESSION_MONGODB=client,
    SESSION_MONGODB_DB='imei_checker',
    SESSION_MONGODB_COLLECT='sessions',
    SESSION_COOKIE_NAME='imeicheck_session',
    SESSION_COOKIE_DOMAIN=os.getenv('SESSION_DOMAIN', None),
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=True,
    
    # Исключение админ-логина из CSRF-защиты
    WTF_CSRF_EXEMPT_ROUTES = ['auth.admin_login'],
    WTF_CSRF_ENABLED = True  # Явное включение CSRF защиты
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

# Контекстный процессор для добавления данных пользователя во все шаблоны
@app.context_processor
def inject_user():
    """Добавляет данные текущего пользователя во все шаблоны"""
    user_data = None
    is_admin = False
    role = 'user'
    admin_role = None
    admin_username = None
    is_impersonation = False
    
    # Проверяем администратора
    if 'admin_id' in session and 'admin_role' in session:
        try:
            admin = admin_users_collection.find_one({'_id': ObjectId(session['admin_id'])})
            if admin:
                is_admin = True
                admin_role = session['admin_role']
                admin_username = admin.get('username')
                # Если есть user_id - это режим имперсонации
                if 'user_id' in session:
                    is_impersonation = True
                    role = 'impersonation'
        except (TypeError, InvalidId):
            session.pop('admin_id', None)
            session.pop('admin_role', None)
            logger.warning("Invalid admin ID in session - cleared")
    
    # Проверяем обычного пользователя
    if 'user_id' in session:
        try:
            user = regular_users_collection.find_one({'_id': ObjectId(session['user_id'])})
            if user:
                name_part = user.get('first_name') or user.get('email', 'user')
                avatar_color = user.get('avatar_color') or generate_avatar_color(name_part)
                
                user_data = {
                    'id': str(user['_id']),
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'balance': user.get('balance', 0),
                    'avatar_color': avatar_color,
                    'avatar_url': user.get('avatar_url'),
                    'is_admin': is_admin,
                    'role': role,
                    'admin_role': admin_role,
                    'admin_username': admin_username,
                    'is_impersonation': is_impersonation
                }
        except (TypeError, InvalidId):
            session.pop('user_id', None)
            logger.warning("Invalid user ID in session - cleared")
        except Exception as e:
            logger.exception(f"Error getting user: {str(e)}")
    
    return {'currentUser': user_data, 'admin_username': admin_username}

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
        # Проверяем роль в сессии и наличие admin_id
        if 'admin_id' not in session or 'admin_role' not in session:
            logger.warning(f"Unauthorized admin access attempt: session={dict(session)}")
            return redirect(url_for('auth.admin_login', next=request.url))
        
        # Проверяем существование администратора в базе
        try:
            admin = admin_users_collection.find_one({'_id': ObjectId(session['admin_id'])})
            if not admin or admin.get('role') not in ['admin', 'superadmin']:
                flash('Administrator account not found or invalid', 'danger')
                session.clear()
                return redirect(url_for('auth.admin_login'))
        except:
            session.clear()
            return redirect(url_for('auth.admin_login'))
            
        return f(*args, **kwargs)
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Разрешаем доступ если есть user_id ИЛИ admin_id
        if 'user_id' not in session and 'admin_id' not in session:
            logger.warning("Unauthorized access attempt")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# ======================================
# Обработчики для управления сессиями
# ======================================

@app.before_request
def refresh_session():
    """Автоматически обновляет срок действия сессии"""
    if 'user_id' in session or 'admin_id' in session:
        session.modified = True
        session.permanent = True

@app.before_request
def check_session_timeout():
    """Проверяет тайм-аут сессии"""
    last_activity = session.get('last_activity')
    if last_activity:
        last_active = datetime.fromisoformat(last_activity)
        if (datetime.utcnow() - last_active).seconds > 3600:  # 1 час
            session.clear()
            flash('Your session has expired due to inactivity', 'warning')
            return redirect(url_for('auth.login'))
    
    # Обновляем время последней активности
    session['last_activity'] = datetime.utcnow().isoformat()

@app.before_request
def check_session_integrity():
    """Проверяет целостность сессии администратора"""
    if 'admin_id' in session:
        try:
            admin = admin_users_collection.find_one({'_id': ObjectId(session['admin_id'])})
            if not admin or admin.get('role') not in ['admin', 'superadmin']:
                session.pop('admin_id', None)
                session.pop('admin_role', None)
                session.pop('admin_username', None)
                flash('Administrator session is invalid', 'danger')
                return redirect(url_for('auth.admin_login'))
        except:
            session.pop('admin_id', None)
            session.pop('admin_role', None)
            session.pop('admin_username', None)

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
def index():
    logger.info("Home page access")
    prices = get_current_prices()
    return render_common_template(
        'index.html',
        stripe_public_key=STRIPE_PUBLIC_KEY,
    )

@app.route('/contacts')
def contacts_page():
    """Страница контактов"""
    logger.info("Contacts page access")
    return render_common_template('contacts.html')

@app.route('/knowledge-base')
def knowledge_base():
    """База знаний"""
    logger.info("Knowledge base access")
    return render_common_template('knowledge-base.html')

# ======================================
# Роут для страницы сравнения телефонов
# ======================================

@app.route('/compares')
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
def apple_check():
    logger.info("Apple check page access")
    # Определяем тип услуги из параметра URL
    service_type = request.args.get('type', 'free')
    
    # Получаем текущие цены
    prices = get_current_prices()
    
    # Создаем словарь цен для каждого типа услуги
    service_prices = {
        'free': 'უფასო',
        'fmi': f"{prices['fmi'] / 100:.2f}₾",
        'blacklist': f"{prices['blacklist'] / 100:.2f}₾",
        'sim_lock': f"{prices['sim_lock'] / 100:.2f}₾",
        'activation': f"{prices['activation'] / 100:.2f}₾",
        'carrier': f"{prices['carrier'] / 100:.2f}₾",
        'mdm': f"{prices['mdm'] / 100:.2f}₾"
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
def android_check():
    """Страница проверки Android устройств"""
    logger.info("Android check page access")
    service_type = request.args.get('type', '')
    prices = get_current_prices()

    service_prices = {
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

def perform_background_check(imei, service_type, session_id):
    """Выполняет проверку в фоновом режиме и обновляет запись в базе"""
    from ifreeapi import perform_api_check
    from datetime import datetime
    try:
        logger.info(f"Background check started for session: {session_id}")
        result = perform_api_check(imei, service_type)
        
        # Обновляем запись в базе
        update_data = {
            'result': result,
            'status': 'completed',
            'completed_at': datetime.utcnow()
        }
        
        # Используем глобальную checks_collection
        if checks_collection is not None:
            checks_collection.update_one(
                {'session_id': session_id},
                {'$set': update_data}
            )
            logger.info(f"Background check completed for session: {session_id}")
        else:
            logger.error("Checks collection is not available")
    except Exception as e:
        logger.exception(f"Background check failed: {str(e)}")

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
        
        # Получаем цену для сервиса
        amount = get_service_price(service_type)
        
        # Для бесплатной проверки не создаем сессию
        if service_type == 'free':
            logger.debug("Free service - no checkout needed")
            return jsonify({'error': 'უფასო შემოწმება არ საჭიროებს გადახდამ'}), 400
        
        # Если пользователь авторизован и выбрал оплату с баланса
        if use_balance and 'user_id' in session:
            user_id = session['user_id']
            # Конвертируем сумму в лари
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
                
                # Запускаем фоновую проверку
                threading.Thread(
                    target=perform_background_check,
                    args=(imei, service_type, idempotency_key),
                    daemon=True
                ).start()
                
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
    
    try:
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
        
        # Проверяем наличие результата
        if 'result' not in record:
            logger.info(f"Check result not ready for session: {session_id}")
            return jsonify({
                'status': 'pending',
                'message': 'შემოწმება მიმდინარეობს, გთხოვთ მოიცადოთ'
            }), 202
        
        return jsonify({
            'imei': record['imei'],
            'result': record['result']
        })
    
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'მონაცემთა ბაზა დროებით მიუწვდომელია'}), 503
    except Exception as e:
        logger.exception(f"Error retrieving check result: {str(e)}")
        return jsonify({'error': 'შეცდომა მონაცემების მოძიებაში'}), 500

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
        
        # Выполняем проверку
        result = perform_api_check(imei, service_type)
        
        # Сохраняем результат в базу данных
        if client:
            record = {
                'imei': imei,
                'service_type': service_type,
                'timestamp': datetime.utcnow(),
                'result': result
            }
            if 'user_id' in session:
                record['user_id'] = ObjectId(session['user_id'])
            checks_collection.insert_one(record)
        
        logger.info(f"Check completed for IMEI: {imei}")
        return jsonify(result)
    
    except Exception as e:
        logger.exception(f'Check error: {str(e)}')
        return jsonify({'error': 'სერვერული შეცდომა'}), 500

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
    except PyMongoError as e:
        logger.error(f"MongoDB error: {str(e)}")
        return jsonify({'error': 'Database unavailable'}), 503
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
app.register_blueprint(test_bp, url_prefix='/test')  # Регистрация тестового модуля

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
        'admin_id': session.get('admin_id'),
        'admin_role': session.get('admin_role'),
        'admin_username': session.get('admin_username'),
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

# Глобальный обработчик ошибок
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Глобальный обработчик непредвиденных ошибок"""
    logger.exception(f"Unexpected error: {str(e)}")
    
    # Определяем тип ошибки для пользователя
    error_type = "internal"
    if isinstance(e, KeyError):
        error_type = "data_missing"
    elif isinstance(e, PyMongoError):
        error_type = "database"
    
    return jsonify({
        'error': 'Internal server error',
        'error_type': error_type,
        'request_id': secrets.token_hex(8),
        'message': 'Please try again later or contact support'
    }), 500

# ======================================
# Health Check
# ======================================

@app.route('/health')
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
