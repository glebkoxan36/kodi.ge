from flask import render_template, current_app
from .bp import admin_bp
from .auth_decorators import admin_required
from db import (
    checks_collection, webhooks_collection, 
    api_keys_collection, audit_logs_collection, db, client
)

@admin_bp.route('/status')
@admin_required
def system_status():
    try:
        # Используем current_app для создания тестового клиента
        with current_app.test_client() as test_client:
            response = test_client.get('/health')
            health_data = response.get_json() or {}
        
        stats = {
            'total_checks': checks_collection.count_documents({}) if checks_collection else 0,
            'active_webhooks': webhooks_collection.count_documents({'active': True}) if webhooks_collection else 0,
            'valid_api_keys': api_keys_collection.count_documents({'revoked': False}) if api_keys_collection else 0,
            'db_size': db.command('dbStats')['dataSize'] if client else 0
        }
        
        audit_events = []
        if audit_logs_collection:
            audit_events = list(audit_logs_collection.find()
                .sort('timestamp', -1)
                .limit(10))
            
            for event in audit_events:
                event['_id'] = str(event['_id'])
                event['timestamp'] = event['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin/admin.html',
            active_section='system_status',
            health_data=health_data,
            system_stats=stats,
            audit_events=audit_events
        )
    except Exception as e:
        current_app.logger.error(f"System status error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
