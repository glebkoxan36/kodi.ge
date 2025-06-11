import os
import json
import requests
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from urllib.parse import quote_plus
import stripe
from datetime import datetime

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Конфигурация из переменных окружения
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
MONGODB_URI = os.getenv('MONGODB_URI')
API_KEY = os.getenv('API_KEY')

# Конфигурация MongoDB
client = MongoClient(MONGODB_URI)
db = client['imei_checker']  # Явное указание базы данных
checks_collection = db['results']

# Конфигурация API проверки
API_URL = "https://api.ifreeicloud.co.uk"
SERVICE_TYPES = {
    'free': 0,
    'paid': 4,
    'premium': 205
}
PRICES = {
    'paid': 499,    # $4.99
    'premium': 999  # $9.99
}

@app.route('/')
def index():
    return render_template('index.html', stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.json
    imei = data.get('imei')
    service_type = data.get('service_type')
    
    if not validate_imei(imei):
        return jsonify({'error': 'Invalid IMEI'}), 400
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'iPhone Check ({service_type.capitalize()})',
                    },
                    'unit_amount': PRICES[service_type],
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
        app.logger.error(f"Stripe error: {str(e)}")
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
        
        result = perform_api_check(imei, service_type)
        
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
        
        return render_template('result.html', result=result, imei=imei)
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/perform_check')
def perform_check():
    imei = request.args.get('imei')
    service_type = request.args.get('service_type')
    
    if not validate_imei(imei):
        return render_template('error.html', error="Invalid IMEI format"), 400
    
    result = perform_api_check(imei, service_type)
    return render_template('result.html', result=result, imei=imei)

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
        app.logger.info(f"Payment succeeded: {session['id']}")
    
    return jsonify({'status': 'success'})

def validate_imei(imei):
    return len(imei) == 15 and imei.isdigit()

def perform_api_check(imei, service_type):
    service_code = SERVICE_TYPES.get(service_type, 0)
    data = {
        "service": service_code,
        "imei": imei,
        "key": API_KEY
    }
    
    try:
        response = requests.post(API_URL, data=data, timeout=30)
        if response.status_code != 200:
            return {'error': f"API Error: {response.status_code}"}
        return response.json()
    except Exception as e:
        return {'error': str(e)}

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="Server error"), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
