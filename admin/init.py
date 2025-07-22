from flask import Blueprint
from .auth_decorators import login_required, admin_required
from .audit_log import log_audit_event

# Создаем Blueprint для админки с префиксом URL
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Импорт всех роутов ПОСЛЕ создания admin_bp
from . import dashboard
from . import price_management
from . import check_history
from . import db_management
from . import admin_users
from . import regular_users
from . import api_keys
from . import webhooks
from . import system_status
from . import user_switching
