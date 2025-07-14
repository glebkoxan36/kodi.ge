# auth.py
import logging
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

# Используем импортированную коллекцию из db.py
from db import regular_users_collection, admin_users_collection

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля"""
    handler = logging.FileHandler('logs/auth.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

auth_bp = Blueprint('auth', __name__)

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
        
        # Создание пользователя
        hashed_password = generate_password_hash(password)
        
        user = {
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': birth_date,
            'phone': phone,
            'email': email,
            'username': username,
            'password': hashed_password,
            'balance': 0.0,
            'role': 'user',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Сохранение в базу данных
        try:
            user_id = regular_users_collection.insert_one(user).inserted_id
            logger.info(f"User registered successfully: {email}")
        except Exception as e:
            logger.error(f"Error saving user: {str(e)}")
            return jsonify(success=False, errors=['სისტემური შეცდომა, გთხოვთ სცადოთ მოგვიანებით'])
        
        # Автоматический вход после регистрации
        session['user_id'] = str(user_id)
        session['role'] = 'user'
        # ФИКС: Делаем сессию постоянной
        session.permanent = True
        
        return jsonify(success=True)
    
    return render_template('register.html')

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
        # ФИКС: Делаем сессию постоянной
        session.permanent = True
        
        logger.info(f"User logged in: {user['email']}")
        return jsonify(success=True)
    
    return render_template('login.html')

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
        session['role'] = admin['role']
        session['username'] = admin['username']
        session.permanent = True
        
        logger.info(f"Admin logged in: {username}")
        flash('თქვენ წარმატებით შეხვედით სისტემაში', 'success')
        return redirect(next_url)
    
    return render_template('admin_login.html', next_url=next_url)

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    session.clear()
    flash('თქვენ გამოხვედით სისტემიდან', 'success')
    logger.info(f"User logged out: {user_id}")
    return redirect(url_for('auth.login'))
