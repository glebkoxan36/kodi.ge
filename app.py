import os
import json
import logging
import re
import hmac
import secrets
import hashlib
import requests
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, current_app
from flask_cors import CORS
from pymongo import MongoClient
import stripe
from functools import wraps
from bs4 import BeautifulSoup
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint

# Импорт функций из нового модуля API
from ifreeapi import validate_imei, perform_api_check, SERVICE_TYPES
from stripepay import StripePayment  # Импорт класса для работы со Stripe

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

# MongoDB
client = MongoClient(MONGODB_URI)
db = client['imei_checker']
checks_collection = db['results']
prices_collection = db['prices']
comparisons_collection = db['comparisons']
phones_collection = db['phones']  # ИЗМЕНЕНО: phones1 -> phones
parser_logs_collection = db['parser_logs']
admin_users_collection = db['admin_users']
regular_users_collection = db['users']
audit_logs_collection = db['audit_logs']
api_keys_collection = db['api_keys']
webhooks_collection = db['webhooks']
payments_collection = db['payments']
failed_logins_collection = db['failed_logins']

# Создаем индекс для поля Name
if 'name_index' not in phones_collection.index_information():
    phones_collection.create_index('Name', name='name_index')
    app.logger.info("Created index on Name field")

# Создаем администратора по умолчанию
if not admin_users_collection.find_one({'username': 'admin'}):
    admin_password = os.getenv('ADMIN_PASSWORD', 'securepassword')
    admin_users_collection.insert_one({
        'username': 'admin',
        'password': generate_password_hash(admin_password),
        'role': 'superadmin',
        'created_at': datetime.utcnow()
    })

DEFAULT_PRICES = {
    'paid': 499,
    'premium': 999,
    'fmi': 299,
    'sim_lock': 199,
    'blacklist': 199,
    'activation': 199,
    'carrier': 199,
    'full': 999,
    'macbook': 349,
    'mdm': 199,  # Добавлена цена для MDM
    # Android-specific prices
    'android_paid': 399,
    'android_premium': 799,
    'google_account': 299,
    'frp_lock': 199,
    'android_full': 799
}

if prices_collection.count_documents({'type': 'current'}) == 0:
    prices_collection.insert_one({
        'type': 'current',
        'prices': DEFAULT_PRICES,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    })

def get_current_prices():
    price_doc = prices_collection.find_one({'type': 'current'})
    if price_doc:
        # Объединяем с DEFAULT_PRICES для поддержки новых сервисов
        return {**DEFAULT_PRICES, **price_doc['prices']}
    return DEFAULT_PRICES

# Инициализация StripePayment
stripe_payment = StripePayment(
    stripe_api_key=stripe.api_key,
    webhook_secret=STRIPE_WEBHOOK_SECRET,
    users_collection=regular_users_collection,
    payments_collection=payments_collection
)

# ======================================
# Оптимизированные функции поиска телефонов
# ======================================

def search_phones(query):
    """Поиск телефонов по Name с использованием индекса"""
    try:
        if not query:
            return []
        
        app.logger.info(f"Searching phones for: {query}")
        
        # Используем индекс для поиска по Name
        regex = re.compile(re.escape(query), re.IGNORECASE)
        results = list(phones_collection.find({
            'Name': regex
        }).limit(10))
        
        normalized = []
        for phone in results:
            normalized.append({
                '_id': str(phone['_id']),
                'name': phone.get('Name', 'Unknown Phone'),
                'image_url': PLACEHOLDER,
            })
        
        app.logger.info(f"Found {len(normalized)} results")
        return normalized
    
    except Exception as e:
        app.logger.error(f"Phone search error: {str(e)}")
        return []

def get_phone_details(phone_id):
    """Получение детальной информации о телефоне"""
    try:
        phone = phones_collection.find_one({'_id': ObjectId(phone_id)})
        if not phone:
            return None
        
        name = phone.get('Name', 'Unknown Phone')
        
        specs = {}
        for key, value in phone.items():
            if key not in ['_id', 'Name']:
                if isinstance(value, ObjectId):
                    value = str(value)
                elif isinstance(value, list):
                    value = ', '.join(map(str, value))
                elif isinstance(value, float) and value.is_integer():
                    value = int(value)
                
                specs[key] = value
        
        return {
            '_id': str(phone['_id']),
            'name': name,
            'image_url': PLACEHOLDER,
            'specs': specs
        }
    
    except Exception as e:
        app.logger.error(f"Details error: {str(e)}")
        return None

def perform_ai_comparison(phone1, phone2):
    """Выполнение AI-сравнения двух телефонов с использованием Google Gemini"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Инициализация модели Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        phone1_name = phone1.get('name', 'Unknown Phone 1')
        phone2_name = phone2.get('name', 'Unknown Phone 2')
        
        # Формируем промпт для Gemini
        prompt = f"""
            შედარება: {phone1_name} vs {phone2_name}
            
            გთხოვთ შეადაროთ შემდეგი კატეგორიები:
            - პროდუქტიულობა
            - ეკრანის ხარისხი
            - კამერა
            - ბატარეის ხანგრძლივობა
            - დიზაინი
            - ფასი და ღირებულება
            
            გთხოვთ მოგვაწოდოთ დეტალური ანალიზი ქართულ ენაზე.
        """
        
        # Генерация контента
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000
            )
        )
        
        content = response.text
        
        # Сохраняем результат сравнения
        if comparisons_collection is not None:
            try:
                comparisons_collection.insert_one({
                    'phone1': phone1_name,
                    'phone2': phone2_name,
                    'timestamp': datetime.utcnow(),
                    'ai_response': content
                })
            except Exception as e:
                app.logger.error(f"Failed to save comparison: {str(e)}")
        
        return content
    
    except Exception as e:
        app.logger.error(f"Gemini API error: {str(e)}")
        return "AI service unavailable"

# ======================================
# Аудит и логирование
# ======================================

def log_audit_event(action, details, user_id=None, username=None):
    """Логирование действий администратора"""
    event = {
        'action': action,
        'details': details,
        'user_id': user_id,
        'username': username,
        'timestamp': datetime.utcnow(),
        'ip_address': request.remote_addr
    }
    audit_logs_collection.insert_one(event)

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

# Новые маршруты для страниц контактов и базы знаний
@app.route('/contacts')
def contacts_page():
    """Страница контактов"""
    user_data = None
    if 'user_id' in session:
        user_id = session['user_id']
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
# Роуты для страницы проверки Apple IMEI (переименованы в applecheck1)
# ======================================

# Отдельные роуты для каждого типа проверки
@app.route('/applecheck1/originality')
def apple_check_originality():
    return apple_check('originality')

@app.route('/applecheck1/fmi')
def apple_check_fmi():
    return apple_check('fmi')

@app.route('/applecheck1/sim_lock')
def apple_check_sim_lock():
    return apple_check('sim_lock')

@app.route('/applecheck1/blacklist')
def apple_check_blacklist():
    return apple_check('blacklist')

@app.route('/applecheck1/mdm')
def apple_check_mdm():
    return apple_check('mdm')

@app.route('/applecheck1/premium')
def apple_check_premium():
    return apple_check('premium')

@app.route('/applecheck1/macbook')
def apple_check_macbook():
    return apple_check('macbook')

# Общий роут для Apple проверки
@app.route('/applecheck1')
@app.route('/applecheck1/<service>')
def apple_check(service=None):
    service = request.args.get('service', service)
    
    # Установка значения по умолчанию, если service не указан
    if not service:
        service = 'originality'
    
    # Получаем текущие цены и конвертируем в доллары
    prices = get_current_prices()
    user_balance = 0.0
    user_data = None
    
    if 'user_id' in session:
        user_id = session['user_id']
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if user:
            user_balance = user.get('balance', 0.0)
            avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
            user_data = {
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'avatar_color': avatar_color
            }

    return render_template(
        'applecheck.html',
        selected_service=service,
        fmi_price=prices['fmi'] / 100.0,
        sim_lock_price=prices['sim_lock'] / 100.0,
        blacklist_price=prices['blacklist'] / 100.0,
        mdm_price=prices.get('mdm', 199) / 100.0,  # Значение по умолчанию
        premium_price=prices['premium'] / 100.0,
        macbook_price=prices.get('macbook', 349) / 100.0,
        stripe_public_key=STRIPE_PUBLIC_KEY,
        user=user_data,
        user_balance=user_balance
    )

# ======================================
# Роут для страницы проверки Android IMEI
# ======================================

@app.route('/androidcheck')
def android_check():
    """Страница проверки Android-устройств"""
    # Определяем тип услуги из параметра URL
    service_type = request.args.get('type', 'free')
    if service_type not in ['free', 'paid', 'premium']:
        service_type = 'free'

    # Получаем текущие цены для Android-услуг
    prices = get_current_prices()
    paid_price = prices.get('android_paid', 399) / 100.0
    premium_price = prices.get('android_premium', 799) / 100.0
    google_account_price = prices.get('google_account', 299) / 100.0
    frp_lock_price = prices.get('frp_lock', 199) / 100.0
    blacklist_price = prices.get('blacklist', 199) / 100.0
    carrier_price = prices.get('carrier', 199) / 100.0
    full_price = prices.get('android_full', 799) / 100.0

    # Данные пользователя (если авторизован)
    user_data = None
    user_balance = 0.0
    if 'user_id' in session:
        user_id = session['user_id']
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if user:
            avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
            user_data = {
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'balance': user.get('balance', 0.0),
                'avatar_color': avatar_color
            }
            user_balance = user.get('balance', 0.0)

    return render_template(
        'androidcheck.html',
        service_type=service_type,
        paid_price=paid_price,
        premium_price=premium_price,
        google_account_price=google_account_price,
        frp_lock_price=frp_lock_price,
        blacklist_price=blacklist_price,
        carrier_price=carrier_price,
        full_price=full_price,
        stripe_public_key=STRIPE_PUBLIC_KEY,
        user=user_data,
        user_balance=user_balance
    )

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        imei = data.get('imei')
        service_type = data.get('service_type')
        
        if not validate_imei(imei):
            return jsonify({'error': 'Invalid IMEI'}), 400
        
        prices = get_current_prices()
        
        # Создаем сессию оплаты через StripePayment
        session = stripe_payment.create_checkout_session(
            imei=imei,
            service_type=service_type,
            amount=prices[service_type],
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('index', _external=True)
        )
        
        return jsonify({'id': session.id})
    
    except Exception as e:
        app.logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        return render_template('error.html', error="Session ID missing"), 400
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        imei = session.metadata.get('imei')
        service_type = session.metadata.get('service_type')
        
        if not imei or not service_type:
            return render_template('error.html', error="Invalid session data"), 400
        
        result = perform_api_check(imei, service_type)
        
        if not result or 'error' in result:
            error_msg = result.get('error', 'No data available for this IMEI')
            return render_template('error.html', error=error_msg)
        
        # Для сервисов, возвращающих HTML
        if 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            if parsed_data:
                result = parsed_data
            else:
                result = {'error': 'Failed to parse HTML response'}
        
        record = {
            'stripe_session_id': session_id,
            'imei': imei,
            'service_type': service_type,
            'paid': True,
            'payment_status': session.payment_status,
            'amount': session.amount_total / 100,
            'currency': session.currency,
            'timestamp': datetime.utcnow(),
            'result': result
        }
        if 'user_id' in session:
            record['user_id'] = ObjectId(session['user_id'])
        checks_collection.insert_one(record)
        
        return redirect(url_for('index', session_id=session_id))
    
    except Exception as e:
        app.logger.error(f"Payment success error: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/get_check_result')
def get_check_result():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    
    record = checks_collection.find_one({'stripe_session_id': session_id})
    if not record:
        return jsonify({'error': 'Result not found'}), 404
    
    return jsonify({
        'imei': record['imei'],
        'result': record['result']
    })

@app.route('/check_with_balance', methods=['POST'])
@login_required
def check_with_balance():
    """Выполнение проверки с использованием баланса пользователя"""
    data = request.get_json()
    imei = data.get('imei')
    service_type = data.get('service_type')
    
    if not imei or not service_type:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # Получаем текущие цены
    prices = get_current_prices()
    
    # Проверяем, есть ли цена для данного типа услуги
    if service_type not in prices:
        return jsonify({'error': f'Invalid service type: {service_type}'}), 400
    
    # Получаем цену услуги в долларах
    service_price = prices[service_type] / 100.0
    
    # Получаем данные пользователя
    user_id = session['user_id']
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Проверяем баланс пользователя
    user_balance = user.get('balance', 0.0)
    if user_balance < service_price:
        return jsonify({'error': 'Insufficient balance'}), 402
    
    try:
        # Выполняем проверку
        result = perform_api_check(imei, service_type)
        
        if not result:
            return jsonify({'error': 'Empty response from API'}), 500
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Для сервисов, возвращающих HTML
        if 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            if parsed_data:
                result = parsed_data
            else:
                result = {'error': 'Failed to parse HTML response'}
        
        # Создаем запись о проверке
        record = {
            'imei': imei,
            'service_type': service_type,
            'paid': True,
            'payment_type': 'balance',
            'amount': service_price,
            'currency': 'USD',
            'timestamp': datetime.utcnow(),
            'result': result,
            'user_id': ObjectId(user_id)
        }
        checks_collection.insert_one(record)
        
        # Списание средств с баланса
        new_balance = user_balance - service_price
        regular_users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'balance': new_balance}}
        )
        
        # Запись о платеже
        payments_collection.insert_one({
            'user_id': ObjectId(user_id),
            'amount': -service_price,
            'currency': 'USD',
            'timestamp': datetime.utcnow(),
            'type': 'check',
            'service_type': service_type,
            'imei': imei
        })
        
        return jsonify({
            'success': True,
            'result': result,
            'new_balance': new_balance
        })
    
    except Exception as e:
        app.logger.error(f'Check with balance error: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/get_user_balance', methods=['GET'])
@login_required
def get_user_balance():
    """Получение баланса пользователя"""
    user_id = session['user_id']
    user = regular_users_collection.find_one(
        {'_id': ObjectId(user_id)},
        {'balance': 1}
    )
    
    if user:
        return jsonify({'balance': user.get('balance', 0.0)})
    return jsonify({'balance': 0.0})

@app.route('/perform_check', methods=['POST'])
def perform_check():
    data = request.get_json()
    imei = data.get('imei', '').strip()
    service_type = data.get('service_type', 'free')
    
    if not imei or not service_type:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # Для MacBook разрешаем 12-18 символов
    is_macbook = service_type in ['macbook', 'macbook_pro', 'macbook_air']
    if not validate_imei(imei, allow_macbook=is_macbook):
        return jsonify({'error': 'Invalid IMEI format'}), 400
    
    try:
        result = perform_api_check(imei, service_type)
        
        if not result:
            return jsonify({'error': 'Empty response from API'}), 500
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Для сервисов, возвращающих HTML
        if 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            if parsed_data:
                result = parsed_data
            else:
                result = {'error': 'Failed to parse HTML response'}
        
        if service_type == 'free':
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
        
        if result and 'error' not in result:
            send_webhook_event('imei_check_completed', {
                'imei': imei,
                'service_type': service_type,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f'Check error: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

def parse_free_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {}
        
        # Парсинг табличных данных
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(':', '').replace(' ', '_').lower()
                    value = cols[1].get_text(strip=True)
                    result[key] = value
        
        # Дополнительные поля для новых сервисов
        labels = [
            "Device", "Model", "Serial", "IMEI", "ICCID", 
            "FMI", "Activation Status", "Blacklist Status",
            "Sim Lock", "MDM Status", "Google Account Status",
            "Carrier", "Purchase Date", "Warranty Status"
        ]
        
        for label in labels:
            element = soup.find(string=re.compile(rf'{label}.*', re.IGNORECASE))
            if not element:
                continue
                
            value_element = None
            if element.parent and element.parent.find_next_sibling():
                value_element = element.parent.find_next_sibling()
            if not value_element and element.parent and element.parent.find('br'):
                value_element = element.parent
            if not value_element and ':' in element:
                value_element = element.split(':', 1)[-1].strip()
            
            if value_element:
                if isinstance(value_element, str):
                    value = value_element
                else:
                    value = value_element.get_text(strip=True)
                value = re.sub(r'[^a-zA-Z0-9\s]', '', value).strip()
                if value:
                    result[label.replace(" ", "_").lower()] = value
        
        return result
    
    except Exception as e:
        app.logger.error(f"HTML parsing error: {str(e)}")
        app.logger.error(f"HTML content: {html_content[:500]}")
        return None

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    """Обработка вебхуков от Stripe"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Обработка вебхука через StripePayment
        stripe_payment.handle_webhook(payload, sig_header)
        return jsonify({'status': 'success'})
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400

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
    
    try:
        db.command('ping')
        status['services']['mongodb'] = 'OK'
    except Exception as e:
        status['services']['mongodb'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    try:
        stripe.Balance.retrieve()
        status['services']['stripe'] = 'OK'
    except Exception as e:
        status['services']['stripe'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    try:
        response = requests.get(API_URL, timeout=5)
        status['services']['external_api'] = 'OK' if response.status_code == 200 else f'HTTP {response.status_code}'
    except Exception as e:
        status['services']['external_api'] = f'ERROR: {str(e)}'
        status['status'] = 'ERROR'
    
    try:
        # Проверка Gemini API
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
        return jsonify({'success': False, 'error': 'No file part'}), 400
    
    file = request.files['carouselImage']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    
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
# Сравнение телефонов (маршруты)
# ======================================

@app.route('/api/search', methods=['GET'])
def api_search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    results = search_phones(query)
    return jsonify(results)

@app.route('/api/phone_details/<phone_id>', methods=['GET'])
def api_phone_details(phone_id):
    phone = get_phone_details(phone_id)
    if not phone:
        return jsonify({'error': 'Phone not found'}), 404
    return jsonify(phone)

@app.route('/api/ai-analysis', methods=['POST'])
def api_ai_analysis():
    data = request.json
    phone1 = data.get('phone1')
    phone2 = data.get('phone2')
    
    if not phone1 or not phone2:
        return jsonify({'error': 'Both phones are required'}), 400
    
    analysis = perform_ai_comparison(phone1, phone2)
    return jsonify({'analysis': analysis})

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
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('User not found', 'danger')
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
            flash('Minimum topup amount is $1', 'danger')
            return redirect(url_for('user.topup_balance'))
        
        # Создаем платежную сессию Stripe
        try:
            session = stripe_payment.create_topup_session(
                user_id=session['user_id'],
                amount=amount,
                success_url=url_for('user.topup_success', _external=True),
                cancel_url=url_for('user.topup_balance', _external=True)
            )
            return redirect(session.url)
        except Exception as e:
            flash(f'Error creating payment session: {str(e)}', 'danger')
            return redirect(url_for('user.topup_balance'))
    
    return render_template('user/topup.html', stripe_public_key=STRIPE_PUBLIC_KEY)

@user_bp.route('/topup/success')
@login_required
def topup_success():
    """Успешное пополнение баланса"""
    flash('Payment successful! Your balance will be updated shortly.', 'success')
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
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    checks = list(checks_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).skip((page - 1) * per_page).limit(per_page))
    
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
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    comparisons = list(comparisons_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).skip((page - 1) * per_page).limit(per_page))
    
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
        errors.append("Имя должно содержать только грузинские буквы")
    
    if not GEORGIAN_LETTERS_REGEX.match(last_name):
        errors.append("Фамилия должна содержать только грузинские буквы")
    
    try:
        birth_date = datetime(int(birth_year), int(birth_month), int(birth_day))
        if birth_date > datetime.utcnow():
            errors.append("Дата рождения не может быть в будущем")
    except (ValueError, TypeError):
        errors.append("Некорректная дата рождения")
    
    if not PHONE_REGEX.match(phone):
        errors.append("Некорректный формат телефона. Используйте +995XXXXXXXXX")
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors.append("Некорректный email адрес")
    
    if not PASSWORD_REGEX.match(password):
        errors.append("Пароль должен содержать минимум 12 символов, одну заглавную букву, одну строчную, одну цифру и один спецсимвол")
    
    if password != confirm_password:
        errors.append("Пароли не совпадают")
    
    if regular_users_collection.find_one({'$or': [{'username': username}, {'email': email}, {'phone': phone}]}):
        errors.append("Пользователь с такими данными уже существует")
    
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
    
    result = regular_users_collection.insert_one(user_data)
    app.logger.info(f"Registered new user: {username}")
    
    session['user_id'] = str(result.inserted_id)
    session['username'] = username
    session['role'] = 'user'
    
    return jsonify({"success": True, "message": "Регистрация успешна!"}), 201

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
    failed_login = failed_logins_collection.find_one({'ip': ip_address})
    
    if failed_login and failed_login.get('blocked_until') and datetime.utcnow() < failed_login['blocked_until']:
        remaining = int((failed_login['blocked_until'] - datetime.utcnow()).total_seconds() / 60)
        return jsonify({
            "success": False,
            "error": f"Аккаунт временно заблокирован. Попробуйте через {remaining} минут"
        }), 429
    
    user = None
    is_admin = False
    
    identifier_lower = identifier.lower()
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

    if user and check_password_hash(user['password'], password):
        if failed_login:
            failed_logins_collection.delete_one({'ip': ip_address})
        
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
        failed_logins_collection.update_one(
            {'ip': ip_address},
            {'$set': {'blocked_until': blocked_until}}
        )
        app.logger.warning(f"IP blocked: {ip_address} for 10 minutes")
        return jsonify({
            "success": False,
            "error": "Слишком много попыток. Аккаунт заблокирован на 10 минут"
        }), 429
    
    app.logger.warning(f"Failed login attempt for: {identifier} from IP: {ip_address}")
    return jsonify({"success": False, "error": "Неверный логин или пароль"}), 401

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

# ======================================
# Регистрация блюпринтов
# ======================================

# Импорт и регистрация admin_bp
from admin_routes import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(user_bp)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
