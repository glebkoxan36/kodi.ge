from flask import render_template, request, flash, redirect, url_for, session, current_app
from . import admin_bp
from .auth_decorators import admin_required
from bson import ObjectId
from werkzeug.security import generate_password_hash
from db import admin_users_collection
from datetime import datetime

@admin_bp.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
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
            'admin/admin.html',
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
    try:
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
