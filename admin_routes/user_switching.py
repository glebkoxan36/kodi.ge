from flask import session, flash, redirect, url_for, current_app
from . import admin_bp
from .auth_decorators import login_required, admin_required
from bson import ObjectId
from db import regular_users_collection

@admin_bp.route('/switch-user/<user_id>', methods=['POST'])
@admin_required
def switch_user(user_id):
    try:
        admin_session = {
            'admin_id': session.get('admin_id'),
            'admin_role': session.get('admin_role'),
            'admin_username': session.get('admin_username')
        }
        
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        if user:
            session.pop('user_id', None)
            session.pop('role', None)
            
            session['user_id'] = str(user['_id'])
            session['role'] = user.get('role', 'user')
            session.permanent = True
            
            session['admin_id'] = admin_session['admin_id']
            session['admin_role'] = admin_session['admin_role']
            session['admin_username'] = admin_session['admin_username']
            
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
    try:
        admin_session = {
            'admin_id': session.get('admin_id'),
            'admin_role': session.get('admin_role'),
            'admin_username': session.get('admin_username')
        }
        
        session.clear()
        
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
