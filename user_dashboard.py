# user_dashboard.py
import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
from functools import wraps
import stripe
from stripepay import StripePayment
from datetime import datetime

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля"""
    handler = logging.FileHandler('logs/user_dashboard.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

# Инициализация Blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

# Проверка наличия ключей Stripe
stripe_api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

if not stripe_api_key or not STRIPE_PUBLIC_KEY:
    logger.critical("Stripe API keys are missing in environment variables")
    raise ValueError("Stripe API keys are missing in environment variables")

stripe.api_key = stripe_api_key

# Подключение к MongoDB
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
logger.info(f"Connecting to MongoDB: {mongodb_uri}")
client = MongoClient(mongodb_uri)
db = client['imei_checker']
regular_users_collection = db['users']
checks_collection = db['results']
payments_collection = db['payments']
refunds_collection = db['refunds']

# Инициализация платежного модуля
stripe_payment = StripePayment(
    stripe_api_key=stripe_api_key,
    webhook_secret=STRIPE_WEBHOOK_SECRET,
    users_collection=regular_users_collection,
    payments_collection=payments_collection,
    refunds_collection=refunds_collection
)

# Декоратор для проверки аутентификации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'user':
            logger.warning("Unauthorized access attempt to protected route")
            flash('გთხოვთ შეხვიდეთ სისტემაში', 'danger')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Middleware для загрузки текущего пользователя
@user_bp.before_request
@login_required
def load_user():
    try:
        # Исправление: преобразование строки в ObjectId
        user_id_str = session['user_id']
        g.user = regular_users_collection.find_one({'_id': ObjectId(user_id_str)})
        
        if not g.user:
            logger.warning(f"User not found: {user_id_str}")
            flash('მომხმარებელი ვერ მოიძებნა', 'danger')
            return redirect(url_for('auth.login'))
            
    except (InvalidId, TypeError) as e:
        logger.error(f"Invalid user ID in session: {str(e)}")
        session.clear()
        flash('არასწორი სესია', 'danger')
        return redirect(url_for('auth.login'))
    
    return None

# Функция для генерации цвета аватара
def generate_avatar_color(name):
    colors = [
        '#00c6ff', '#ff3d71', '#00d68f', '#ffaa00', 
        '#8c7ae6', '#0097e6', '#e1b12c', '#44bd32'
    ]
    if not name:
        return colors[0]
    char_code = ord(name[0].lower())
    return colors[char_code % len(colors)]

# Роуты для страниц
@user_bp.route('/dashboard')
@login_required
def dashboard():
    logger.info(f"Dashboard access for user: {g.user['_id']}")
    # Проверка наличия пользователя
    if not hasattr(g, 'user') or not g.user:
        logger.warning("User not loaded in dashboard")
        return redirect(url_for('auth.login'))
    
    user = g.user
    user_id = user['_id']  # Используем ObjectId из g.user
    
    balance = user.get('balance', 0.0)
    
    # Получаем последние проверки
    checks = list(checks_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    # Получаем последние платежи
    payments = list(payments_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    # Считаем общее количество проверок
    total_checks = checks_collection.count_documents({'user_id': user_id})
    
    # Генерируем цвет аватара
    avatar_color = generate_avatar_color(f"{user.get('first_name', '')} {user.get('last_name', '')}")
    
    # Форматируем даты для шаблона
    for check in checks:
        check['formatted_timestamp'] = check['timestamp'].strftime('%d.%m.%Y %H:%M')
    
    for payment in payments:
        payment['formatted_timestamp'] = payment['timestamp'].strftime('%d.%m.%Y %H:%M')
    
    logger.debug(f"Dashboard data loaded for user: {user['email']}")
    return render_template(
        'user/dashboard.html',  # Исправленный путь
        user=user,
        balance=balance,
        last_checks=checks,
        last_payments=payments,
        total_checks=total_checks,
        avatar_color=avatar_color,
        stripe_public_key=STRIPE_PUBLIC_KEY
    )

@user_bp.route('/settings')
@login_required
def settings():
    logger.info(f"Settings access for user: {g.user['_id']}")
    user = g.user
    return render_template('user/settings.html', user=user)  # Исправленный путь

@user_bp.route('/history/checks')
@login_required
def history_checks():
    logger.info(f"Check history access for user: {g.user['_id']}")
    user = g.user
    user_id = user['_id']
    balance = user.get('balance', 0.0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')
    
    query = {'user_id': user_id}
    if search_query:
        query['imei'] = {'$regex': search_query, '$options': 'i'}
    if status_filter != 'all':
        query['status'] = status_filter
    
    checks = list(checks_collection.find(query)
        .sort('timestamp', -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    total = checks_collection.count_documents(query)
    
    for check in checks:
        check['formatted_timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M')
    
    logger.debug(f"Loaded {len(checks)} checks for user")
    return render_template(
        'user/history_checks.html',  # Исправленный путь
        user=user,
        balance=balance,
        checks=checks,
        page=page,
        per_page=per_page,
        total=total,
        search_query=search_query,
        status_filter=status_filter
    )

@user_bp.route('/check-details/<check_id>')
@login_required
def check_details(check_id):
    try:
        logger.info(f"Check details request: {check_id}")
        obj_id = ObjectId(check_id)
        user_id = g.user['_id']
        
        check = checks_collection.find_one({'_id': obj_id, 'user_id': user_id})
        
        if not check:
            logger.warning(f"Check not found: {check_id}")
            return jsonify({'error': 'შემოწმება ვერ მოიძებნა'}), 404
        
        check['formatted_timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Удаляем несериализуемые поля
        if '_id' in check:
            check['_id'] = str(check['_id'])
        if 'user_id' in check:
            check['user_id'] = str(check['user_id'])
        
        return jsonify(check)
    
    except InvalidId:
        logger.error(f"Invalid check ID: {check_id}")
        return jsonify({'error': 'არასწორი ID'}), 400

@user_bp.route('/accounts')
@login_required
def accounts():
    logger.info(f"Accounts access for user: {g.user['_id']}")
    user = g.user
    user_id = user['_id']
    
    payments = list(payments_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(20))
    
    for payment in payments:
        payment['formatted_timestamp'] = payment['timestamp'].strftime('%d.%m.%Y %H:%M')
    
    logger.debug(f"Loaded {len(payments)} payments for user")
    return render_template(
        'user/accounts.html',  # Исправленный путь
        user=user,
        payments=payments
    )

# Платежные роуты
@user_bp.route('/create-payment-session', methods=['POST'])
@login_required
def create_payment_session():
    try:
        logger.info("Creating payment session")
        data = request.get_json()
        if not data:
            logger.warning("Invalid payment session data")
            return jsonify({'error': 'არასწორი მონაცემები'}), 400
        
        try:
            amount = float(data.get('amount', 0))
        except (TypeError, ValueError):
            logger.error("Invalid amount format")
            return jsonify({'error': 'არასწორი თანხის ფორმატი'}), 400
        
        if amount < 1:
            logger.warning(f"Amount too low: {amount}")
            return jsonify({'error': 'მინიმალური თანხა: 1 ₾'}), 400

        user_id = g.user['_id']
        
        try:
            session_stripe = stripe_payment.create_topup_session(
                user_id=str(user_id),  # Преобразуем в строку
                amount=amount,
                success_url=url_for('user.topup_success', _external=True) + f'?amount={amount}',
                cancel_url=url_for('user.dashboard', _external=True) + '?payment=cancel'
            )
            
            logger.info(f"Stripe session created: {session_stripe.id}")
            return jsonify({'sessionId': session_stripe.id})
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e.user_message}")
            return jsonify({'error': str(e.user_message)}), 500
        
        except Exception as e:
            logger.exception("Payment creation error")
            return jsonify({'error': 'Payment system is temporarily unavailable'}), 500
    except Exception as e:
        logger.exception("Error in create-payment-session")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/topup/success')
@login_required
def topup_success():
    amount = request.args.get('amount', '0.00')
    logger.info(f"Topup success: {amount} GEL for user: {g.user['_id']}")
    
    # Обновляем данные пользователя
    try:
        user_id_str = session['user_id']
        g.user = regular_users_collection.find_one({'_id': ObjectId(user_id_str)})
    except Exception as e:
        logger.error(f"Failed to refresh user data: {str(e)}")
    
    return redirect(url_for(
        'user.dashboard',
        payment='success',
        amount=amount
    ))

@user_bp.route('/get-balance')
@login_required
def get_balance():
    try:
        logger.info(f"Balance request for user: {g.user['_id']}")
        user_id_str = session['user_id']
        user = regular_users_collection.find_one({'_id': ObjectId(user_id_str)})
        if user:
            balance = user.get('balance', 0.0)
            logger.debug(f"Balance retrieved: {balance}")
            return jsonify({'balance': balance})
        logger.warning(f"User not found: {user_id_str}")
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.exception("Error getting balance")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    logger.info("Stripe webhook received")
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Webhook data error: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature error: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    try:
        stripe_payment.handle_webhook(event)
        logger.info("Webhook processed successfully")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.exception("Webhook processing error")
        return jsonify({'error': str(e)}), 500
