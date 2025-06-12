import os
import json
import requests
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, flash
from pymongo import MongoClient
import stripe
from datetime import datetime
from flask_caching import Cache
from functools import wraps
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Конфигурация кэширования
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Настройка расширенного логирования
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Создаем обработчик для ротации логов
log_handler = RotatingFileHandler(
    'app.log', 
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=3
)
log_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(log_handler)

# Конфигурация из переменных окружения
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
MONGODB_URI = os.getenv('MONGODB_URI')
API_KEY = os.getenv('API_KEY')

# Конфигурация админ-панели
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'securepassword')

# Конфигурация MongoDB
client = MongoClient(MONGODB_URI)
db = client['imei_checker']
checks_collection = db['results']
prices_collection = db['prices']

# Инициализация цен по умолчанию
DEFAULT_PRICES = {
    'paid': 499,    # $4.99
    'premium': 999  # $9.99
}

# Убедимся, что цены инициализированы в базе
if prices_collection.count_documents({'type': 'current'}) == 0:
    prices_collection.insert_one({
        'type': 'current',
        'prices': DEFAULT_PRICES,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    })

# Конфигурация API проверки
API_URL = "https://api.ifreeicloud.co.uk"
SERVICE_TYPES = {
    'free': 0,
    'paid': 4,
    'premium': 205
}

# Функция для получения текущих цен
def get_current_prices():
    price_doc = prices_collection.find_one({'type': 'current'})
    if price_doc:
        return price_doc['prices']
    return DEFAULT_PRICES

# Главная страница с кэшированием на 1 час
@app.route('/')
@cache.cached(timeout=3600)
def index():
    app.logger.info('Serving index page')
    prices = get_current_prices()
    return render_template('index.html', 
                           stripe_public_key=STRIPE_PUBLIC_KEY,
                           paid_price=prices['paid'] / 100,
                           premium_price=prices['premium'] / 100)

# Создание сессии оплаты
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        imei = data.get('imei')
        service_type = data.get('service_type')
        
        if not validate_imei(imei):
            app.logger.warning(f'Invalid IMEI format: {imei}')
            return jsonify({'error': 'Invalid IMEI'}), 400
        
        app.logger.info(f'Creating checkout session for IMEI: {imei}, service: {service_type}')
        
        # Получаем актуальные цены
        prices = get_current_prices()
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'iPhone Check ({service_type.capitalize()})',
                    },
                    'unit_amount': prices[service_type],
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={
                'imei': imei,
                'service_type': service_type
            },
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('index', _external=True),
        )
        
        app.logger.info(f'Checkout session created: {session.id}')
        return jsonify({'id': session.id})
    
    except Exception as e:
        app.logger.error(f'Stripe session creation error: {str(e)}')
        return jsonify({'error': str(e)}), 500

# Успешная оплата
@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        app.logger.warning('Payment success accessed without session_id')
        return render_template('error.html', error="Session ID missing"), 400
    
    try:
        app.logger.info(f'Processing payment success for session: {session_id}')
        session = stripe.checkout.Session.retrieve(session_id)
        imei = session.metadata.get('imei')
        service_type = session.metadata.get('service_type')
        
        if not imei or not service_type:
            app.logger.error(f'Invalid session data for session: {session_id}')
            return render_template('error.html', error="Invalid session data"), 400
        
        # Проверка IMEI через API
        result = perform_api_check(imei, service_type)
        
        # Сохранение в базу данных
        record = {
            'stripe_session_id': session_id,
            'imei': imei,
            'service_type': service_type,
            'paid': True,
            'payment_status': session.payment_status,
            'amount': session.amount_total / 100,
            'currency': session.currency,
            'timestamp': datetime.utcnow(),
            'result': result
        }
        checks_collection.insert_one(record)
        
        app.logger.info(f'Payment processed successfully for IMEI: {imei}')
        return render_template('result.html', result=result, imei=imei)
    
    except Exception as e:
        app.logger.error(f'Payment processing error: {str(e)}')
        return render_template('error.html', error=str(e)), 500

# Выполнение проверки IMEI с кэшированием
@app.route('/perform_check')
@cache.cached(timeout=600, query_string=True)  # Кэш на 10 минут
def perform_check():
    imei = request.args.get('imei')
    service_type = request.args.get('service_type')
    
    if not validate_imei(imei):
        app.logger.warning(f'Invalid IMEI format in perform_check: {imei}')
        return render_template('error.html', error="Invalid IMEI format"), 400
    
    try:
        app.logger.info(f'Performing API check for IMEI: {imei}, service: {service_type}')
        result = perform_api_check(imei, service_type)
        
        # Сохранение в базу данных только для бесплатных проверок
        if service_type == 'free':
            record = {
                'imei': imei,
                'service_type': service_type,
                'paid': False,
                'timestamp': datetime.utcnow(),
                'result': result
            }
            checks_collection.insert_one(record)
        
        return render_template('result.html', result=result, imei=imei)
    
    except Exception as e:
        app.logger.error(f'API check error: {str(e)}')
        return render_template('error.html', error=str(e)), 500

# Вебхук Stripe
@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        app.logger.info(f'Stripe webhook received: {event["type"]}')
    except ValueError as e:
        app.logger.error(f'Invalid payload in webhook: {str(e)}')
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        app.logger.error(f'Invalid signature in webhook: {str(e)}')
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        app.logger.info(f"Payment succeeded: {session['id']}")
    
    return jsonify({'status': 'success'})

# Функция валидации IMEI
def validate_imei(imei):
    return len(imei) == 15 and imei.isdigit()

# Функция выполнения API проверки
def perform_api_check(imei, service_type):
    service_code = SERVICE_TYPES.get(service_type, 0)
    data = {
        "service": service_code,
        "imei": imei,
        "key": API_KEY
    }
    
    try:
        app.logger.debug(f'Sending API request for IMEI: {imei}')
        response = requests.post(API_URL, data=data, timeout=30)
        
        if response.status_code != 200:
            error_msg = f"API Error: {response.status_code}"
            app.logger.error(error_msg)
            return {'error': error_msg}
        
        result = response.json()
        app.logger.debug(f'API response received for IMEI: {imei}')
        return result
    
    except Exception as e:
        error_msg = f"Service error: {str(e)}"
        app.logger.error(error_msg)
        return {'error': error_msg}

# Базовый мидлвейр для аутентификации
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD):
            return Response(
                'Please enter valid admin credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

# Панель администратора
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    try:
        # Обработка изменения цен
        if request.method == 'POST':
            try:
                paid_price = int(float(request.form.get('paid_price')) * 100)
                premium_price = int(float(request.form.get('premium_price')) * 100)
                
                # Получаем текущие цены
                current_doc = prices_collection.find_one({'type': 'current'})
                current_prices = current_doc['prices']
                
                # Сохраняем текущие цены в историю
                prices_collection.insert_one({
                    'type': 'history',
                    'prices': current_prices,
                    'changed_at': datetime.utcnow(),
                    'changed_by': request.authorization.username
                })
                
                # Обновляем текущие цены
                prices_collection.update_one(
                    {'type': 'current'},
                    {'$set': {
                        'prices.paid': paid_price,
                        'prices.premium': premium_price,
                        'updated_at': datetime.utcnow()
                    }}
                )
                
                # Логируем изменение
                app.logger.info(f"Prices updated by {request.authorization.username}: paid={paid_price}, premium={premium_price}")
                flash('Prices updated successfully!', 'success')
                
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                app.logger.error(f'Price update error: {str(e)}')
                flash(f'Error updating prices: {str(e)}', 'danger')
        
        # Параметры пагинации
        page = int(request.args.get('page', 1))
        per_page = 50
        
        # Поиск по IMEI если указан
        imei_query = request.args.get('imei', '')
        query = {'imei': {'$regex': f'^{imei_query}'}} if imei_query else {}
        
        # Статистика
        total_checks = checks_collection.count_documents({})
        paid_checks = checks_collection.count_documents({'paid': True})
        free_checks = total_checks - paid_checks
        
        # Получение данных с пагинацией
        checks = list(checks_collection.find(query)
            .sort('timestamp', -1)
            .skip((page - 1) * per_page)
            .limit(per_page))
        
        # Форматирование данных для отображения
        for check in checks:
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            if check.get('paid'):
                check['amount'] = f"${check.get('amount', 0):.2f}"
            else:
                check['amount'] = 'Free'
        
        # Получаем текущие цены
        current_prices = get_current_prices()
        
        # Рассчитываем общую выручку
        revenue_cursor = checks_collection.aggregate([
            {"$match": {"paid": True}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ])
        revenue_data = list(revenue_cursor)
        total_revenue = revenue_data[0]['total'] if revenue_data else 0
        
        # Получаем историю цен (последние 5 записей)
        price_history = list(prices_collection.find({'type': 'history'})
            .sort('changed_at', -1)
            .limit(5))
        
        # Форматируем историю цен
        for item in price_history:
            item['changed_at'] = item['changed_at'].strftime('%Y-%m-%d %H:%M')
            item['paid'] = item['prices']['paid'] / 100
            item['premium'] = item['prices']['premium'] / 100
        
        # Форматируем текущие цены для формы
        formatted_prices = {
            'paid': current_prices['paid'] / 100,
            'premium': current_prices['premium'] / 100
        }
        
        return render_template(
            'admin.html',
            checks=checks,
            total_checks=total_checks,
            paid_checks=paid_checks,
            free_checks=free_checks,
            total_revenue=total_revenue,
            imei_query=imei_query,
            page=page,
            per_page=per_page,
            current_prices=formatted_prices,
            price_history=price_history
        )
    except Exception as e:
        app.logger.error(f'Admin dashboard error: {str(e)}')
        return render_template('error.html', error="Admin error"), 500

# Обработка ошибок
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f'Page not found: {request.url}')
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f'Internal server error: {str(e)}')
    return render_template('error.html', error="Server error"), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f'Starting server on port {port}')
    app.run(host='0.0.0.0', port=port)
