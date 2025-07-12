from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, g
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
from functools import wraps
import os
import stripe
from .stripepay import StripePayment
from datetime import datetime

# Инициализация Blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

# Проверка наличия ключей Stripe
stripe_api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

if not stripe_api_key or not STRIPE_PUBLIC_KEY:
    raise ValueError("Stripe API keys are missing in environment variables")

stripe.api_key = stripe_api_key

# Подключение к MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
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
            flash('გთხოვთ შეხვიდეთ სისტემაში', 'danger')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Middleware для загрузки текущего пользователя
@user_bp.before_request
def load_user():
    if 'user_id' in session and session.get('role') == 'user':
        try:
            g.user = regular_users_collection.find_one({'_id': ObjectId(session['user_id'])})
        except InvalidId:
            session.clear()
            flash('არასწორი სესია', 'danger')
            return redirect(url_for('auth.login'))

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
    user_id = session['user_id']
    user = g.user
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0.0)
    
    checks = list(checks_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    payments = list(payments_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    total_checks = checks_collection.count_documents({'user_id': user_id})
    
    avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
    
    return render_template(
        'user/dashboard.html',
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
    user = g.user
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    return render_template('user/settings.html', user=user)

@user_bp.route('/history/checks')
@login_required
def history_checks():
    user = g.user
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0.0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')
    
    query = {'user_id': user['_id']}
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
        check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M')
    
    return render_template(
        'user/history_checks.html',
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
        obj_id = ObjectId(check_id)
    except InvalidId:
        return jsonify({'error': 'არასწორი ID'}), 400
    
    user_id = session['user_id']
    check = checks_collection.find_one({'_id': obj_id, 'user_id': user_id})
    
    if not check:
        return jsonify({'error': 'შემოწმება ვერ მოიძებნა'}), 404
    
    check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(check)

@user_bp.route('/accounts')
@user_bp.route('/payment_history')
@login_required
def accounts():
    user = g.user
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    payments = list(payments_collection.find({'user_id': user['_id']})
        .sort('timestamp', -1)
        .limit(20))
    
    for payment in payments:
        payment['timestamp'] = payment['timestamp'].strftime('%d.%m.%Y %H:%M')
    
    return render_template(
        'user/accounts.html',
        user=user,
        payments=payments
    )

# Платежные роуты
@user_bp.route('/create-payment-session', methods=['POST'])
@login_required
def create_payment_session():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'არასწორი მონაცემები'}), 400
    
    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'არასწორი თანხის ფორმატი'}), 400
    
    if amount < 1:
        return jsonify({'error': 'მინიმალური თანხა: 1 ₾'}), 400

    user_id = session['user_id']
    
    try:
        session_stripe = stripe_payment.create_topup_session(
            user_id=user_id,
            amount=amount,
            success_url=url_for('user.topup_success', _external=True) + f'?amount={amount}',
            cancel_url=url_for('user.dashboard', _external=True) + '?payment=cancel'
        )
        
        return jsonify({'sessionId': session_stripe.id})
    
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe შეცდომა: {e.user_message}")
        return jsonify({'error': str(e.user_message)}), 500
    
    except Exception as e:
        current_app.logger.exception("გადახდის შექმნის შეცდომა")
        return jsonify({'error': 'გადახდის სისტემა დროებით მიუწვდომელია'}), 500

@user_bp.route('/topup/success')
@login_required
def topup_success():
    if 'user_id' not in session:
        flash('გთხოვთ შეხვიდეთ სისტემაში', 'danger')
        return redirect(url_for('auth.login'))
    
    amount = request.args.get('amount', '0.00')
    flash(f'გადახდა წარმატებით დასრულდა! თქვენი ბალანსი განახლდება მალე (+{amount} ₾).', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Верификация подписи Stripe
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        current_app.logger.error(f"ვებჰუკის მონაცემების შეცდომა: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        current_app.logger.error(f"ვებჰუკის ხელმოწერის შეცდომა: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    try:
        # Обработка вебхука через платежный модуль
        stripe_payment.handle_webhook(event)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"ვებჰუკის დამუშავების შეცდომა: {str(e)}")
        return jsonify({'error': str(e)}), 500
