from datetime import datetime
from db import audit_logs_collection
from flask import current_app

def log_audit_event(action, details, user_id=None, username=None):
    try:
        event = {
            'action': action,
            'details': details,
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'username': username
        }
        audit_logs_collection.insert_one(event)
    except Exception as e:
        current_app.logger.error(f"Audit log error: {str(e)}")
