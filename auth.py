# auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
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
        
        # Проверка заполненности полей
        if not all([first_name, last_name, birth_date_str, 
                   phone, email, username, password, confirm_password]):
            return jsonify(success=False, errors=['გთხოვთ შეავსოთ ყველა ველი'])
        
        # Проверка совпадения паролей
        if password != confirm_password:
            return jsonify(success=False, errors=['პაროლები არ ემთხვევა'])
        
        # Валидация email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify(success=False, errors=['ელ. ფოსტის არასწორი ფორმატი'])
        
        # Валидация телефона
        if not re.match(r'^\+995\d{9}$', phone):
            return jsonify(success=False, errors=['ტელეფონის ნომერი უნდა იყოს ფორმატით +995XXXXXXXXX'])
        
        # Валидация имени и фамилии (только грузинские буквы)
        georgian_regex = re.compile('^[\u10A0-\u10FF\s]+$')
        if not georgian_regex.match(first_name):
            return jsonify(success=False, errors=['სახელი უნდა შეიცავდეს მხოლოდ ქართულ ასოებს'])
        if not georgian_regex.match(last_name):
            return jsonify(success=False, errors=['გვარი უნდა შეიცავდეს მხოლოდ ქართულ ასოებს'])
        
        # Проверка длины логина
        if len(username) < 4:
            return jsonify(success=False, errors=['მომხმარებლის სახელი უნდა შედგებოდეს მინიმუმ 4 სიმბოლოსგან'])
        
        # Проверка сложности пароля
        if len(password) < 12:
            return jsonify(success=False, errors=['პაროლი უნდა შედგებოდეს მინიმუმ 12 სიმბოლოსგან'])
        if not re.search(r'[A-Z]', password):
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ დიდ ასოს'])
        if not re.search(r'[a-z]', password):
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ პატარა ასოს'])
        if not re.search(r'[0-9]', password):
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ ციფრს'])
        if not re.search(r'[@$!%*?&]', password):
            return jsonify(success=False, errors=['პაროლი უნდა შეიცავდეს მინიმუმ ერთ სპეციალურ სიმბოლოს (@$!%*?&)'])
        
        # Проверка уникальности email и username
        db = current_app.config['db']
        users_collection = db['users']
        
        if users_collection.find_one({'email': email}):
            return jsonify(success=False, errors=['მომხმარებელი ამ ელ. ფოსტით უკვე არსებობს'])
        
        if users_collection.find_one({'username': username}):
            return jsonify(success=False, errors=['მომხმარებელი ამ სახელით უკვე არსებობს'])
        
        # Преобразование даты рождения
        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        except ValueError:
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
        user_id = users_collection.insert_one(user).inserted_id
        
        # Автоматический вход после регистрации
        session['user_id'] = str(user_id)
        session['role'] = 'user'
        
        return jsonify(success=True)
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        
        if not identifier or not password:
            return jsonify(success=False, message='გთხოვთ შეავსოთ ყველა ველი')
        
        db = current_app.config['db']
        users_collection = db['users']
        
        # Поиск пользователя по email или username
        user = users_collection.find_one({
            '$or': [
                {'email': identifier},
                {'username': identifier}
            ]
        })
        
        if not user:
            return jsonify(success=False, message='მომხმარებლის სახელი ან პაროლი არასწორია')
        
        if not check_password_hash(user['password'], password):
            return jsonify(success=False, message='მომხმარებლის სახელი ან პაროლი არასწორია')
        
        # Успешная аутентификация
        session['user_id'] = str(user['_id'])
        session['role'] = user.get('role', 'user')
        
        return jsonify(success=True)
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('თქვენ გამოხვედით სისტემიდან', 'success')
    return redirect(url_for('auth.login'))
