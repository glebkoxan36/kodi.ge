from flask import render_template, request, flash, redirect, url_for, session, current_app
from .bp import admin_bp
from .auth_decorators import admin_required
from .audit_log import log_audit_event
from bson import ObjectId
import re
from db import (
    regular_users_collection, checks_collection, 
    payments_collection, phonebase_collection
)
from datetime import datetime

@admin_bp.route('/users/regular', methods=['GET'])
@admin_required
def manage_regular_users():
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
            'admin/admin.html',
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
    try:
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin.manage_regular_users'))
        
        user['_id'] = str(user['_id'])
        user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
        if 'birth_date' in user:
            user['birth_date'] = user['birth_date'].strftime('%Y-%m-%d')
        
        checks = list(checks_collection.find({'user_id': ObjectId(user_id)})
            .sort('timestamp', -1)
            .limit(10))
        for check in checks:
            check['_id'] = str(check['_id'])
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        payments = list(payments_collection.find({'user_id': ObjectId(user_id)})
            .sort('timestamp', -1)
            .limit(10))
        for payment in payments:
            payment['_id'] = str(payment['_id'])
            payment['timestamp'] = payment['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/admin.html',
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
    try:
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin.manage_regular_users'))
        
        if request.method == 'POST':
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            username = request.form.get('username')
            phone = request.form.get('phone')
            balance = float(request.form.get('balance', 0))
            is_blocked = request.form.get('is_blocked') == 'on'
            role = request.form.get('role', 'user')

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

            regular_users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )

            flash('User updated successfully', 'success')
            return redirect(url_for('admin.view_regular_user', user_id=user_id))

        user['_id'] = str(user['_id'])
        if 'birth_date' in user:
            user['birth_date'] = user['birth_date'].strftime('%Y-%m-%d')

        return render_template(
            'admin/admin.html',
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
        
        regular_users_collection.update_one(
            {'_id': ObjectId(user_id)},
            update
        )
        
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
