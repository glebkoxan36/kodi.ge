import os
import json
import requests
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, flash
from flask_cors import CORS
from pymongo import MongoClient
import stripe
from datetime import datetime
from functools import wraps
from bson import ObjectId

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

log_handler = RotatingFileHandler(
    'app.log', 
    maxBytes=1024 * 1024 * 5,
    backupCount=3
)
log_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(log_handler)

# Конфигурация
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
MONGODB_URI = os.getenv('MONGODB_URI')

# Данные для PHP API
API_URL = "https://api.ifreeicloud.co.uk"
API_KEY = os.getenv('API_KEY', '4KH-IFR-KW5-TSE-D7G-KWU-2SD-UCO')  # PHP API Key

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'securepassword')

# MongoDB
client = MongoClient(MONGODB_URI)
db = client['imei_checker']
checks_collection = db['results']
prices_collection = db['prices']
stats_collection = db['stats']

DEFAULT_PRICES = {
    'paid': 499,    # $4.99
    'premium': 999  # $9.99
}

DEFAULT_STATS = {
    'daily': 1248,
    'weekly': 8721,
    'monthly': 34215
}

# Initialize collections
if prices_collection.count_documents({'type': 'current'}) == 0:
    prices_collection.insert_one({
        'type': 'current',
        'prices': DEFAULT_PRICES,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    })

if stats_collection.count_documents({'type': 'current'}) == 0:
    stats_collection.insert_one({
        'type': 'current',
        'stats': DEFAULT_STATS,
        'updated_at': datetime.utcnow()
    })

# Типы сервисов
SERVICE_TYPES = {
    'free': 0,     # Бесплатная проверка
    'paid': 205,    # Платная проверка
    'premium': 242  # Премиум проверка
}

def get_current_prices():
    price_doc = prices_collection.find_one({'type': 'current'})
    if price_doc:
        return price_doc['prices']
    return DEFAULT_PRICES

def get_current_stats():
    stats_doc = stats_collection.find_one({'type': 'current'})
    if stats_doc:
        return stats_doc['stats']
    return DEFAULT_STATS

@app.route('/')
def index():
    prices = get_current_prices()
    return render_template('index.html', 
                         stripe_public_key=STRIPE_PUBLIC_KEY,
                         paid_price=prices['paid'] / 100,
                         premium_price=prices['premium'] / 100)

@app.route('/get_prices')
def get_prices_endpoint():
    prices = get_current_prices()
    return jsonify({
        'paid': prices['paid'] / 100,
        'premium': prices['premium'] / 100
    })

@app.route('/get_stats')
def get_stats():
    stats = get_current_stats()
    return jsonify(stats)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        imei = data.get('imei')
        service_type = data.get('service_type')
        
        if not validate_imei(imei):
            return jsonify({'error': 'Invalid IMEI'}), 400
        
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
        
        return jsonify({'id': session.id})
    
    except Exception as e:
        app.logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        return render_template('error.html', error="Session ID missing"), 400
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        imei = session.metadata.get('imei')
        service_type = session.metadata.get('service_type')
        
        if not imei or not service_type:
            return render_template('error.html', error="Invalid session data"), 400
        
        # Perform actual check
        result = perform_api_check(imei, service_type)
        
        if not result or 'error' in result:
            error_msg = result.get('error', 'No data available for this IMEI')
            return render_template('error.html', error=error_msg)
        
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
        
        # Update stats
        update_stats()
        
        return redirect(url_for('index', session_id=session_id))
    
    except Exception as e:
        app.logger.error(f"Payment success error: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/get_check_result')
def get_check_result():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    
    record = checks_collection.find_one({'stripe_session_id': session_id})
    if not record:
        return jsonify({'error': 'Result not found'}), 404
    
    return jsonify({
        'imei': record['imei'],
        'result': record['result']
    })

@app.route('/perform_check', methods=['POST'])
def perform_check():
    data = request.json
    imei = data.get('imei')
    service_type = data.get('service_type')
    
    if not imei or not service_type:
        return jsonify({'error': 'Missing parameters'}), 400
    
    if not validate_imei(imei):
        return jsonify({'error': 'Invalid IMEI format'}), 400
    
    try:
        result = perform_api_check(imei, service_type)
        
        if not result:
            return jsonify({'error': 'Empty response from API'}), 500
        
        if 'error' in result:
            return jsonify(result), 400
        
        if service_type == 'free':
            record = {
                'imei': imei,
                'service_type': service_type,
                'paid': False,
                'timestamp': datetime.utcnow(),
                'result': result
            }
            checks_collection.insert_one(record)
            update_stats()
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f'Check error: {str(e)}')
        return jsonify({'error': str(e)}), 500

def validate_imei(imei):
    return len(imei) == 15 and imei.isdigit()

def perform_api_check(imei, service_type):
    # Simulate API response
    models = ['iPhone 15 Pro Max', 'iPhone 14 Pro', 'iPhone 13', 'iPhone 12 mini']
    statuses = ['აქტიური', 'ქულდებაში', 'დაკარგული/მოპარული', 'გაუქმებული']
    carriers = ['Magti', 'Geocell', 'Beeline', 'Unlocked']
    countries = ['საქართველო', 'აშშ', 'გერმანია', 'გაერთიანებული სამეფო']
    
    return {
        'imei': imei,
        'model': models[0],
        'serial': 'C8P' + imei[-9:],
        'status': statuses[0],
        'fmi': 'ჩართულია',
        'blacklist': 'არ არის',
        'simlock': 'განბლოკილი',
        'warranty': 'მოქმედებს',
        'purchase_date': datetime.now().strftime('%d/%m/%Y'),
        'activation_status': 'აქტივირებული',
        'carrier': carriers[0],
        'country': countries[0]
    }

def update_stats():
    today = datetime.utcnow().date()
    stats_doc = stats_collection.find_one({'type': 'current'})
    
    if stats_doc:
        new_stats = {
            'daily': stats_doc['stats']['daily'] + 1,
            'weekly': stats_doc['stats']['weekly'] + 1,
            'monthly': stats_doc['stats']['monthly'] + 1
        }
        
        stats_collection.update_one(
            {'type': 'current'},
            {'$set': {'stats': new_stats, 'updated_at': datetime.utcnow()}}
        )

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Handle successful payment
    
    return jsonify({'status': 'success'})

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

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    try:
        if request.method == 'POST':
            try:
                paid_price = int(float(request.form.get('paid_price')) * 100)
                premium_price = int(float(request.form.get('premium_price')) * 100)
                
                current_doc = prices_collection.find_one({'type': 'current'})
                current_prices = current_doc['prices']
                
                prices_collection.insert_one({
                    'type': 'history',
                    'prices': current_prices,
                    'changed_at': datetime.utcnow(),
                    'changed_by': request.authorization.username
                })
                
                prices_collection.update_one(
                    {'type': 'current'},
                    {'$set': {
                        'prices.paid': paid_price,
                        'prices.premium': premium_price,
                        'updated_at': datetime.utcnow()
                    }}
                )
                
                flash('Prices updated successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                flash(f'Error updating prices: {str(e)}', 'danger')
        
        page = int(request.args.get('page', 1))
        per_page = 50
        
        imei_query = request.args.get('imei', '')
        query = {'imei': {'$regex': f'^{imei_query}'}} if imei_query else {}
        
        total_checks = checks_collection.count_documents({})
        paid_checks = checks_collection.count_documents({'paid': True})
        free_checks = total_checks - paid_checks
        
        checks = list(checks_collection.find(query)
            .sort('timestamp', -1)
            .skip((page - 1) * per_page)
            .limit(per_page))
        
        for check in checks:
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            if check.get('paid'):
                check['amount'] = f"${check.get('amount', 0):.2f}"
            else:
                check['amount'] = 'Free'
        
        current_prices = get_current_prices()
        
        revenue_cursor = checks_collection.aggregate([
            {"$match": {"paid": True}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ])
        revenue_data = list(revenue_cursor)
        total_revenue = revenue_data[0]['total'] if revenue_data else 0
        
        price_history = list(prices_collection.find({'type': 'history'})
            .sort('changed_at', -1)
            .limit(5))
        
        for item in price_history:
            item['changed_at'] = item['changed_at'].strftime('%Y-%m-%d %H:%M')
            item['paid'] = item['prices']['paid'] / 100
            item['premium'] = item['prices']['premium'] / 100
        
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
        app.logger.error(f"Admin dashboard error: {str(e)}")
        return render_template('error.html', error="Admin error"), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="Server error"), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
