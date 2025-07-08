# auth.py
import re
import os
import logging
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, session, redirect, url_for, jsonify, flash, render_template
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from clerk import Clerk  # Импортируем Clerk

# Создаем Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к MongoDB
MONGODB_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['imei_checker']
regular_users_collection = db['users']
admin_users_collection = db['admin_users']
failed_logins_collection = db['failed_logins']

# Инициализация Clerk
clerk_client = Clerk(
    api_key=os.getenv('CLERK_SECRET_KEY'),
    frontend_api=os.getenv('CLERK_FRONTEND_API')
)

@auth_bp.route('/register', methods=['GET'])
def show_register_form():
    """Перенаправление на страницу регистрации Clerk"""
    return redirect(f"https://{os.getenv('CLERK_FRONTEND_API')}.clerk.accounts.dev/sign-up")

@auth_bp.route('/login', methods=['GET'])
def show_login_form():
    """Отображение страницы входа с кнопками социальных сетей"""
    return render_template('login.html', clerk_frontend_api=os.getenv('CLERK_FRONTEND_API'))

@auth_bp.route('/auth/google')
def auth_google():
    """Перенаправление на аутентификацию Google через Clerk"""
    redirect_url = clerk_client.oauth_url(
        provider='google',
        redirect_url=url_for('auth.auth_callback', _external=True)
    )
    return redirect(redirect_url)

@auth_bp.route('/auth/facebook')
def auth_facebook():
    """Перенаправление на аутентификацию Facebook через Clerk"""
    redirect_url = clerk_client.oauth_url(
        provider='facebook',
        redirect_url=url_for('auth.auth_callback', _external=True)
    )
    return redirect(redirect_url)

@auth_bp.route('/auth/callback')
def auth_callback():
    """Обработка callback от Clerk после аутентификации"""
    session_token = request.args.get('__session')
    if not session_token:
        flash('Ошибка аутентификации', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        # Проверка сессии Clerk
        user_data = clerk_client.verify_session(session_token)
        
        # Поиск или создание пользователя
        user = regular_users_collection.find_one({'clerk_user_id': user_data['id']})
        if not user:
            # Создаем нового пользователя
            email = user_data['email_addresses'][0]['email_address'] if user_data['email_addresses'] else None
            
            new_user = {
                'clerk_user_id': user_data['id'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'email': email,
                'role': 'user',
                'balance': 0.0,
                'created_at': datetime.utcnow()
            }
            result = regular_users_collection.insert_one(new_user)
            user_id = result.inserted_id
        else:
            user_id = user['_id']
        
        # Установка сессии
        session['user_id'] = str(user_id)
        session['role'] = 'user'
        session.modified = True
        
        return redirect(url_for('user.dashboard'))
    
    except Exception as e:
        logger.error(f'Clerk auth error: {str(e)}')
        flash('Ошибка аутентификации', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    """Выход из системы с перенаправлением на Clerk"""
    session.clear()
    return redirect(f"https://{os.getenv('CLERK_FRONTEND_API')}.clerk.accounts.dev/sign-out")
