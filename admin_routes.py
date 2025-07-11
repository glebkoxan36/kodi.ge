from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
import threading
from app import (
    admin_required, get_current_prices, log_audit_event, health_check,
    checks_collection, prices_collection, phones_collection, parser_logs_collection,
    admin_users_collection, audit_logs_collection, api_keys_collection, webhooks_collection,
    db, MONGODB_URI
)

admin_bp = Blueprint('admin', __name__)

# ======================================
# Админ-панель
# ======================================

@admin_bp.route('/dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    """Главная панель администратора"""
    try:
        if request.method == 'POST' and 'run_parser' in request.form:
            try:
                from gsm_parser.scrap_specs import main as run_gsm_parser
                thread = threading.Thread(target=run_gsm_parser, args=(MONGODB_URI,))
                thread.start()
                flash('Parser started in background', 'success')
            except Exception as e:
                current_app.logger.error(f"Parser error: {str(e)}")
                flash(f'Error starting parser: {str(e)}', 'danger')
            return redirect(url_for('admin.admin_dashboard'))
        
        # Статистика
        total_checks = checks_collection.count_documents({})
        paid_checks = checks_collection.count_documents({'paid': True})
        free_checks = total_checks - paid_checks
        
        # Выручка
        revenue_cursor = checks_collection.aggregate([
            {"$match": {"paid": True}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ])
        revenue_data = list(revenue_cursor)
        total_revenue = revenue_data[0]['total'] if revenue_data else 0
        
        # Логи парсера
        parser_logs = list(
            parser_logs_collection.find()
            .sort('timestamp', -1)
            .limit(10)
        )
        
        for log in parser_logs:
            log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            log['_id'] = str(log['_id'])
        
        # Статистика телефонов
        total_phones = phones_collection.count_documents({})
        brands = phones_collection.distinct("brand")
        
        return render_template(
            'admin.html',
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
    """Управление ценами"""
    try:
        if request.method == 'POST':
            try:
                # ИСПРАВЛЕНИЕ: правильное преобразование данных формы
                paid_price = int(float(request.form.get('paid_price')) * 100)
                premium_price = int(float(request.form.get('premium_price')) * 100)
                
                current_doc = prices_collection.find_one({'type': 'current'})
                current_prices = current_doc['prices']
                
                prices_collection.insert_one({
                    'type': 'history',
                    'prices': current_prices,
                    'changed_at': datetime.utcnow(),
                    'changed_by': session.get('username', 'unknown')
                })
                
                prices_collection.update_one(
                    {'type': 'current'},
                    {'$set': {
                        'prices.paid': paid_price,
                        'prices.premium': premium_price,
                        'updated_at': datetime.utcnow()
                    }}
                )
                
                # Аудит изменения цен
                log_audit_event(
                    action='price_change',
                    details={
                        'old_prices': current_prices,
                        'new_prices': {
                            'paid': paid_price / 100,
                            'premium': premium_price / 100
                        }
                    },
                    user_id=session.get('user_id'),
                    username=session.get('username')
                )
                
                flash('Prices updated successfully!', 'success')
                return redirect(url_for('admin.price_management'))
                
            except Exception as e:
                flash(f'Error updating prices: {str(e)}', 'danger')
        
        # Получаем текущие цены
        current_prices_doc = prices_collection.find_one({'type': 'current'})
        current_prices = current_prices_doc['prices']
        formatted_prices = {
            'paid': current_prices['paid'] / 100,
            'premium': current_prices['premium'] / 100
        }
        
        # Получаем историю изменений цен
        price_history = list(prices_collection.find({'type': 'history'})
            .sort('changed_at', -1)
            .limit(5))
        
        for item in price_history:
            item['changed_at'] = item['changed_at'].strftime('%Y-%m-%d %H:%M')
            item['paid'] = item['prices']['paid'] / 100
            item['premium'] = item['prices']['premium'] / 100
        
        return render_template(
            'admin.html',
            current_prices=formatted_prices,
            price_history=price_history,
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
        
        total_checks = checks_collection.count_documents(query)
        checks = list(
            checks_collection.find(query)
            .sort('timestamp', -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        
        current_prices = get_current_prices()
        formatted_prices = {
            'paid': current_prices['paid'] / 100,
            'premium': current_prices['premium'] / 100
        }
        
        # Форматируем данные для отображения
        for check in checks:
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            if check.get('paid'):
                check['amount'] = f"${check.get('amount', 0):.2f}"
            else:
                check['amount'] = 'Free'
        
        return render_template(
            'admin.html',
            checks=checks,
            total_checks=total_checks,
            imei_query=imei_query,
            page=page,
            per_page=per_page,
            current_prices=formatted_prices,
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
        collections = db.list_collection_names()
        # Создаем словарь с количеством документов для каждой коллекции
        collection_counts = {}
        for name in collections:
            collection_counts[name] = db[name].count_documents({})
        
        return render_template(
            'admin.html',
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
            if doc_id:
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
        cursor = db[collection_name].find().skip(skip).limit(per_page)
        for doc in cursor:
            doc['_id'] = str(doc['_id'])  # Конвертируем ObjectId в строку
            documents.append(doc)
            
        total = db[collection_name].count_documents({})
        
        return render_template(
            'admin.html',
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
        doc = db[collection_name].find_one({'_id': ObjectId(doc_id)})
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
            'admin.html',
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
                result = db[collection_name].insert_one(form_data)
                flash(f'Document added successfully with ID: {result.inserted_id}', 'success')
                return redirect(url_for('admin.collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error adding document: {str(e)}', 'danger')
        
        return render_template(
            'admin.html',
            active_section='db_management',
            collection_name=collection_name
        )
    except Exception as e:
        current_app.logger.error(f"Add document error: {str(e)}")
        flash(f'Error loading form: {str(e)}', 'danger')
        return redirect(url_for('admin.collection_view', collection_name=collection_name))

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
                'created_at': datetime.utcnow()
            })
            flash('User created successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        
        users = list(admin_users_collection.find({}, {'password': 0}))
        for user in users:
            user['_id'] = str(user['_id'])
            user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin.html',
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
        current_username = session.get('username')
        user = admin_users_collection.find_one({'_id': ObjectId(user_id)})
        
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
        
        # Получение всех ключей
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
            'admin.html',
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
        
        # Получение всех вебхуков
        webhooks = list(webhooks_collection.find().sort('created_at', -1))
        
        # Преобразование данных
        for wh in webhooks:
            wh['_id'] = str(wh['_id'])
            wh['created_at'] = wh['created_at'].strftime('%Y-%m-%d %H:%M')
            if wh.get('last_delivery'):
                wh['last_delivery'] = wh['last_delivery'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin.html',
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
        # Получаем статус health check
        health_response = health_check()
        health_data = health_response[0].get_json()
        
        # Статистика использования
        stats = {
            'total_checks': checks_collection.count_documents({}),
            'active_webhooks': webhooks_collection.count_documents({'active': True}),
            'valid_api_keys': api_keys_collection.count_documents({'revoked': False}),
            'db_size': db.command('dbStats')['dataSize']
        }
        
        # Последние события аудита
        audit_events = list(audit_logs_collection.find()
            .sort('timestamp', -1)
            .limit(10))
        
        for event in audit_events:
            event['_id'] = str(event['_id'])
            event['timestamp'] = event['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin.html',
            active_section='system_status',
            health_data=health_data,
            system_stats=stats,
            audit_events=audit_events
        )
    except Exception as e:
        current_app.logger.error(f"System status error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
