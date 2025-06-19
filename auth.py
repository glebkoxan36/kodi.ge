# auth.py
import re
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, session, render_template, jsonify
from . import (
    app, 
    regular_users_collection,
    admin_users_collection,
    failed_logins_collection
)
from werkzeug.security import generate_password_hash, check_password_hash

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Регулярные выражения для валидации
GEORGIAN_LETTERS_REGEX = re.compile(r'^[\u10A0-\u10FF\s]+$')  # Грузинские буквы и пробелы
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$')
PHONE_REGEX = re.compile(r'^\+995\d{9}$')  # Пример: +995123456789

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
    email = data.get('email', '').strip().lower()  # Нормализация email
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # Валидация данных
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
    
    # Проверка уникальности данных
    if regular_users_collection.find_one({'$or': [{'username': username}, {'email': email}, {'phone': phone}]}):
        errors.append("Пользователь с такими данными уже существует")
    
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    # Создание пользователя
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
    logger.debug(f"Registered new user: {username} with ID: {result.inserted_id}")
    
    # Автоматический вход после регистрации
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
    logger.debug(f"Login attempt for: {identifier}")
    
    # Нормализация идентификатора
    identifier_lower = identifier.lower()
    
    # Проверка блокировки
    ip_address = request.remote_addr
    failed_login = failed_logins_collection.find_one({'ip': ip_address})
    
    if failed_login and failed_login.get('blocked_until') and datetime.utcnow() < failed_login['blocked_until']:
        remaining = int((failed_login['blocked_until'] - datetime.utcnow()).total_seconds() / 60)
        return jsonify({
            "success": False,
            "error": f"Аккаунт временно заблокирован. Попробуйте через {remaining} минут"
        }), 429
    
    # Поиск пользователя по email/телефону или username
    user = None
    is_admin = False
    
    # Попробовать найти обычного пользователя
    if '@' in identifier_lower:
        user = regular_users_collection.find_one({'email': identifier_lower})
    elif identifier.startswith('+995'):
        user = regular_users_collection.find_one({'phone': identifier})
    elif identifier.isdigit() and len(identifier) == 9:
        user = regular_users_collection.find_one({'phone': f"+995{identifier}"})
    else:
        user = regular_users_collection.find_one({'username': identifier})
    
    # Попробовать найти администратора
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

    # Проверка пароля
    if user and check_password_hash(user['password'], password):
        # Сброс счетчика неудачных попыток для IP
        if failed_login:
            failed_logins_collection.delete_one({'ip': ip_address})
        
        # Обновление данных пользователя
        collection = admin_users_collection if is_admin else regular_users_collection
        collection.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # Создание сессии
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        session['role'] = user['role']
        logger.debug(f"Successful login for: {user['username']} (Role: {user['role']})")
        
        # Перенаправление в зависимости от роли
        if user['role'] in ['admin', 'superadmin']:
            return jsonify({
                "success": True,
                "redirect_url": url_for('admin.admin_dashboard')
            }), 200
        else:
            return jsonify({
                "success": True,
                "redirect_url": url_for('user.dashboard')
            }), 200
    
    # Обработка неудачной попытки входа
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
    
    # Блокировка после 5 неудачных попыток
    if attempts >= 5:
        blocked_until = datetime.utcnow() + timedelta(minutes=10)
        failed_logins_collection.update_one(
            {'ip': ip_address},
            {'$set': {'blocked_until': blocked_until}}
        )
        logger.warning(f"IP blocked: {ip_address} for 10 minutes")
        return jsonify({
            "success": False,
            "error": "Слишком много попыток. Аккаунт заблокирован на 10 минут"
        }), 429
    
    logger.debug(f"Failed login attempt for: {identifier} from IP: {ip_address}")
    return jsonify({"success": False, "error": "Неверный логин или пароль"}), 401

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
