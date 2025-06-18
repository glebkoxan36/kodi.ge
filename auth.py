# auth.py
import re
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, flash, session
from . import (
    app, 
    regular_users_collection,
    admin_users_collection,
    failed_logins_collection
)
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)

# Регулярные выражения для валидации
GEORGIAN_LETTERS_REGEX = re.compile(r'^[\u10A0-\u10FF\s]+$')  # Грузинские буквы и пробелы
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$')
PHONE_REGEX = re.compile(r'^\+995\d{9}$')  # Пример: +995123456789

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.form
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    birth_day = data.get('birth_day')
    birth_month = data.get('birth_month')
    birth_year = data.get('birth_year')
    phone = data.get('phone')
    email = data.get('email')
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
        if birth_date > datetime.now():
            errors.append("Дата рождения не может быть в будущем")
    except ValueError:
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
        return {"success": False, "errors": errors}, 400

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
    
    # Автоматический вход после регистрации
    session['user_id'] = str(result.inserted_id)
    session['username'] = username
    session['role'] = 'user'
    
    return {"success": True, "message": "Регистрация успешна!"}, 201

@auth_bp.route('/login', methods=['POST'])
def login():
    identifier = request.form.get('identifier')
    password = request.form.get('password')
    
    # Проверка блокировки
    ip_address = request.remote_addr
    failed_login = failed_logins_collection.find_one({'ip': ip_address})
    
    if failed_login and failed_login.get('blocked_until') and datetime.utcnow() < failed_login['blocked_until']:
        remaining = int((failed_login['blocked_until'] - datetime.utcnow()).total_seconds() / 60)
        return {
            "success": False,
            "error": f"Аккаунт временно заблокирован. Попробуйте через {remaining} минут"
        }, 429
    
    # Поиск пользователя по email/телефону или username
    user = None
    if '@' in identifier:
        user = regular_users_collection.find_one({'email': identifier})
    elif identifier.startswith('+995'):
        user = regular_users_collection.find_one({'phone': identifier})
    else:
        user = regular_users_collection.find_one({'username': identifier})
    
    # Проверка администратора
    if not user:
        admin_user = admin_users_collection.find_one({'username': identifier})
        if admin_user and check_password_hash(admin_user['password'], password):
            session['user_id'] = str(admin_user['_id'])
            session['username'] = admin_user['username']
            session['role'] = admin_user['role']
            return {"success": True}, 200
    
    if not user or not check_password_hash(user['password'], password):
        # Обработка неудачной попытки входа
        attempts = 1
        if failed_login:
            attempts = failed_login['attempts'] + 1
            failed_logins_collection.update_one(
                {'ip': ip_address},
                {'$set': {
                    'attempts': attempts,
                    'last_attempt': datetime.utcnow()
                }}
            )
        else:
            failed_logins_collection.insert_one({
                'ip': ip_address,
                'attempts': 1,
                'last_attempt': datetime.utcnow()
            })
        
        # Блокировка после 5 неудачных попыток
        if attempts >= 5:
            blocked_until = datetime.utcnow() + timedelta(minutes=10)
            failed_logins_collection.update_one(
                {'ip': ip_address},
                {'$set': {'blocked_until': blocked_until}}
            )
            return {
                "success": False,
                "error": "Слишком много попыток. Аккаунт заблокирован на 10 минут"
            }, 429
        
        return {"success": False, "error": "Неверный логин или пароль"}, 401
    
    # Сброс счетчика неудачных попыток
    if failed_login:
        failed_logins_collection.delete_one({'ip': ip_address})
    
    # Обновление данных пользователя
    regular_users_collection.update_one(
        {'_id': user['_id']},
        {'$set': {
            'last_login': datetime.utcnow(),
            'failed_attempts': 0
        }}
    )
    
    # Создание сессии
    session['user_id'] = str(user['_id'])
    session['username'] = user['username']
    session['role'] = user['role']
    
    return {"success": True}, 200

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
