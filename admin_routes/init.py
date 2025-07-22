from flask import Blueprint

# Создаем Blueprint для админки с префиксом URL
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Явно экспортируем admin_bp
__all__ = ['admin_bp']

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
