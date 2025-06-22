# user_dashboard.py
import os
import stripe
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from bson import ObjectId

# Инициализация Blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

# Настройки Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')

# Подключение к MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['imei_checker']
regular_users_collection = db['users']
checks_collection = db['results']
comparisons_collection = db['comparisons']
payments_collection = db['payments']  # Коллекция для платежей

def login_required(f):
    """Декоратор для проверки аутентификации пользователя."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'user':
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def generate_avatar_color(name):
    """Генерирует цвет для аватара на основе имени"""
    colors = [
        '#00c6ff', '#ff3d71', '#00d68f', '#ffaa00', 
        '#8c7ae6', '#0097e6', '#e1b12c', '#44bd32'
    ]
    if not name:
        return colors[0]
    char_code = ord(name[0].lower())
    return colors[char_code % len(colors)]

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """Личный кабинет пользователя"""
    user_id = session['user_id']
    user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('login'))
    
    # Получение баланса
    balance = user.get('balance', 0)
    
    # Последние 5 проверок
    checks = list(checks_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    # Последние 5 сравнений
    comparisons = list(comparisons_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    # Последние 5 платежей
    payments = list(payments_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .limit(5))
    
    # Общее количество операций
    total_checks = checks_collection.count_documents({'user_id': user_id})
    total_comparisons = comparisons_collection.count_documents({'user_id': user_id})
    
    return render_template(
        'user/dashboard.html',
        user=user,
        balance=balance,
        checks=checks,
        comparisons=comparisons,
        payments=payments,
        total_checks=total_checks,
        total_comparisons=total_comparisons,
        generate_avatar_color=generate_avatar_color,
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
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Balance Topup',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata={
                    'user_id': session['user_id'],
                    'type': 'balance_topup'
                },
                success_url=url_for('user.topup_success', _external=True),
                cancel_url=url_for('user.topup_balance', _external=True),
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
        return redirect(url_for('login'))
    
    balance = user.get('balance', 0)
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    checks = list(checks_collection.find({'user_id': user_id})
        .sort('timestamp', -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    total = checks_collection.count_documents({'user_id': user_id})
    
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
        return redirect(url_for('login'))
    
    balance = user.get('balance', 0)
    
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
