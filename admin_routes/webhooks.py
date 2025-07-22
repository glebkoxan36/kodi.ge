from flask import render_template, request, flash, redirect, url_for, current_app
from . import admin_bp
from .auth_decorators import admin_required
from bson import ObjectId
from datetime import datetime
from db import webhooks_collection

@admin_bp.route('/webhooks', methods=['GET', 'POST'])
@admin_required
def manage_webhooks():
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
        
        webhooks = []
        if webhooks_collection:
            webhooks = list(webhooks_collection.find().sort('created_at', -1))
        
        for wh in webhooks:
            wh['_id'] = str(wh['_id'])
            wh['created_at'] = wh['created_at'].strftime('%Y-%m-%d %H:%M')
            if wh.get('last_delivery'):
                wh['last_delivery'] = wh['last_delivery'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/admin.html',
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
    try:
        result = webhooks_collection.delete_one({'_id': ObjectId(webhook_id)})
        if result.deleted_count > 0:
            flash('Webhook deleted successfully', 'success')
        else:
            flash('Webhook not found', 'warning')
    except Exception as e:
        flash(f'Error deleting webhook: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_webhooks'))
