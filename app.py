import os
import json
import logging
import secrets
import re
import hmac
import threading
import hashlib
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_cors import CORS
import stripe
from functools import wraps, lru_cache
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from flask_session import Session
from flask_caching import Cache
from pymongo.errors import PyMongoError
from flask_pymongo import PyMongo
from celery import Celery
import celery.states as states
import jwt
import requests

# Импорт модулей
from auth import auth_bp
from user_dashboard import user_bp
from ifreeapi import perform_api_check
from db import client, db, regular_users_collection, checks_collection, payments_collection, refunds_collection, prices_collection, admin_users_collection, parser_logs_collection, audit_logs_collection, api_keys_collection, webhooks_collection, phonebase_collection
from stripepay import StripePayment
from admin_routes import admin_bp
from price import get_current_prices, get_service_price, init_prices
from utilities import (
    validate_imei, 
    generate_avatar_color, 
    get_apple_services_data, 
    get_android_services_data,
)

# Настройка корневого логгера
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Создаем директорию для логов если ее не существует
log_dir = '/kodige/mexsiereb'
try:
    os.makedirs(log_dir, exist_ok=True)
    root_logger.info(f"Log directory created: {log_dir}")
except Exception as e:
    root_logger.error(f"Failed to create log directory: {str(e)}")
    # Если не удалось создать, используем текущую директорию
    log_dir = '.'

# Обработчик для записи в файл
log_file_path = os.path.join(log_dir, 'app.log')
file_handler = RotatingFileHandler(
    log_file_path, 
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

# Уровень логирования для production
if os.getenv('FLASK_ENV') == 'production':
    root_logger.setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

# Инициализация Celery
celery = Celery(
    app.name,
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Конфигурация Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=280,
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Инициализация PyMongo
app.config["MONGO_URI"] = os.getenv('MONGODB_URI')
mongo = PyMongo(app)

# Инициализация кэширования
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Логгер для app.py
logger = logging.getLogger(__name__)
logger.info("Application starting")

# Инициализация цен после подключения к БД
if client:
    logger.info("Initializing prices")
    init_prices()
else:
    logger.warning("Skipping price initialization - MongoDB not available")

# Конфигурация сессии
app.config.update(
    SESSION_TYPE='mongodb',
    SESSION_MONGODB=client,
    SESSION_MONGODB_DB='imei_checker',
    SESSION_MONGODB_COLLECT='sessions',
    SESSION_COOKIE_NAME='imeicheck_session',
    SESSION_COOKIE_DOMAIN=os.getenv('SESSION_DOMAIN', None),
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=True,
    
    # Корректная конфигурация CSRF
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_CHECK_DEFAULT=True,
    WTF_CSRF_SSL_STRICT=False,
    WTF_CSRF_TIME_LIMIT=3600,
    WTF_CSRF_EXEMPT_ROUTES = [
        'stripe_webhook',
        'get_check_result',
        'health',
        'auth.facebook_callback',
        'scan_imei'
    ]
)
Session(app)

# Инициализация CSRF защиты
csrf = CSRFProtect(app)
csrf.exempt(auth_bp)

# Фильтр для форматирования даты в шаблонах Jinja2
@app.template_filter('format_datetime')
def format_datetime_filter(value, format='%d.%m.%Y %H:%M'):
    """Фильтр для форматирования даты в шаблонах Jinja2"""
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        return dt.strftime(format)
    except:
        return value

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
    if 'admin_id' in session:
        try:
            admin = admin_users_collection.find_one(
                {'_id': ObjectId(session['admin_id'])},
                projection={'username': 1, 'role': 1}
            )
            if admin:
                is_admin = True
                admin_role = admin.get('role')
                admin_username = admin.get('username')
                session['admin_role'] = admin_role
                
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
            user = regular_users_collection.find_one(
                {'_id': ObjectId(session['user_id'])},
                projection={'first_name': 1, 'last_name': 1, 'balance': 1, 'avatar_color': 1, 'avatar_url': 1, 'email': 1, 'username': 1}
            )
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
                    'is_impersonation': is_impersonation,
                    'username': user.get('username', '')
                }
        except (TypeError, InvalidId):
            session.pop('user_id', None)
            logger.warning("Invalid user ID in session - cleared")
        except Exception as e:
            logger.exception(f"Error getting user: {str(e)}")
    
    return {
        'currentUser': user_data, 
        'admin_username': admin_username
    }

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
        if 'admin_id' not in session or 'admin_role' not in session:
            logger.warning(f"Unauthorized admin access attempt: session={dict(session)}")
            return redirect(url_for('auth.admin_login', next=request.url))
        
        try:
            admin = admin_users_collection.find_one(
                {'_id': ObjectId(session['admin_id'])},
                projection={'role': 1}
            )
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
        # Список публичных страниц, не требующих авторизации
        public_paths = [
            '/', 
            '/contacts', 
            '/knowledge-base', 
            '/politika', 
            '/applecheck', 
            '/androidcheck',
            '/compare'
        ]
        
        # Если запрос к публичной странице, пропускаем
        if request.path in public_paths:
            return f(*args, **kwargs)
            
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
    """Проверяет тайм-аут сессии только для авторизованных пользователей"""
    # Разрешаем доступ к публичным страницам без проверки
    public_paths = [
        '/', 
        '/contacts', 
        '/knowledge-base', 
        '/politika', 
        '/applecheck', 
        '/androidcheck',
        '/compare'
    ]
    if request.path in public_paths:
        return
    
    last_activity = session.get('last_activity')
    if last_activity:
        try:
            last_active = datetime.fromisoformat(last_activity)
            if (datetime.utcnow() - last_active).total_seconds() > 3600:  # 1 час
                session.clear()
                flash('Your session has expired due to inactivity', 'warning')
                return redirect(url_for('auth.login'))
        except:
            session['last_activity'] = datetime.utcnow().isoformat()
    
    session['last_activity'] = datetime.utcnow().isoformat()

@app.before_request
def check_session_integrity():
    """Проверяет целостность сессии администратора"""
    if 'admin_id' in session:
        try:
            admin = admin_users_collection.find_one(
                {'_id': ObjectId(session['admin_id'])},
                projection={'role': 1}
            )
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
# Celery задачи
# ======================================

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def background_check_task(self, imei, service_type, session_id):
    """Выполняет проверку в фоновом режиме и обновляет запись в базе"""
    from ifreeapi import perform_api_check
    from datetime import datetime
    from pymongo import MongoClient
    import os
    import logging
    
    # Настройка логгера для задачи
    logger = logging.getLogger(f'celery.task.{self.name}')
    logger.setLevel(logging.INFO)
    
    try:
        logger.info(f"Starting background check for session: {session_id}")
        
        # Создаем новое подключение к MongoDB
        mongo_uri = os.getenv('MONGODB_URI')
        client = MongoClient(mongo_uri)
        db = client['imei_checker']
        checks_collection = db['results']
        
        # Выполняем проверку
        result = perform_api_check(imei, service_type)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown API error')
            logger.error(f"API check failed: {error_msg}")
            raise Exception(f"API error: {error_msg}")
        
        update_data = {
            'result': result,
            'status': 'completed',
            'completed_at': datetime.utcnow()
        }
        
        # Обновляем запись в базе
        update_result = checks_collection.update_one(
            {'session_id': session_id},
            {'$set': update_data}
        )
        
        if update_result.matched_count == 0:
            update_result = checks_collection.update_one(
                {'stripe_session_id': session_id},
                {'$set': update_data}
            )
            if update_result.matched_count == 0:
                logger.error(f"Record not found for session: {session_id}")
                raise Exception("Database record not found")
        
        logger.info(f"Background check completed for session: {session_id}")
        return True
    
    except Exception as exc:
        logger.exception(f"Background check failed: {str(exc)}")
        
        # Фиксация ошибки в базе данных
        error_data = {
            'result': {
                'success': False,
                'error': f"Background processing error: {str(exc)}",
                'error_type': 'internal_error',
                'status': 'Error'
            },
            'status': 'failed',
            'completed_at': datetime.utcnow(),
            'retry_count': self.request.retries
        }
        
        try:
            if 'checks_collection' in locals():
                checks_collection.update_one(
                    {'$or': [
                        {'session_id': session_id},
                        {'stripe_session_id': session_id}
                    ]},
                    {'$set': error_data}
                )
        except Exception as e:
            logger.error(f"Failed to update error status in database: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        else:
            logger.error("Task failed after all retries")
            return False
    
    finally:
        # Всегда закрываем подключение к БД
        if 'client' in locals() and client:
            client.close()

# ======================================
# Основные маршруты приложения
# ======================================
@app.route('/')
@cache.cached(timeout=300, unless=lambda: 'user_id' in session or 'admin_id' in session)
def index():
    logger.info("Home page access")
    prices = get_current_prices()
    
    # Добавляем получение карусельных слайдов
    carousel_slides = list(db.carousel_slides.find().sort("order", 1))
    
    # Проверяем авторизацию пользователя
    user_authenticated = 'user_id' in session or 'admin_id' in session
    
    return render_template(
        'index.html',
        stripe_public_key=STRIPE_PUBLIC_KEY,
        carousel_slides=carousel_slides,
        prices=prices,
        user_authenticated=user_authenticated
    )
    
@app.route('/contacts')
@cache.cached(timeout=3600)
def contacts_page():
    """Страница контактов"""
    logger.info("Contacts page access")
    return render_common_template('contacts.html')

@app.route('/knowledge-base')
@cache.cached(timeout=3600)
def knowledge_base():
    """База знаний"""
    logger.info("Knowledge base access")
    return render_common_template('knowledge-base.html')

@app.route('/politika')
@cache.cached(timeout=3600)
def policy_page():
    """Страница политики конфиденциальности"""
    logger.info("Policy page access")
    return render_common_template('politika.html')

# ======================================
# Роут для страницы проверки Apple IMEI
# ======================================

@app.route('/applecheck')
def apple_check():
    logger.info("Apple check page access")
    service_type = request.args.get('type', 'free')
    service_prices = get_apple_services_data()

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
    service_prices = get_android_services_data()

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

    # Определяем базовый тип сервиса для выделения карточки
    base_service_type = service_type.split('_')[0] if '_' in service_type else service_type

    return render_common_template(
        'androidcheck.html',
        service_type=service_type,
        base_service_type=base_service_type,
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
        
        amount = get_service_price(service_type)
        
        # Проверка корректности суммы
        if not isinstance(amount, int) or amount <= 0:
            logger.error(f"Invalid amount for service {service_type}: {amount}")
            return jsonify({
                'error': 'Invalid service price configuration',
                'details': f'Service: {service_type}, Amount: {amount}'
            }), 500
        
        if service_type == 'free':
            logger.debug("Free service - no checkout needed")
            return jsonify({'error': 'უფასო შემოწმება არ საჭიროებს გადახდამ'}), 400
        
        if use_balance and 'user_id' in session:
            user_id = session['user_id']
            amount_gel = amount / 100.0
            
            idempotency_key = f"bal_{user_id}_{imei}_{datetime.utcnow().timestamp()}"
            
            if stripe_payment.deduct_balance(
                user_id=user_id,
                amount=amount_gel,
                service_type=service_type,
                imei=imei,
                idempotency_key=idempotency_key
            ):
                record = {
                    'session_id': idempotency_key,
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
                    'status': 'pending_verification'
            }
                if client:
                    checks_collection.insert_one(record)
                    logger.info(f"Balance payment recorded for IMEI: {imei}")
                
                # Запуск фоновой задачи через Celery
                background_check_task.delay(imei, service_type, idempotency_key)
                
                return jsonify({
                    'id': idempotency_key,
                    'payment_method': 'balance'
                })
            else:
                logger.warning(f"Balance deduction failed for user: {user_id}")
                return jsonify({'error': 'ბალანსიდან გადახდა ვერ მოხერხდა'}), 500
        
        base_url = request.host_url.rstrip('/')
        success_url = f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}&imei={imei}&service_type={service_type}"
        
        if service_type in ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']:
            cancel_url = f"{base_url}/applecheck?type={service_type}"
        else:
            cancel_url = f"{base_url}/androidcheck?type={service_type}"
        
        metadata = {
            'imei': imei,
            'service_type': service_type,
            'idempotency_key': idempotency_key
        }
        if 'user_id' in session:
            metadata['user_id'] = session['user_id']
        
        stripe_session = stripe_payment.create_checkout_session(
            imei=imei,
            service_type=service_type,
            amount=amount,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            idempotency_key=idempotency_key
        )
        
        # Проверка ответа Stripe
        if not stripe_session or not hasattr(stripe_session, 'id'):
            logger.error("Stripe session creation failed: empty response")
            return jsonify({
                'error': 'Stripe session creation failed',
                'details': 'Empty response from Stripe API'
            }), 500
            
        logger.info(f"Stripe session created successfully: {stripe_session.id}")
        return jsonify({
            'id': stripe_session.id,
            'payment_method': 'stripe'
        })
    
    except Exception as e:
        logger.exception(f"Error creating checkout session: {str(e)}")
        return jsonify({
            'error': 'გადახდის შეცდომა',
            'details': str(e),
            'error_type': 'server_error'
        }), 500

@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    imei = request.args.get('imei')
    service_type = request.args.get('service_type')
    
    logger.info(f"Payment success: session_id={session_id}, imei={imei}, service={service_type}")
    
    if not session_id or not imei or not service_type:
        logger.warning("Missing parameters in payment success")
        return render_template('error.html', error="არასაკმარისი პარამეტრები"), 400
    
    if session_id.startswith('bal_'):
        apple_services = ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']
        if service_type in apple_services:
            return redirect(url_for('apple_check', type=service_type, imei=imei, session_id=session_id))
        else:
            return redirect(url_for('android_check', type=service_type, imei=imei, session_id=session_id))
    else:
        try:
            # Проверка статуса платежа в Stripe
            stripe_session = stripe.checkout.Session.retrieve(session_id)
            
            if stripe_session.payment_status != 'paid':
                logger.error(f"Unpaid Stripe session: {session_id}")
                return render_template('error.html', 
                    error=f"გადახდა არ დასრულებულა სესიისთვის: {session_id}"), 402
            
            record = {
                'session_id': session_id,
                'stripe_session_id': session_id,
                'imei': imei,
                'service_type': service_type,
                'paid': True,
                'payment_status': stripe_session.payment_status,
                'amount': stripe_session.amount_total / 100,
                'currency': stripe_session.currency,
                'timestamp': datetime.utcnow(),
                'status': 'pending_verification'
            }
            if 'user_id' in session:
                record['user_id'] = ObjectId(session['user_id'])
            if client:
                checks_collection.insert_one(record)
                logger.info(f"Payment recorded: {session_id}")
            
            # Запуск фоновой задачи через Celery
            background_check_task.delay(imei, service_type, session_id)
            
            apple_services = ['fmi', 'blacklist', 'sim_lock', 'activation', 'carrier', 'mdm']
            if service_type in apple_services:
                return redirect(url_for('apple_check', type=service_type, imei=imei, session_id=session_id))
            else:
                return redirect(url_for('android_check', type=service_type, imei=imei, session_id=session_id))
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in /success: {e.user_message}")
            return render_template('error.html', 
                error=f"Stripe შეცდომა: {e.user_message}"), 500
        except Exception as e:
            logger.exception(f"Payment success processing failed: {str(e)}")
            return render_template('error.html', 
                error="სისტემური შეცდომა"), 500

@app.route('/get_check_result')
@csrf.exempt
def get_check_result():
    session_id = request.args.get('session_id')
    logger.info(f"Check result request: {session_id}")
    if not session_id:
        logger.warning("Missing session_id in check result request")
        return jsonify({'error': 'სესიის ID არის მითითებული'}), 400
    
    try:
        record = checks_collection.find_one({
            '$or': [
                {'session_id': session_id},
                {'stripe_session_id': session_id}
            ]
        })
        if not record:
            logger.warning(f"Check result not found: {session_id}")
            return jsonify({'error': 'შედეგი ვერ მოიძებნა'}), 404
        
        response_data = {
            'imei': record.get('imei'),
            'service_type': record.get('service_type'),
            'status': record.get('status', 'pending'),
            'timestamp': record.get('timestamp'),
            'completed_at': record.get('completed_at')
        }
        
        if 'result' in record:
            response_data['result'] = record['result']
        
        return jsonify(response_data)
    
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}")
        return jsonify({
            'error': 'მონაცემთა ბაზა დროებით მიუწვდომელია',
            'details': str(e)
        }), 503
    except Exception as e:
        logger.exception(f"Error retrieving check result: {str(e)}")
        return jsonify({
            'error': 'შეცდომა მონაცემების მოძიებაში',
            'details': str(e)
        }), 500

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
        
        result = perform_api_check(imei, service_type)
        
        if client:
            record = {
                'imei': imei,
                'service_type': service_type,
                'timestamp': datetime.utcnow(),
                'result': result,
                'status': 'completed' if result.get('success') else 'failed'
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
        user = regular_users_collection.find_one(
            {'_id': ObjectId(user_id)},
            projection={'balance': 1}
        )
        if not user:
            logger.warning(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404

        balance = user.get('balance', 0)
        return jsonify({'balance': balance})
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
# Роут для сравнения телефонов
# ======================================

@app.route('/compare')
@cache.cached(timeout=3600)
def compare_phones():
    """Страница сравнения характеристик телефонов"""
    logger.info("Phone comparison page accessed")
    return render_template('compare.html')

@app.route('/api/search_phones')
def search_phones():
    """API для поиска телефонов в базе"""
    query = request.args.get('query', '').lower().strip()
    
    if not query:
        return jsonify([])
    
    try:
        # Поиск по бренду и модели
        regex = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)
        results = list(phonebase_collection.find({
            "$or": [
                {"Бренд": regex},
                {"Модель": regex}
            ]
        }).limit(10))
        
        # Преобразование ObjectId в строки
        for phone in results:
            phone['_id'] = str(phone['_id'])
            
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Phone search error: {str(e)}")
        return jsonify([])

# ======================================
# Webhook Manager
# ======================================

def send_webhook_event(event_type, payload):
    if not client:
        logger.warning("Database unavailable for webhook")
        return
        
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

# Регистрация блюпринтов
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

# Установка CSRF-куки
@app.after_request
def set_csrf_cookie(response):
    if not request.path.startswith(('/static', '/api')):
        secure = False
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
    logger.error(f"CSRF Validation Error: {e.description}")
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
    logger.exception(f"Unexpected error: {str(e)}")
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
    
    # Проверка Celery
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        active_tasks = inspect.active()
        if active_tasks is not None:
            status['services']['celery'] = 'OK'
        else:
            status['services']['celery'] = 'ERROR: No response from workers'
            status['status'] = 'ERROR'
    except Exception as e:
        status['services']['celery'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    return jsonify(status), 200 if status['status'] == 'OK' else 500

# Создание индексов при запуске
def create_indexes():
    if client:
        try:
            checks_collection.create_index([("session_id", 1)])
            checks_collection.create_index([("stripe_session_id", 1)])
            checks_collection.create_index([("user_id", 1)])
            checks_collection.create_index([("timestamp", -1)])
            phonebase_collection.create_index([("Бренд", "text"), ("Модель", "text")])
            logger.info("Database indexes created")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")

if __name__ == '__main__':
    # Создание индексов
    create_indexes()
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting application on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_ENV') != 'production'
                )
