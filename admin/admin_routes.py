import os
import re
import json
import logging
import threading
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, flash, session, jsonify, current_app
)
from bson import ObjectId
from pymongo import MongoClient

# Создаем блюпринт для админки
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ======================================
# Вспомогательные функции
# ======================================

def get_current_prices():
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['imei_checker']
    prices_collection = db['prices']
    
    DEFAULT_PRICES = {
        'paid': 499,    # $4.99
        'premium': 999  # $9.99
    }
    
    price_doc = prices_collection.find_one({'type': 'current'})
    if price_doc:
        return price_doc['prices']
    return DEFAULT_PRICES

def log_audit_event(action, details, user_id=None, username=None):
    """Логирование действий администратора"""
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['imei_checker']
    audit_logs_collection = db['audit_logs']
    
    event = {
        'action': action,
        'details': details,
        'user_id': user_id,
        'username': username,
        'timestamp': datetime.utcnow(),
        'ip_address': request.remote_addr
    }
    audit_logs_collection.insert_one(event)

# ======================================
# Декораторы
# ======================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or session['role'] not in ['admin', 'superadmin']:
            # Добавляем параметр next с текущим URL
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# ======================================
# Маршруты админки
# ======================================

@admin_bp.route('/price', methods=['GET', 'POST'])
@admin_required
def price_management():
    """Управление ценами"""
    try:
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client['imei_checker']
        prices_collection = db['prices']
        
        if request.method == 'POST':
            try:
                # Преобразование данных формы
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
            'admin/admin.html',
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
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client['imei_checker']
        checks_collection = db['results']
        
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
            'admin/admin.html',
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

@admin_bp.route('', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    """Главная панель администратора"""
    try:
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client['imei_checker']
        checks_collection = db['results']
        parser_logs_collection = db['parser_logs']
        phones_collection = db['phones']
        
        if request.method == 'POST' and 'run_parser' in request.form:
            try:
                from gsm_parser.scrap_specs import main as run_gsm_parser
                thread = threading.Thread(target=run_gsm_parser, args=(os.getenv('MONGODB_URI'),))
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
            'admin/admin.html',
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
