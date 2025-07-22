from flask import render_template, request, flash, redirect, url_for, session
from . import admin_bp
from .auth_decorators import admin_required
from db import (
    checks_collection, prices_collection, phonebase_collection,
    parser_logs_collection, audit_logs_collection
)
from price import get_current_prices, DEFAULT_PRICES
from datetime import datetime

@admin_bp.route('/dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    try:
        if request.method == 'POST' and 'run_parser' in request.form:
            flash('Parser functionality is not implemented', 'info')
            return redirect(url_for('admin.admin_dashboard'))
        
        # Статистика
        total_checks = checks_collection.count_documents({}) if checks_collection else 0
        paid_checks = checks_collection.count_documents({'paid': True}) if checks_collection else 0
        free_checks = total_checks - paid_checks
        
        # Выручка
        total_revenue = 0
        if checks_collection:
            revenue_cursor = checks_collection.aggregate([
                {"$match": {"paid": True}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ])
            revenue_data = list(revenue_cursor)
            total_revenue = revenue_data[0]['total'] if revenue_data else 0
        
        # Логи парсера
        parser_logs = []
        if parser_logs_collection:
            parser_logs = list(
                parser_logs_collection.find()
                .sort('timestamp', -1)
                .limit(10)
            )
            for log in parser_logs:
                log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                log['_id'] = str(log['_id'])
        
        # Статистика телефонов
        total_phones = phonebase_collection.count_documents({}) if phonebase_collection else 0
        brands = phonebase_collection.distinct("brand") if phonebase_collection else []
        
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
