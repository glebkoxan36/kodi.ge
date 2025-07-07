from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from pymongo import MongoClient
from bson import ObjectId
from functools import wraps
import os
import stripe

# Инициализация Blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

# Настройка Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Подключение к MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['imei_checker']
regular_users_collection = db['users']
checks_collection = db['results']
comparisons_collection = db['comparisons']
payments_collection = db['payments']
refunds_collection = db['refunds']

# Импорт платежного модуля (предполагается, что он существует)
from .stripepay import StripePayment

stripe_payment = StripePayment(
    stripe_api_key=os.getenv('STRIPE_SECRET_KEY'),
    webhook_secret=os.getenv('STRIPE_WEBHOOK_SECRET'),
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
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0.0)
    
    checks = list(checks_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    comparisons = list(comparisons_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    payments = list(payments_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    total_checks = checks_collection.count_documents({'user_id': user_id})
    total_comparisons = comparisons_collection.count_documents({'user_id': user_id})
    
    avatar_color = generate_avatar_color(user.get('first_name', '') + ' ' + user.get('last_name', ''))
    
    return render_template(
        'user/dashboard.html',
        user=user,
        balance=balance,
        last_checks=checks,
        last_comparisons=comparisons,
        last_payments=payments,
        total_checks=total_checks,
        total_comparisons=total_comparisons,
        avatar_color=avatar_color,
        stripe_public_key=STRIPE_PUBLIC_KEY
    )

@user_bp.route('/settings')
@login_required
def settings():
    user_id = session['user_id']
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    return render_template('user/settings.html', user=user)

@user_bp.route('/history/comparisons')
@login_required
def history_comparisons():
    user_id = session['user_id']
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0.0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    comparisons = list(comparisons_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    total = comparisons_collection.count_documents({'user_id': user_id})
    
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

@user_bp.route('/history/checks')
@login_required
def history_checks():
    user_id = session['user_id']
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
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
    user_id = session['user_id']
    check = checks_collection.find_one({'_id': ObjectId(check_id), 'user_id': user_id})
    
    if not check:
        return jsonify({'error': 'Check not found'}), 404
    
    check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(check)

@user_bp.route('/accounts')
@login_required
def accounts():
    user_id = session['user_id']
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('მომხმარებელი ვერ მოიძებნა', 'danger')
        return redirect(url_for('auth.login'))
    
    balance = user.get('balance', 0.0)
    
    payments = list(payments_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(20))
    
    for payment in payments:
        payment['timestamp'] = payment['timestamp'].strftime('%d.%m.%Y %H:%M')
    
    return render_template(
        'user/accounts.html',
        user=user,
        balance=balance,
        payments=payments
    )

# Платежные роуты
@user_bp.route('/create-payment-session', methods=['POST'])
@login_required
def create_payment_session():
    data = request.json
    amount = float(data.get('amount'))
    user_id = session['user_id']
    
    if amount < 1:
        return jsonify({'error': 'მინიმალური თანხა: 1 ₾'}), 400

    try:
        session_stripe = stripe_payment.create_topup_session(
            user_id=user_id,
            amount=amount,
            success_url=url_for('user.dashboard', _external=True) + '?payment=success&amount=' + str(amount),
            cancel_url=url_for('user.dashboard', _external=True) + '?payment=cancel'
        )
        
        return jsonify({'sessionId': session_stripe.id})
    except Exception as e:
        current_app.logger.error(f"შეცდომა გადახდის შექმნისას: {str(e)}")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/topup/success')
@login_required
def topup_success():
    flash('გადახდა წარმატებით დასრულდა! თქვენი ბალანსი განახლდება მალე.', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/topup', methods=['GET', 'POST'])
@login_required
def topup_balance():
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        user_id = session['user_id']
        
        if amount < 1:
            flash('მინიმალური თანხა: 1 ₾', 'danger')
            return redirect(url_for('user.accounts'))
        
        try:
            session_stripe = stripe_payment.create_topup_session(
                user_id=user_id,
                amount=amount,
                success_url=url_for('user.topup_success', _external=True),
                cancel_url=url_for('user.accounts', _external=True)
            )
            return redirect(session_stripe.url)
        except Exception as e:
            flash(f'შეცდომა: {str(e)}', 'danger')
            return redirect(url_for('user.accounts'))
    
    return redirect(url_for('user.accounts'))

@user_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe_payment.handle_webhook(payload, sig_header)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"ვებჰუკის შეცდომა: {str(e)}")
        return jsonify({'error': str(e)}), 400
