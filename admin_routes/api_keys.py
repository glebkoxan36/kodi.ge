from flask import render_template, request, flash, redirect, url_for
from .bp import admin_bp
from .auth_decorators import admin_required
from bson import ObjectId
from datetime import datetime, timedelta
import secrets
from db import api_keys_collection

@admin_bp.route('/api-keys', methods=['GET', 'POST'])
@admin_required
def manage_api_keys():
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            expires_in = int(request.form.get('expires_in', 365))
            permissions = request.form.getlist('permissions')
            
            if not name:
                flash('Name is required', 'danger')
                return redirect(url_for('admin.manage_api_keys'))
            
            key = secrets.token_urlsafe(32)
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(days=expires_in)
            
            api_keys_collection.insert_one({
                'name': name,
                'key': key,
                'permissions': permissions,
                'created_at': created_at,
                'expires_at': expires_at,
                'revoked': False
            })
            
            flash(f'API key created: {key}', 'success')
            return redirect(url_for('admin.manage_api_keys'))
        
        keys = list(api_keys_collection.find().sort('created_at', -1))
        for key in keys:
            key['_id'] = str(key['_id'])
            key['created_at'] = key['created_at'].strftime('%Y-%m-%d %H:%M')
            key['expires_at'] = key['expires_at'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/admin.html',
            active_section='api_keys',
            api_keys=keys
        )
    except Exception as e:
        current_app.logger.error(f"API keys management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/api-keys/revoke/<key_id>', methods=['POST'])
@admin_required
def revoke_api_key(key_id):
    try:
        api_keys_collection.update_one(
            {'_id': ObjectId(key_id)},
            {'$set': {'revoked': True}}
        )
        flash('API key revoked', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin.manage_api_keys'))

@admin_bp.route('/api-keys/delete/<key_id>', methods=['POST'])
@admin_required
def delete_api_key(key_id):
    try:
        api_keys_collection.delete_one({'_id': ObjectId(key_id)})
        flash('API key deleted', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin.manage_api_keys'))
