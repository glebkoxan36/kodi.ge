from functools import wraps
from flask import session, redirect, url_for, request, current_app

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session and 'admin_id' not in session:
            current_app.logger.warning("Unauthorized access attempt")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session or 'admin_role' not in session:
            current_app.logger.warning("Unauthorized admin access attempt")
            return redirect(url_for('auth.admin_login', next=request.url))
        
        from bson import ObjectId
        from db import admin_users_collection
        
        try:
            admin = admin_users_collection.find_one({'_id': ObjectId(session['admin_id'])})
            if not admin or admin.get('role') not in ['admin', 'superadmin']:
                from flask import flash
                flash('Administrator account not found or invalid', 'danger')
                session.clear()
                return redirect(url_for('auth.admin_login'))
        except:
            session.clear()
            return redirect(url_for('auth.admin_login'))
            
        return f(*args, **kwargs)
    return decorated
