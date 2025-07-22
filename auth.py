# auth.py
import logging
import re
import secrets
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
import requests
from urllib.parse import urlencode
import time

# Используем импортированную коллекцию из db.py
from db import regular_users_collection, admin_users_collection
from utilities import generate_verification_code, send_verification_email, store_verification_data, verify_code

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля"""
    # Создаем папку для логов если не существует
    os.makedirs('logs', exist_ok=True)
    
    handler = logging.FileHandler('logs/auth.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

auth_bp = Blueprint('auth', __name__)

# Facebook OAuth configuration
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
FACEBOOK_REDIRECT_URI = os.getenv('FACEBOOK_REDIRECT_URI')

# Глобальное хранилище для кодов верификации
verification_storage = {}

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    logger.info(f"Register request: {request.method}")
    if request.method == 'POST':
        # Получение данных формы
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        birth_date_str = request.form.get('birth_date')
        phone = request.form.get('phone')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        logger.debug(f"Registration attempt: {email}, {username}")
        
        # Проверка заполненности полей
        if not all([first_name, last_name, birth_date_str, 
                   phone, email, username, password, confirm_password]):
            logger.warning("Missing fields in registration")
            return jsonify(success=False, errors=['გთხოვთ შეავსოთ ყველა ველი'])
        
        # Проверка совпадения паролей
        if password != confirm_password:
            logger.warning("Password mismatch in registration")
            return jsonify(success=False, errors=['პაროლები არ ემთხვევა'])
        
        # Валидация email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            logger.warning(f"Invalid email format: {email}")
            return jsonify(success=False, errors=['ელ. ფოსტის არასწორი ფორმატი'])
        
        # Валидация телефона
        if not re.match(r'^\+995\d{9}$', phone):
            logger.warning(f"Invalid phone format: {phone}")
            return jsonify(success=False, errors=['ტელეფონის ნომერი უნდა იყოს ფორმატით +995XXXXXXXXX'])
        
        # Валидация имени и фамилии (только грузинские буквы)
        georgian_regex = re.compile('^[\u10A0-\u10FF\s]+$')
        if not georgian_regex.match(first_name):
            logger.warning(f"Invalid first name: {first_name}")
            return jsonify(success=False, errors=['სახელი უნდა შეიცავდეს მხოლოდ ქართულ ასოებს'])
        if not georgian_regex.match(last_name):
            logger.warning(f"Invalid last name: {last_name}")
            return jsonify(success=False, errors=['გვარი უნდა შეიცავდეს მხოლოდ ქართულ ასოებს'])
        
        # Проверка длины логина
        if len(username) < 4:
            logger.warning(f"Username too short: {username}")
            return jsonify(success=False, errors=['მომხმარებლის სახელი უნდა შედგებოდეს მინიმუმ 4 სიმბოლოსგან'])
        
        # Проверка сложности пароля
        if len(password) < 12:
            logger.warning("Password too short")
            return jsonify(success=False, errors=['პაროლი უნდა შედგებოდეს მინიმუმ 12 სიმბოლოსგან'])
        if not re.search(r'[A-Z]', password):
            logger.warning("Password missing uppercase")
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ დიდ ასოს'])
        if not re.search(r'[a-z]', password):
            logger.warning("Password missing lowercase")
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ პატარა ასოს'])
        if not re.search(r'[0-9]', password):
            logger.warning("Password missing digit")
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ ციფრს'])
        if not re.search(r'[@$!%*?&]', password):
            logger.warning("Password missing special character")
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ სპეციალურ სიმბოლოს (@$!%*?&)'])
        
        # Проверка уникальности email и username
        if regular_users_collection.find_one({'email': email}):
            logger.warning(f"Email already exists: {email}")
            return jsonify(success=False, errors=['მომხმარებელი ამ ელ. ფოსტით უკვე არსებობს'])
        
        if regular_users_collection.find_one({'username': username}):
            logger.warning(f"Username already exists: {username}")
            return jsonify(success=False, errors=['მომხმარებელი ამ სახელით უკვე არსებობს'])
        
        # Преобразование даты рождения
        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Invalid birth date format: {birth_date_str}")
            return jsonify(success=False, errors=['დაბადების თარიღის არასწორი ფორმატი'])
        
        # Генерация кода верификации
        verification_code = generate_verification_code()
        
        # Сохраняем данные для верификации
        store_verification_data(
            email, 
            verification_code, 
            verification_storage
        )
        
        # Отправляем email с кодом
        if not send_verification_email(email, verification_code):
            return jsonify(success=False, errors=['ვერიფიკაციის კოდის გაგზავნა ვერ მოხერხდა'])
        
        # Сохраняем данные пользователя в сессии
        session['pending_user'] = {
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': birth_date_str,
            'phone': phone,
            'email': email,
            'username': username,
            'password': password,
            'verification_email': email
        }
        
        return jsonify(
            success=False, 
            verify_required=True,
            message='ვერიფიკაციის კოდი გამოგზავნილია თქვენს ელ. ფოსტაზე'
        )
    
    return render_template('register.html')

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.json
    code = data.get('code')
    email = session.get('pending_user', {}).get('verification_email')
    
    if not email:
        return jsonify(success=False, message='სესიის ვადა გაუვიდა')
    
    is_valid, message = verify_code(email, code, verification_storage)
    
    if is_valid:
        # Получаем данные из сессии
        user_data = session['pending_user']
        
        # Создаем пользователя
        try:
            birth_date = datetime.strptime(user_data['birth_date'], '%Y-%m-%d')
            hashed_password = generate_password_hash(user_data['password'])
            
            user = {
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'birth_date': birth_date,
                'phone': user_data['phone'],
                'email': user_data['email'],
                'username': user_data['username'],
                'password': hashed_password,
                'balance': 0.0,
                'role': 'user',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'email_verified': True
            }
            
            user_id = regular_users_collection.insert_one(user).inserted_id
            logger.info(f"User registered with verification: {user_data['email']}")
            
            # Очищаем сессию
            session.pop('pending_user', None)
            
            # Авторизуем пользователя
            session['user_id'] = str(user_id)
            session['role'] = 'user'
            session.permanent = True
            session.modified = True
            
            return jsonify(success=True)
        except Exception as e:
            logger.error(f"Error completing registration: {str(e)}")
            return jsonify(success=False, message='რეგისტრაციის დროს მოხდა შეცდომა')
    
    return jsonify(success=False, message=message)

@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    pending_user = session.get('pending_user')
    if not pending_user:
        return jsonify(success=False, message='სესიის ვადა გაუვიდა')
    
    email = pending_user['email']
    
    # Генерируем новый код
    new_code = generate_verification_code()
    
    # Обновляем хранилище
    store_verification_data(email, new_code, verification_storage)
    
    # Отправляем email
    if send_verification_email(email, new_code):
        return jsonify(success=True, message='ახალი კოდი გამოგზავნილია')
    
    return jsonify(success=False, message='კოდის გაგზავნა ვერ მოხერხდა')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"Login request: {request.method}")
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        
        if not identifier or not password:
            logger.warning("Missing credentials in login")
            return jsonify(success=False, message='გთხოვთ შეავსოთ ყველა ველი')
        
        logger.debug(f"Login attempt: {identifier}")
        
        # Поиск пользователя по email или username
        user = regular_users_collection.find_one({
            '$or': [
                {'email': identifier},
                {'username': identifier}
            ]
        })
        
        if not user:
            logger.warning(f"User not found: {identifier}")
            return jsonify(success=False, message='მომხმარებლის სახელი ან პაროლი არასწორია')
        
        if not check_password_hash(user['password'], password):
            logger.warning(f"Invalid password for: {identifier}")
            return jsonify(success=False, message='მომხმარებლის სახელი ან პაროლი არასწორია')
        
        # Успешная аутентификация
        session['user_id'] = str(user['_id'])
        session['role'] = user.get('role', 'user')
        # Делаем сессию постоянной
        session.permanent = True
        session.modified = True
        
        logger.info(f"User logged in: {user['email']}")
        return jsonify(success=True)
    
    return render_template('login.html')

@auth_bp.route('/facebook/login')
def facebook_login():
    """Перенаправление на Facebook для авторизации"""
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        logger.error("Facebook OAuth not configured")
        flash('Facebook ავტორიზაცია არ არის კონფიგურირებული', 'danger')
        return redirect(url_for('auth.login'))
    
    # Генерация state для защиты от CSRF
    state = secrets.token_urlsafe(16)
    session['facebook_state'] = state
    
    params = {
        'client_id': FACEBOOK_APP_ID,
        'redirect_uri': FACEBOOK_REDIRECT_URI,
        'scope': 'email,public_profile',
        'response_type': 'code',
        'state': state
    }
    url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    return redirect(url)

@auth_bp.route('/facebook/callback')
def facebook_callback():
    """Обработка ответа от Facebook"""
    # Проверка ошибок
    if 'error' in request.args:
        error_msg = request.args.get('error_description', 'Unknown Facebook error')
        logger.error(f"Facebook auth error: {error_msg}")
        flash('Facebook ავტორიზაცია ვერ მოხერხდა', 'danger')
        return redirect(url_for('auth.login'))
    
    # Проверка state для защиты от CSRF
    state = request.args.get('state')
    if not state or state != session.get('facebook_state'):
        logger.warning("Facebook state mismatch - possible CSRF attack")
        flash('უსაფრთხოების შეცდომა', 'danger')
        return redirect(url_for('auth.login'))
    
    # Получение кода авторизации
    code = request.args.get('code')
    if not code:
        logger.warning("Facebook callback without code")
        return redirect(url_for('auth.login'))
    
    try:
        # Обмен кода на access token
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        token_params = {
            'client_id': FACEBOOK_APP_ID,
            'client_secret': FACEBOOK_APP_SECRET,
            'redirect_uri': FACEBOOK_REDIRECT_URI,
            'code': code
        }
        token_response = requests.get(token_url, params=token_params)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data['access_token']
        
        # Получение информации о пользователе
        user_info_url = "https://graph.facebook.com/v18.0/me"
        params = {
            'fields': 'id,email,first_name,last_name,picture',
            'access_token': access_token
        }
        user_response = requests.get(user_info_url, params=params)
        user_response.raise_for_status()
        user_info = user_response.json()
        
        # Извлечение данных пользователя
        facebook_id = user_info['id']
        email = user_info.get('email')
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')
        picture_url = None
        if 'picture' in user_info and 'data' in user_info['picture']:
            picture_url = user_info['picture']['data'].get('url')
        
        if not email:
            logger.warning("Facebook user without email")
            flash('Facebook არ მიაწოდებს თქვენს ელ. ფოსტას. გთხოვთ გამოიყენოთ სხვა მეთოდი', 'warning')
            return redirect(url_for('auth.login'))
        
        # Поиск пользователя по email или Facebook ID
        user = regular_users_collection.find_one({
            '$or': [
                {'email': email},
                {'facebook_id': facebook_id}
            ]
        })
        
        if user:
            # Обновление Facebook ID для существующего пользователя
            if not user.get('facebook_id'):
                regular_users_collection.update_one(
                    {'_id': user['_id']},
                    {'$set': {
                        'facebook_id': facebook_id,
                        'updated_at': datetime.utcnow()
                    }}
                )
                logger.info(f"Facebook ID added for user: {user['email']}")
        else:
            # Создание нового пользователя
            username = email.split('@')[0]
            # Проверка уникальности username
            counter = 1
            while regular_users_collection.find_one({'username': username}):
                username = f"{email.split('@')[0]}_{counter}"
                counter += 1
            
            # Генерация случайного пароля
            password = secrets.token_urlsafe(16)
            
            new_user = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'username': username,
                'password': generate_password_hash(password),
                'facebook_id': facebook_id,
                'avatar_url': picture_url,
                'balance': 0.0,
                'role': 'user',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'email_verified': True
            }
            user_id = regular_users_collection.insert_one(new_user).inserted_id
            user = regular_users_collection.find_one({'_id': user_id})
            logger.info(f"New user created via Facebook: {email}")
        
        # Авторизация пользователя
        session['user_id'] = str(user['_id'])
        session['role'] = user.get('role', 'user')
        session.permanent = True
        session.modified = True
        
        logger.info(f"User logged in via Facebook: {email}")
        return redirect(url_for('user_dashboard.dashboard'))
    
    except Exception as e:
        logger.exception(f"Facebook auth error: {str(e)}")
        flash('Facebook-ით შესვლისას დაფიქსირდა შეცდომა', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Аутентификация администратора"""
    logger.info(f"Admin login request: {request.method}")
    
    # Получаем URL для перенаправления
    next_url = request.args.get('next') or url_for('admin.admin_dashboard')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('გთხოვთ შეავსოთ ყველა ველი', 'error')
            logger.warning("Missing admin credentials")
            return redirect(url_for('auth.admin_login', next=next_url))
        
        logger.debug(f"Admin login attempt: {username}")
        
        # Сохраняем текущую пользовательскую сессию
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Поиск администратора по имени пользователя
        admin = admin_users_collection.find_one({'username': username})
        
        if not admin:
            logger.warning(f"Admin not found: {username}")
            flash('არასწორი მომხმარებლის სახელი ან პაროლი', 'error')
            return redirect(url_for('auth.admin_login', next=next_url))
        
        if not check_password_hash(admin['password'], password):
            logger.warning(f"Invalid password for admin: {username}")
            flash('არასწორი მომხმარებლის სახელი ან პაროლი', 'error')
            return redirect(url_for('auth.admin_login', next=next_url))
        
        # Успешная аутентификация
        session['admin_id'] = str(admin['_id'])
        session['admin_role'] = admin['role']  # Используем отдельный ключ для роли администратора
        session['admin_username'] = admin['username']  # Сохраняем имя администратора
        session.permanent = True
        session.modified = True
        
        # Восстанавливаем пользовательскую сессию
        if user_id:
            session['user_id'] = user_id
            session['role'] = user_role
        
        logger.info(f"Admin logged in: {username}")
        flash('თქვენ წარმატებით შეხვედით სისტემაში', 'success')
        return redirect(next_url)
    
    return render_template('admin_login.html', next_url=next_url)

@auth_bp.route('/logout')
def logout():
    """Выход только из пользовательской сессии"""
    try:
        # Сохраняем данные администратора
        admin_data = {
            'admin_id': session.get('admin_id'),
            'admin_role': session.get('admin_role'),
            'admin_username': session.get('admin_username')
        }
        
        # Очищаем только пользовательские данные
        session.pop('user_id', None)
        session.pop('role', None)
        
        # Восстанавливаем админские данные
        if admin_data['admin_id']:
            session['admin_id'] = admin_data['admin_id']
            session['admin_role'] = admin_data['admin_role']
            session['admin_username'] = admin_data['admin_username']
            session.permanent = True
        
        session.modified = True
        
        flash('თქვენ გამოხვედით სისტემიდან', 'success')
        logger.info(f"User logged out, admin session preserved: {session.get('admin_id')}")
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        flash('Error during logout', 'danger')
        return redirect(url_for('index'))

@auth_bp.route('/admin/logout')
def admin_logout():
    """Выход только из административной сессии"""
    try:
        # Сохраняем данные пользователя
        user_data = {
            'user_id': session.get('user_id'),
            'role': session.get('role')
        }
        
        # Очищаем только административные данные
        session.pop('admin_id', None)
        session.pop('admin_role', None)
        session.pop('admin_username', None)
        
        # Восстанавливаем пользовательские данные
        if user_data['user_id']:
            session['user_id'] = user_data['user_id']
            session['role'] = user_data['role']
            session.permanent = True
        
        session.modified = True
        
        flash('თქვენ გამოხვედით ადმინ პანელიდან', 'success')
        logger.info(f"Admin logged out, user session preserved: {session.get('user_id')}")
        return redirect(url_for('auth.admin_login'))
    except Exception as e:
        logger.error(f"Admin logout error: {str(e)}")
        flash('Error during admin logout', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
