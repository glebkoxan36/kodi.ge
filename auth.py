from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
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
        birth_day = request.form.get('birth_day')
        birth_month = request.form.get('birth_month')
        birth_year = request.form.get('birth_year')
        phone = request.form.get('phone')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Проверка заполненности полей
        if not all([first_name, last_name, birth_day, birth_month, birth_year, 
                   phone, email, username, password, confirm_password]):
            flash('გთხოვთ შეავსოთ ყველა ველი', 'danger')
            return redirect(url_for('auth.register'))
        
        # Проверка совпадения паролей
        if password != confirm_password:
            flash('პაროლები არ ემთხვევა', 'danger')
            return redirect(url_for('auth.register'))
        
        # Валидация email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('ელ. ფოსტის არასწორი ფორმატი', 'danger')
            return redirect(url_for('auth.register'))
        
        # Валидация телефона
        if not re.match(r'^\+995\d{9}$', phone):
            flash('ტელეფონის ნომერი უნდა იყოს ფორმატით +995XXXXXXXXX', 'danger')
            return redirect(url_for('auth.register'))
        
        # Проверка длины логина
        if len(username) < 4:
            flash('მომხმარებლის სახელი უნდა შედგებოდეს მინიმუმ 4 სიმბოლოსგან', 'danger')
            return redirect(url_for('auth.register'))
        
        # Проверка сложности пароля
        if len(password) < 12:
            flash('პაროლი უნდა შედგებოდეს მინიმუმ 12 სიმბოლოსგან', 'danger')
            return redirect(url_for('auth.register'))
        if not re.search(r'[A-Z]', password):
            flash('პაროლი უნდა შეიცავდეს მინიმუმ ერთ დიდ ასოს', 'danger')
            return redirect(url_for('auth.register'))
        if not re.search(r'[a-z]', password):
            flash('პაროლი უნდა შეიცავდეს მინიმუმ ერთ პატარა ასოს', 'danger')
            return redirect(url_for('auth.register'))
        if not re.search(r'[0-9]', password):
            flash('პაროლი უნდა შეიცავდეს მინიმუმ ერთ ციფრს', 'danger')
            return redirect(url_for('auth.register'))
        if not re.search(r'[@$!%*?&]', password):
            flash('პაროლი უნდა შეიცავდეს მინიმუმ ერთ სპეციალურ სიმბოლოს (@$!%*?&)', 'danger')
            return redirect(url_for('auth.register'))
        
        # Проверка уникальности email и username
        db = current_app.config['db']
        users_collection = db['users']
        
        if users_collection.find_one({'email': email}):
            flash('მომხმარებელი ამ ელ. ფოსტით უკვე არსებობს', 'danger')
            return redirect(url_for('auth.register'))
        
        if users_collection.find_one({'username': username}):
            flash('მომხმარებელი ამ სახელით უკვე არსებობს', 'danger')
            return redirect(url_for('auth.register'))
        
        # Создание пользователя
        hashed_password = generate_password_hash(password)
        birth_date = datetime(int(birth_year), int(birth_month), int(birth_day))
        
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
        
        flash('რეგისტრაცია წარმატებით დასრულდა!', 'success')
        return redirect(url_for('user.dashboard'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        
        if not identifier or not password:
            flash('გთხოვთ შეავსოთ ყველა ველი', 'danger')
            return redirect(url_for('auth.login'))
        
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
            flash('მომხმარებლის სახელი ან პაროლი არასწორია', 'danger')
            return redirect(url_for('auth.login'))
        
        if not check_password_hash(user['password'], password):
            flash('მომხმარებლის სახელი ან პაროლი არასწორია', 'danger')
            return redirect(url_for('auth.login'))
        
        # Успешная аутентификация
        session['user_id'] = str(user['_id'])
        session['role'] = user.get('role', 'user')
        
        flash('წარმატებული შესვლა!', 'success')
        return redirect(url_for('user.dashboard'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('თქვენ გამოხვედით სისტემიდან', 'success')
    return redirect(url_for('auth.login'))
