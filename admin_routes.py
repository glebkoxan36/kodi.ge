from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from functools import wraps
from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
import requests
from db import (
    client, checks_collection, prices_collection, phonebase_collection, 
    parser_logs_collection, admin_users_collection, audit_logs_collection, 
    api_keys_collection, webhooks_collection, db, regular_users_collection,
    payments_collection
)
from price import get_current_prices, DEFAULT_PRICES
from utilities import upload_carousel_image  # Импорт новой функции
import cloudinary.uploader

admin_bp = Blueprint('admin', __name__)

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Проверяем наличие user_id или admin_id в сессии
        if 'user_id' not in session and 'admin_id' not in session:
            current_app.logger.warning("Unauthorized access attempt")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# Улучшенный декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Проверяем наличие административной сессии
        if 'admin_id' not in session or 'admin_role' not in session:
            current_app.logger.warning("Unauthorized admin access attempt")
            return redirect(url_for('auth.admin_login', next=request.url))
        
        # Проверяем существование администратора в базе
        try:
            admin = admin_users_collection.find_one({'_id': ObjectId(session['admin_id'])})
            if not admin or admin.get('role') not in ['admin', 'superadmin']:
                flash('Administrator account not found or invalid', 'danger')
                session.clear()
                return redirect(url_for('auth.admin_login'))
        except:
            session.clear()
            return redirect(url_for('auth.admin_login'))
            
        return f(*args, **kwargs)
    return decorated

# Вспомогательная функция для логирования аудита
def log_audit_event(action, details, user_id=None, username=None):
    try:
        event = {
            'action': action,
            'details': details,
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'username': username
        }
        audit_logs_collection.insert_one(event)
    except Exception as e:
        current_app.logger.error(f"Audit log error: {str(e)}")

# ======================================
# Админ-панель
# ======================================

@admin_bp.route('/dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    """Главная панель администратора"""
    try:
        if request.method == 'POST' and 'run_parser' in request.form:
            flash('Parser functionality is not implemented', 'info')
            return redirect(url_for('admin.admin_dashboard'))
        
        # Статистика (Исправлено: явная проверка на None)
        total_checks = checks_collection.count_documents({}) if checks_collection is not None else 0
        paid_checks = checks_collection.count_documents({'paid': True}) if checks_collection is not None else 0
        free_checks = total_checks - paid_checks
        
        # Выручка (Исправлено: явная проверка на None)
        total_revenue = 0
        if checks_collection is not None:
            revenue_cursor = checks_collection.aggregate([
                {"$match": {"paid": True}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ])
            revenue_data = list(revenue_cursor)
            total_revenue = revenue_data[0]['total'] if revenue_data else 0
        
        # Логи парсера (Исправлено: явная проверка на None)
        parser_logs = []
        if parser_logs_collection is not None:
            parser_logs = list(
                parser_logs_collection.find()
                .sort('timestamp', -1)
                .limit(10)
            )
            
            for log in parser_logs:
                log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                log['_id'] = str(log['_id'])
        
        # Статистика телефонов (Исправлено: явная проверка на None)
        total_phones = phonebase_collection.count_documents({}) if phonebase_collection is not None else 0
        brands = phonebase_collection.distinct("brand") if phonebase_collection is not None else []
        
        return render_template(
            'admin/dashboard.html',
            total_checks=total_checks,
            paid_checks=paid_checks,
            free_checks=free_checks,
            total_revenue=total_revenue,
            parser_logs=parser_logs,
            total_phones=total_phones,
            brands=brands,
            active_section='admin_dashboard'
        )
    except Exception as e:
        current_app.logger.error(f"Admin dashboard error: {str(e)}")
        return render_template('error.html', error="Admin error"), 500

@admin_bp.route('/price', methods=['GET', 'POST'])
@admin_required
def price_management():
    """Управление ценами для всех сервисов"""
    try:
        if request.method == 'POST':
            try:
                # Собираем новые цены для всех сервисов
                new_prices = {}
                for service in DEFAULT_PRICES.keys():
                    # Конвертируем в центы
                    price_value = float(request.form.get(service, 0))
                    new_prices[service] = int(price_value * 100)
                
                # Получаем текущие цены для истории
                current_doc = prices_collection.find_one({'type': 'current'})
                current_prices = current_doc['prices'] if current_doc else {}
                
                # Сохраняем историю изменений
                prices_collection.insert_one({
                    'type': 'history',
                    'prices': current_prices,
                    'changed_at': datetime.utcnow(),
                    'changed_by': session.get('admin_username', 'unknown')
                })
                
                # Обновляем текущие цены
                prices_collection.update_one(
                    {'type': 'current'},
                    {'$set': {
                        'prices': new_prices,
                        'updated_at': datetime.utcnow()
                    }},
                    upsert=True
                )
                
                # Аудит изменения цен
                log_audit_event(
                    action='price_change',
                    details={'new_prices': new_prices},
                    user_id=session.get('admin_id'),
                    username=session.get('admin_username')
                )
                
                flash('Prices updated successfully!', 'success')
                return redirect(url_for('admin.price_management'))
                
            except Exception as e:
                flash(f'Error updating prices: {str(e)}', 'danger')
        
        # Получаем текущие цены
        current_prices = get_current_prices()
        
        # Форматируем для отображения (в лари)
        formatted_prices = {
            service: price / 100 
            for service, price in current_prices.items()
        }
        
        # Получаем историю изменений цен
        price_history = list(prices_collection.find({'type': 'history'})
            .sort('changed_at', -1)
            .limit(5))
        
        # Форматируем историю
        for item in price_history:
            item['changed_at'] = item['changed_at'].strftime('%Y-%m-%d %H:%M')
            item['prices'] = {
                service: price / 100 
                for service, price in item['prices'].items()
            }
        
        # Группируем сервисы для отображения
        apple_services = [
            'fmi', 'blacklist', 'sim_lock', 
            'activation', 'carrier', 'mdm'
        ]
        
        android_services = [
            'samsung_v1', 'samsung_v2', 'samsung_knox',
            'xiaomi', 'google_pixel', 'huawei_v1',
            'huawei_v2', 'motorola', 'oppo', 'frp',
            'sim_lock_android'
        ]
        
        return render_template(
            'admin/price_management.html',
            current_prices=formatted_prices,
            price_history=price_history,
            apple_services=apple_services,
            android_services=android_services,
            active_section='price_management'
        )
    
    except Exception as e:
        current_app.logger.error(f"Price management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/history')
@admin_required
def check_history():
    """История проверок IMEI"""
    try:
        page = int(request.args.get('page', 1))
        per_page = 50
        imei_query = request.args.get('imei', '')
        
        # Формируем запрос
        query = {}
        if imei_query:
            query['imei'] = {'$regex': f'^{imei_query}'}
        
        # Исправлено: явная проверка на None
        total_checks = checks_collection.count_documents(query) if checks_collection is not None else 0
        
        checks = []
        if checks_collection is not None:
            checks = list(
                checks_collection.find(query)
                .sort('timestamp', -1)
                .skip((page - 1) * per_page)
                .limit(per_page)
            )
        
        # Получаем текущие цены
        current_prices = get_current_prices()
        
        # Форматируем данные для отображения
        for check in checks:
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            if check.get('paid'):
                check['amount'] = f"${check.get('amount', 0):.2f}"
            else:
                check['amount'] = 'Free'
            check['_id'] = str(check['_id'])
        
        return render_template(
            'admin/check_history.html',
            checks=checks,
            total_checks=total_checks,
            imei_query=imei_query,
            page=page,
            per_page=per_page,
            active_section='check_history'
        )
    except Exception as e:
        current_app.logger.error(f"Check history error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/db')
@admin_required
def db_management():
    """Главная страница управления БД"""
    try:
        # Исправлено: явная проверка на None
        collections = db.list_collection_names() if client is not None else []
        
        # Создаем словарь с количеством документов для каждой коллекции
        collection_counts = {}
        for name in collections:
            # Исправлено: явная проверка на None
            collection_counts[name] = db[name].count_documents({}) if client is not None else 0
        
        return render_template(
            'admin/db_management.html',
            active_section='db_management',
            collections=collections,
            collection_counts=collection_counts
        )
    except Exception as e:
        current_app.logger.error(f"Database error: {str(e)}")
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/db/<collection_name>', methods=['GET', 'POST'])
@admin_required
def collection_view(collection_name):
    """Просмотр и управление коллекцией"""
    try:
        # Обработка удаления документов
        if request.method == 'POST':
            doc_id = request.form.get('doc_id')
            if doc_id and client is not None:
                try:
                    db[collection_name].delete_one({'_id': ObjectId(doc_id)})
                    flash('Document deleted successfully', 'success')
                except Exception as e:
                    flash(f'Error deleting document: {str(e)}', 'danger')
            return redirect(url_for('admin.collection_view', collection_name=collection_name))
        
        # Пагинация
        page = int(request.args.get('page', 1))
        per_page = 20
        skip = (page - 1) * per_page
        
        # Получение документов
        documents = []
        total = 0
        # Исправлено: явная проверка на None
        if client is not None and collection_name in db.list_collection_names():
            total = db[collection_name].count_documents({})
            cursor = db[collection_name].find().skip(skip).limit(per_page)
            for doc in cursor:
                doc['_id'] = str(doc['_id'])  # Конвертируем ObjectId в строку
                documents.append(doc)
            
        return render_template(
            'admin/collection_view.html',
            active_section='db_management',
            collection_name=collection_name,
            documents=documents,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Collection view error: {str(e)}")
        flash(f'Error loading collection: {str(e)}', 'danger')
        return redirect(url_for('admin.db_management'))

@admin_bp.route('/db/<collection_name>/edit/<doc_id>', methods=['GET', 'POST'])
@admin_required
def edit_document(collection_name, doc_id):
    """Редактирование документа"""
    try:
        doc = None
        # Исправлено: явная проверка на None
        if client is not None:
            try:
                doc = db[collection_name].find_one({'_id': ObjectId(doc_id)})
            except:
                doc = None
        if not doc:
            flash('Document not found', 'danger')
            return redirect(url_for('admin.collection_view', collection_name=collection_name))
        
        if request.method == 'POST':
            try:
                # Собираем данные формы
                form_data = {}
                for key, value in request.form.items():
                    if key.startswith('field_'):
                        field_name = key[6:]
                        form_data[field_name] = value
                
                # Обновление документа
                db[collection_name].update_one(
                    {'_id': ObjectId(doc_id)},
                    {'$set': form_data}
                )
                flash('Document updated successfully', 'success')
                return redirect(url_for('admin.collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error updating document: {str(e)}', 'danger')
        
        # Преобразование ObjectId для отображения
        doc['_id'] = str(doc['_id'])
        
        return render_template(
            'admin/edit_document.html',
            active_section='db_management',
            collection_name=collection_name,
            doc_id=doc_id,
            document=doc
        )
    except Exception as e:
        current_app.logger.error(f"Edit document error: {str(e)}")
        flash(f'Error loading document: {str(e)}', 'danger')
        return redirect(url_for('admin.collection_view', collection_name=collection_name))

@admin_bp.route('/db/<collection_name>/add', methods=['GET', 'POST'])
@admin_required
def add_document(collection_name):
    """Добавление нового документа"""
    try:
        if request.method == 'POST':
            try:
                # Собираем данные формы
                form_data = {}
                for key, value in request.form.items():
                    if key.startswith('field_'):
                        field_name = key[6:]
                        form_data[field_name] = value
                
                # Вставка нового документа
                # Исправлено: явная проверка на None
                if client is not None:
                    result = db[collection_name].insert_one(form_data)
                    flash(f'Document added successfully with ID: {result.inserted_id}', 'success')
                else:
                    flash('Database connection error', 'danger')
                return redirect(url_for('admin.collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error adding document: {str(e)}', 'danger')
        
        return render_template(
            'admin/add_document.html',
            active_section='db_management',
            collection_name=collection_name
        )
    except Exception as e:
        current_app.logger.error(f"Add document error: {str(e)}")
        flash(f'Error loading form: {str(e)}', 'danger')
        return redirect(url_for('admin.collection_view', collection_name=collection_name))

# ======================================
# Управление каруселью
# ======================================
@admin_bp.route('/carousel', methods=['GET'])
@admin_required
def manage_carousel():
    """Управление каруселью главной страницы"""
    try:
        slides = list(db.carousel_slides.find().sort("order", 1))
        return render_template(
            'admin/manage_carousel.html',
            slides=slides,
            active_section='carousel'
        )
    except Exception as e:
        flash(f'Error loading carousel: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/carousel/add', methods=['GET', 'POST'])
@admin_required
def add_carousel_slide():
    """Добавление нового слайда карусели"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        order = int(request.form.get('order', 0))
        image_file = request.files.get('image')
        
        if not image_file:
            flash('Image is required', 'danger')
            return redirect(url_for('admin.add_carousel_slide'))
        
        try:
            # Загружаем изображение
            image_bytes = image_file.read()
            image_url, public_id = upload_carousel_image(image_bytes)
            
            # Проверяем успешность загрузки
            if not image_url:
                flash('Image upload failed. Please try again.', 'danger')
                return redirect(url_for('admin.add_carousel_slide'))
            
            # Сохраняем в базу
            db.carousel_slides.insert_one({
                'title': title,
                'description': description,
                'image_url': image_url,
                'public_id': public_id,
                'link': link,
                'order': order,
                'created_at': datetime.utcnow()
            })
            
            flash('Slide added successfully', 'success')
            return redirect(url_for('admin.manage_carousel'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('admin/add_carousel_slide.html')

@admin_bp.route('/carousel/edit/<slide_id>', methods=['GET', 'POST'])
@admin_required
def edit_carousel_slide(slide_id):
    """Редактирование слайда карусели"""
    try:
        slide = db.carousel_slides.find_one({'_id': ObjectId(slide_id)})
        if not slide:
            flash('Slide not found', 'danger')
            return redirect(url_for('admin.manage_carousel'))
        
        if request.method == 'POST':
            update_data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'link': request.form.get('link'),
                'order': int(request.form.get('order', 0)),
                'updated_at': datetime.utcnow()
            }
            
            # Обработка новой картинки
            image_file = request.files.get('image')
            if image_file:
                try:
                    # Загружаем новое изображение
                    image_bytes = image_file.read()
                    new_image_url, new_public_id = upload_carousel_image(image_bytes)
                    
                    if new_image_url:
                        # Удаляем старое изображение
                        if slide.get('public_id'):
                            try:
                                cloudinary.uploader.destroy(slide['public_id'])
                            except Exception as cloud_err:
                                current_app.logger.error(f"Error deleting old image: {str(cloud_err)}")
                        
                        # Обновляем данные
                        update_data['image_url'] = new_image_url
                        update_data['public_id'] = new_public_id
                    else:
                        flash('New image upload failed. Keeping old image.', 'warning')
                except Exception as e:
                    flash(f'Image upload error: {str(e)}', 'danger')
            
            db.carousel_slides.update_one(
                {'_id': ObjectId(slide_id)},
                {'$set': update_data}
            )
            flash('Slide updated successfully', 'success')
            return redirect(url_for('admin.manage_carousel'))
        
        return render_template('admin/edit_carousel_slide.html', slide=slide)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_carousel'))

@admin_bp.route('/carousel/delete/<slide_id>', methods=['POST'])
@admin_required
def delete_carousel_slide(slide_id):
    """Удаление слайда карусели"""
    try:
        slide = db.carousel_slides.find_one({'_id': ObjectId(slide_id)})
        if slide:
            # Удаляем изображение из Cloudinary
            if slide.get('public_id'):
                try:
                    cloudinary.uploader.destroy(slide['public_id'])
                except Exception as e:
                    current_app.logger.error(f"Error deleting carousel image: {str(e)}")
            
            # Удаляем из базы
            db.carousel_slides.delete_one({'_id': ObjectId(slide_id)})
            flash('Slide deleted successfully', 'success')
        else:
            flash('Slide not found', 'warning')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_carousel'))

# ======================================
# Управление администраторами
# ======================================

@admin_bp.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    """Управление пользователями админки"""
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role', 'admin')
            email = request.form.get('email', '')
            
            if not username or not password:
                flash('Username and password are required', 'danger')
                return redirect(url_for('admin.manage_users'))
            
            if admin_users_collection.find_one({'username': username}):
                flash('User already exists', 'danger')
                return redirect(url_for('admin.manage_users'))
            
            admin_users_collection.insert_one({
                'username': username,
                'password': generate_password_hash(password),
                'role': role,
                'email': email,
                'created_at': datetime.utcnow()
            })
            flash('User created successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        
        users = list(admin_users_collection.find({}, {'password': 0}))
        for user in users:
            user['_id'] = str(user['_id'])
            user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/manage_users.html',
            active_section='manage_users',
            users=users
        )
    except Exception as e:
        current_app.logger.error(f"User management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/users/delete/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Удаление пользователя"""
    try:
        # Нельзя удалить текущего пользователя или суперадмина
        current_username = session.get('admin_username')
        try:
            user = admin_users_collection.find_one({'_id': ObjectId(user_id)})
        except:
            user = None
        
        if not user:
            flash('User not found', 'danger')
        elif user['username'] == current_username:
            flash('You cannot delete yourself', 'danger')
        elif user['role'] == 'superadmin':
            flash('Cannot delete superadmin', 'danger')
        else:
            admin_users_collection.delete_one({'_id': ObjectId(user_id)})
            flash('User deleted successfully', 'success')
    except Exception as e:
        current_app.logger.error(f"Delete user error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_users'))

# ======================================
# Управление обычными пользователями
# ======================================

@admin_bp.route('/users/regular', methods=['GET'])
@admin_required
def manage_regular_users():
    """Управление обычными пользователями"""
    try:
        page = int(request.args.get('page', 1))
        per_page = 20
        search_query = request.args.get('search', '')
        
        query = {}
        if search_query:
            regex = re.compile(f'.*{search_query}.*', re.IGNORECASE)
            query = {
                '$or': [
                    {'email': regex},
                    {'username': regex},
                    {'first_name': regex},
                    {'last_name': regex}
                ]
            }
        
        # Используем коллекцию regular_users_collection из db.py
        users = list(regular_users_collection.find(query)
            .sort('created_at', -1)
            .skip((page - 1) * per_page)
            .limit(per_page))
        
        total = regular_users_collection.count_documents(query)
        
        for user in users:
            user['_id'] = str(user['_id'])
            user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
            user['balance'] = user.get('balance', 0.0)
        
        return render_template(
            'admin/manage_regular_users.html',
            active_section='manage_regular_users',
            users=users,
            page=page,
            per_page=per_page,
            total=total,
            search_query=search_query
        )
    except Exception as e:
        current_app.logger.error(f"Regular users management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/users/regular/<user_id>', methods=['GET'])
@admin_required
def view_regular_user(user_id):
    """Просмотр деталей обычного пользователя"""
    try:
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin.manage_regular_users'))
        
        # Преобразование ObjectId и дат
        user['_id'] = str(user['_id'])
        user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
        if 'birth_date' in user:
            user['birth_date'] = user['birth_date'].strftime('%Y-%m-%d')
        
        # Получение истории проверок пользователя
        checks = list(checks_collection.find({'user_id': ObjectId(user_id)})
            .sort('timestamp', -1)
            .limit(10))
        for check in checks:
            check['_id'] = str(check['_id'])
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        # Получение истории платежей
        payments = list(payments_collection.find({'user_id': ObjectId(user_id)})
            .sort('timestamp', -1)
            .limit(10))
        for payment in payments:
            payment['_id'] = str(payment['_id'])
            payment['timestamp'] = payment['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/view_regular_users.html',
            active_section='view_regular_user',
            user=user,
            checks=checks,
            payments=payments
        )
    except Exception as e:
        current_app.logger.error(f"View regular user error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_regular_users'))

@admin_bp.route('/users/regular/edit/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_regular_user(user_id):
    """Редактирование обычного пользователя"""
    try:
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin.manage_regular_users'))
        
        if request.method == 'POST':
            # Обработка формы редактирования
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            username = request.form.get('username')
            phone = request.form.get('phone')
            balance = float(request.form.get('balance', 0))
            is_blocked = request.form.get('is_blocked') == 'on'
            role = request.form.get('role', 'user')

            # Обновляем данные
            update_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'username': username,
                'phone': phone,
                'balance': balance,
                'is_blocked': is_blocked,
                'role': role,
                'updated_at': datetime.utcnow()
            }

            # Обновление в базе
            regular_users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )

            flash('User updated successfully', 'success')
            return redirect(url_for('admin.view_regular_user', user_id=user_id))

        # Преобразование для формы
        user['_id'] = str(user['_id'])
        if 'birth_date' in user:
            user['birth_date'] = user['birth_date'].strftime('%Y-%m-%d')

        return render_template(
            'admin/edit_regular_users.html',
            active_section='edit_regular_user',
            user=user
        )
    except Exception as e:
        current_app.logger.error(f"Edit regular user error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_regular_users'))

@admin_bp.route('/users/regular/block/<user_id>', methods=['POST'])
@admin_required
def block_regular_user(user_id):
    """Блокировка/разблокировка пользователя"""
    try:
        action = request.form.get('action')
        is_blocked = action == 'block'
        
        regular_users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_blocked': is_blocked}}
        )
        
        status = "blocked" if is_blocked else "unblocked"
        flash(f'User {status} successfully', 'success')
        return redirect(url_for('admin.view_regular_user', user_id=user_id))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_regular_users'))

@admin_bp.route('/users/regular/balance/<user_id>', methods=['POST'])
@admin_required
def adjust_user_balance(user_id):
    """Изменение баланса пользователя"""
    try:
        amount = float(request.form.get('amount', 0))
        operation = request.form.get('operation')
        
        if operation == 'add':
            update = {'$inc': {'balance': amount}}
        elif operation == 'subtract':
            update = {'$inc': {'balance': -amount}}
        else:
            flash('Invalid operation', 'danger')
            return redirect(url_for('admin.view_regular_user', user_id=user_id))
        
        # Обновление баланса
        regular_users_collection.update_one(
            {'_id': ObjectId(user_id)},
            update
        )
        
        # Логирование операции
        log_audit_event(
            action='balance_adjustment',
            details={
                'user_id': user_id,
                'amount': amount,
                'operation': operation
            },
            user_id=session.get('admin_id'),
            username=session.get('admin_username')
        )
        
        flash(f'Balance updated successfully', 'success')
        return redirect(url_for('admin.view_regular_user', user_id=user_id))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_regular_users'))

# ======================================
# Управление API-ключами
# ======================================

@admin_bp.route('/api-keys', methods=['GET', 'POST'])
@admin_required
def manage_api_keys():
    """Управление API ключами"""
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            permissions = request.form.get('permissions', '').split(',')
            expires_at = request.form.get('expires_at')
            
            if not name:
                flash('Name is required', 'danger')
                return redirect(url_for('admin.manage_api_keys'))
            
            # Генерация ключа
            api_key = secrets.token_urlsafe(32)
            
            # Сохранение ключа
            api_keys_collection.insert_one({
                'name': name,
                'key': api_key,
                'permissions': [p.strip() for p in permissions if p.strip()],
                'created_at': datetime.utcnow(),
                'expires_at': datetime.fromisoformat(expires_at) if expires_at else None,
                'revoked': False,
                'last_used': None
            })
            
            flash(f'API key created: {api_key}', 'success')
            return redirect(url_for('admin.manage_api_keys'))
        
        # Получение всех ключей (Исправлено: явная проверка на None)
        api_keys = []
        if api_keys_collection is not None:
            api_keys = list(api_keys_collection.find().sort('created_at', -1))
        
        # Преобразование ObjectId и дат
        for key in api_keys:
            key['_id'] = str(key['_id'])
            key['created_at'] = key['created_at'].strftime('%Y-%m-%d %H:%M')
            if key.get('expires_at'):
                key['expires_at'] = key['expires_at'].strftime('%Y-%m-%d')
            if key.get('last_used'):
                key['last_used'] = key['last_used'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/manage_api_keys.html',
            active_section='api_keys',
            api_keys=api_keys
        )
    except Exception as e:
        current_app.logger.error(f"API keys management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/api-keys/revoke/<key_id>', methods=['POST'])
@admin_required
def revoke_api_key(key_id):
    """Отзыв API ключа"""
    try:
        result = api_keys_collection.update_one(
            {'_id': ObjectId(key_id)},
            {'$set': {'revoked': True, 'revoked_at': datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            flash('API key revoked successfully', 'success')
        else:
            flash('API key not found', 'warning')
    except Exception as e:
        flash(f'Error revoking key: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_api_keys'))

@admin_bp.route('/api-keys/delete/<key_id>', methods=['POST'])
@admin_required
def delete_api_key(key_id):
    """Удаление API ключа"""
    try:
        result = api_keys_collection.delete_one({'_id': ObjectId(key_id)})
        if result.deleted_count > 0:
            flash('API key deleted successfully', 'success')
        else:
            flash('API key not found', 'warning')
    except Exception as e:
        flash(f'Error deleting key: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_api_keys'))

# ======================================
# Управление вебхуками
# ======================================

@admin_bp.route('/webhooks', methods=['GET', 'POST'])
@admin_required
def manage_webhooks():
    """Управление вебхуками"""
    try:
        if request.method == 'POST':
            url = request.form.get('url')
            events = request.form.get('events', '').split(',')
            secret = request.form.get('secret')
            
            if not url or not events:
                flash('URL and events are required', 'danger')
                return redirect(url_for('admin.manage_webhooks'))
            
            webhooks_collection.insert_one({
                'url': url,
                'events': [e.strip() for e in events if e.strip()],
                'secret': secret,
                'active': True,
                'created_at': datetime.utcnow(),
                'last_delivery': None,
                'last_status': None
            })
            
            flash('Webhook created successfully', 'success')
            return redirect(url_for('admin.manage_webhooks'))
        
        # Получение всех вебхуков (Исправлено: явная проверка на None)
        webhooks = []
        if webhooks_collection is not None:
            webhooks = list(webhooks_collection.find().sort('created_at', -1))
        
        # Преобразование данных
        for wh in webhooks:
            wh['_id'] = str(wh['_id'])
            wh['created_at'] = wh['created_at'].strftime('%Y-%m-%d %H:%M')
            if wh.get('last_delivery'):
                wh['last_delivery'] = wh['last_delivery'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/manage_webhooks.html',
            active_section='webhooks',
            webhooks=webhooks
        )
    except Exception as e:
        current_app.logger.error(f"Webhooks management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/webhooks/toggle/<webhook_id>', methods=['POST'])
@admin_required
def toggle_webhook(webhook_id):
    """Активация/деактивация вебхука"""
    try:
        webhook = webhooks_collection.find_one({'_id': ObjectId(webhook_id)})
        if not webhook:
            flash('Webhook not found', 'warning')
            return redirect(url_for('admin.manage_webhooks'))
        
        new_status = not webhook.get('active', False)
        webhooks_collection.update_one(
            {'_id': ObjectId(webhook_id)},
            {'$set': {'active': new_status}}
        )
        
        status = "activated" if new_status else "deactivated"
        flash(f'Webhook {status} successfully', 'success')
    except Exception as e:
        flash(f'Error toggling webhook: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_webhooks'))

@admin_bp.route('/webhooks/delete/<webhook_id>', methods=['POST'])
@admin_required
def delete_webhook(webhook_id):
    """Удаление вебхука"""
    try:
        result = webhooks_collection.delete_one({'_id': ObjectId(webhook_id)})
        if result.deleted_count > 0:
            flash('Webhook deleted successfully', 'success')
        else:
            flash('Webhook not found', 'warning')
    except Exception as e:
        flash(f'Error deleting webhook: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_webhooks'))

# ======================================
# Status Page
# ======================================

@admin_bp.route('/status')
@admin_required
def system_status():
    """Страница статуса системы"""
    try:
        # Делаем запрос к /health
        with current_app.test_client() as client:
            response = client.get('/health')
            health_data = response.get_json() or {}
        
        # Статистика использования (Исправлено: явная проверка на None)
        stats = {
            'total_checks': checks_collection.count_documents({}) if checks_collection is not None else 0,
            'active_webhooks': webhooks_collection.count_documents({'active': True}) if webhooks_collection is not None else 0,
            'valid_api_keys': api_keys_collection.count_documents({'revoked': False}) if api_keys_collection is not None else 0,
            'db_size': db.command('dbStats')['dataSize'] if client is not None else 0
        }
        
        # Последние события аудита (Исправлено: явная проверка на None)
        audit_events = []
        if audit_logs_collection is not None:
            audit_events = list(audit_logs_collection.find()
                .sort('timestamp', -1)
                .limit(10))
            
            for event in audit_events:
                event['_id'] = str(event['_id'])
                event['timestamp'] = event['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/system_status.html',
            active_section='system_status',
            health_data=health_data,
            system_stats=stats,
            audit_events=audit_events
        )
    except Exception as e:
        current_app.logger.error(f"System status error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

# ======================================
# User Switching
# ======================================

@admin_bp.route('/switch-user/<user_id>', methods=['POST'])
@admin_required
def switch_user(user_id):
    """Переключение на аккаунт пользователя из админ-панели"""
    try:
        # Сохраняем текущую админскую сессию
        admin_session = {
            'admin_id': session.get('admin_id'),
            'admin_role': session.get('admin_role'),
            'admin_username': session.get('admin_username')
        }
        
        # Устанавливаем пользовательскую сессию
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if user:
            # Очищаем только пользовательскую часть сессии
            session.pop('user_id', None)
            session.pop('role', None)
            
            # Устанавливаем новые пользовательские данные
            session['user_id'] = str(user['_id'])
            session['role'] = user.get('role', 'user')
            session.permanent = True
            
            # Восстанавливаем админскую сессию
            session['admin_id'] = admin_session['admin_id']
            session['admin_role'] = admin_session['admin_role']
            session['admin_username'] = admin_session['admin_username']
            
            # Помечаем сессию как измененную
            session.modified = True
            
            flash(f'Switched to user: {user.get("email")}', 'success')
            return redirect(url_for('user_dashboard.dashboard'))
        else:
            flash('User not found', 'danger')
            return redirect(url_for('admin.manage_regular_users'))
    except Exception as e:
        current_app.logger.error(f"Switch user error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_regular_users'))

@admin_bp.route('/switch-back', methods=['GET'])
@login_required
def switch_back():
    """Возврат к админской сессии из пользовательской"""
    try:
        # Сохраняем админскую сессию
        admin_session = {
            'admin_id': session.get('admin_id'),
            'admin_role': session.get('admin_role'),
            'admin_username': session.get('admin_username')
        }
        
        # Очищаем всю сессию
        session.clear()
        
        # Восстанавливаем только админскую сессию
        if admin_session['admin_id']:
            session['admin_id'] = admin_session['admin_id']
            session['admin_role'] = admin_session['admin_role']
            session['admin_username'] = admin_session['admin_username']
            session.permanent = True
            session.modified = True
            
            flash('Switched back to admin session', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('No admin session found', 'danger')
            return redirect(url_for('auth.admin_login'))
    except Exception as e:
        current_app.logger.error(f"Switch back error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard.dashboard'))
