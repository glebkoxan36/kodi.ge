import os
import json
import requests
import logging
import threading
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, flash
from flask_cors import CORS
from pymongo import MongoClient
import stripe
from datetime import datetime
from functools import wraps
from bs4 import BeautifulSoup
import re
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

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
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')  # DeepSeek API Key

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'securepassword'))

# MongoDB
client = MongoClient(MONGODB_URI)
db = client['imei_checker']
checks_collection = db['results']
prices_collection = db['prices']
comparisons_collection = db['comparisons']
phones_collection = db['phones']
parser_logs_collection = db['parser_logs']
users_collection = db['admin_users']

# Создаем администратора по умолчанию, если не существует
if not users_collection.find_one({'username': ADMIN_USERNAME}):
    users_collection.insert_one({
        'username': ADMIN_USERNAME,
        'password': ADMIN_PASSWORD,
        'role': 'superadmin',
        'created_at': datetime.utcnow()
    })

# ИСПРАВЛЕНИЕ: Проверка существующих индексов перед созданием
try:
    # Проверяем существование текстового индекса
    existing_indexes = phones_collection.index_information()
    text_index_exists = any(
        'text' in index['key'].values() 
        for index in existing_indexes.values()
    )
    
    # Создаем индекс только если его еще нет
    if not text_index_exists:
        phones_collection.create_index([
            ('brand', 'text'), 
            ('model', 'text'), 
            ('Name', 'text')
        ])
except Exception as e:
    app.logger.error(f"Index creation error: {str(e)}")

DEFAULT_PRICES = {
    'paid': 499,    # $4.99
    'premium': 999  # $9.99
}

if prices_collection.count_documents({'type': 'current'}) == 0:
    prices_collection.insert_one({
        'type': 'current',
        'prices': DEFAULT_PRICES,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    })

# Типы сервисов
SERVICE_TYPES = {
    'free': 0,
    'paid': 205,
    'premium': 242
}

def get_current_prices():
    price_doc = prices_collection.find_one({'type': 'current'})
    if price_doc:
        return price_doc['prices']
    return DEFAULT_PRICES

@app.route('/')
def index():
    prices = get_current_prices()
    return render_template('index.html', 
                         stripe_public_key=STRIPE_PUBLIC_KEY,
                         paid_price=prices['paid'] / 100,
                         premium_price=prices['premium'] / 100)

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
        
        result = perform_api_check(imei, service_type)
        
        if not result or 'error' in result:
            error_msg = result.get('error', 'No data available for this IMEI')
            return render_template('error.html', error=error_msg)
        
        # Для бесплатных проверок обрабатываем HTML
        if service_type == 'free' and 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            if parsed_data:
                result = parsed_data
            else:
                result = {'error': 'Failed to parse HTML response'}
        
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
    data = request.get_json()
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
        
        # Для бесплатных проверок обрабатываем HTML
        if service_type == 'free' and 'html_content' in result:
            parsed_data = parse_free_html(result['html_content'])
            if parsed_data:
                result = parsed_data
            else:
                result = {'error': 'Failed to parse HTML response'}
        
        if service_type == 'free':
            record = {
                'imei': imei,
                'service_type': service_type,
                'paid': False,
                'timestamp': datetime.utcnow(),
                'result': result
            }
            checks_collection.insert_one(record)
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f'Check error: {str(e)}')
        return jsonify({'error': str(e)}), 500

def validate_imei(imei):
    return len(imei) == 15 and imei.isdigit()

def perform_api_check(imei, service_type):
    data = {
        "service": SERVICE_TYPES[service_type],
        "imei": imei,
        "key": API_KEY
    }
    
    try:
        app.logger.info(f"Sending API request to {API_URL} with data: {data}")
        response = requests.post(API_URL, data=data, timeout=60)
        
        if response.status_code != 200:
            return {'error': f'API returned HTTP code {response.status_code}'}
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON response from API'}
        
        if not result.get('success', False):
            return {'error': result.get('error', 'Unknown API error')}
        
        if service_type == 'free':
            return {
                'html_content': result.get('response', ''),
                'raw_response': response.text
            }
        else:
            return result.get('object', {})
    
    except requests.exceptions.RequestException as e:
        return {'error': f"Request error: {str(e)}"}
    except Exception as e:
        return {'error': f"Service error: {str(e)}"}

def parse_free_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {}
        
        # Поиск в таблицах
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(':', '').replace(' ', '_').lower()
                    value = cols[1].get_text(strip=True)
                    result[key] = value
        
        # Поиск по меткам в других структурах
        labels = [
            "Device", "Model", "Serial", "IMEI", "ICCID", 
            "FMI", "Activation Status", "Blacklist Status"
        ]
        
        for label in labels:
            # Поиск элемента с текстом метки
            element = soup.find(string=re.compile(rf'{label}.*', re.IGNORECASE))
            if not element:
                continue
                
            # Поиск значения
            value_element = None
            
            # Вариант 1: значение в соседнем элементе
            if element.parent and element.parent.find_next_sibling():
                value_element = element.parent.find_next_sibling()
            
            # Вариант 2: значение в том же элементе после <br>
            if not value_element and element.parent and element.parent.find('br'):
                value_element = element.parent
                
            # Вариант 3: значение после двоеточия в том же элементе
            if not value_element and ':' in element:
                value_element = element.split(':', 1)[-1].strip()
            
            if value_element:
                if isinstance(value_element, str):
                    value = value_element
                else:
                    value = value_element.get_text(strip=True)
                
                # Очистка значения от лишних символов
                value = re.sub(r'[^a-zA-Z0-9\s]', '', value).strip()
                if value:
                    result[label.replace(" ", "_").lower()] = value
        
        return result
    
    except Exception as e:
        app.logger.error(f"HTML parsing error: {str(e)}")
        app.logger.error(f"HTML content: {html_content[:500]}")  # Логируем часть HTML для отладки
        return None

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
        # Обработка успешного платежа
    
    return jsonify({'status': 'success'})

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return auth_required()
        
        user = users_collection.find_one({'username': auth.username})
        if not user or not check_password_hash(user['password'], auth.password):
            return auth_required()
            
        return f(*args, **kwargs)
    return decorated

def auth_required():
    return Response(
        'Please enter valid admin credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        'error.html', 
        code=404,
        message="გვერდი ვერ მოიძებნა"
    ), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        'error.html', 
        code=500,
        message="სერვერზე შეცდომა მოხდა"
    ), 500
    
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    try:
        if request.method == 'POST':
            # Обработка обновления цен
            if 'paid_price' in request.form:
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
            
            # Обработка запуска парсера
            elif 'run_parser' in request.form:
                try:
                    from gsm_parser.scrap_specs import main as run_gsm_parser
                    # Запуск парсера в фоновом режиме
                    thread = threading.Thread(target=run_gsm_parser, args=(MONGODB_URI,))
                    thread.start()
                    flash('Parser started in background', 'success')
                except Exception as e:
                    app.logger.error(f"Parser error: {str(e)}")
                    flash(f'Error starting parser: {str(e)}', 'danger')
                return redirect(url_for('admin_dashboard'))
        
        page = int(request.args.get('page', 1))
        per_page = 50
        
        imei_query = request.args.get('imei', '')
        query = {'imei': {'$regex': f'^{imei_query}'}} if imei_query else {}
        
        total_checks = checks_collection.count_documents({})
        paid_checks = checks_collection.count_documents({'paid': True})
        free_checks = total_checks - paid_checks
        
        # ИСПРАВЛЕНО: Правильные отступы для цепочки вызовов
        checks = list(
            checks_collection.find(query)
            .sort('timestamp', -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        
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
        
        # ИСПРАВЛЕНО: Правильные отступы для цепочки вызовов
        parser_logs = list(
            parser_logs_collection.find()
            .sort('timestamp', -1)
            .limit(10)
        )
        
        for log in parser_logs:
            log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            log['_id'] = str(log['_id'])
        
        # Статистика телефонов
        total_phones = phones_collection.count_documents({})
        brands = phones_collection.distinct("brand")
        
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
            price_history=price_history,
            parser_logs=parser_logs,
            total_phones=total_phones,
            brands=brands,
            db_management_section=False
        )
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {str(e)}")
        return render_template('error.html', error="Admin error"), 500

# Обновленный маршрут для поиска телефонов
@app.route('/api/search', methods=['GET'])
def search_phones():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    # Поиск по нескольким полям с проекцией только нужных полей
    regex_query = {'$regex': f'.*{re.escape(query)}.*', '$options': 'i'}
    results = list(phones_collection.find({
        '$or': [
            {'brand': regex_query},
            {'model': regex_query},
            {'Name': regex_query}
        ]
    }, {
        '_id': 1,
        'Name': 1,
        'Image_URL': 1
    }).limit(10))
    
    # Преобразование ObjectId в строки и нормализация данных
    normalized_results = []
    for phone in results:
        normalized_results.append({
            '_id': str(phone['_id']),
            'name': phone.get('Name', 'Unknown Phone'),
            'image_url': phone.get('Image_URL', '')
        })
    
    return jsonify(normalized_results)

# Обновленный маршрут для получения деталей телефона
@app.route('/api/phone_details/<phone_id>', methods=['GET'])
def phone_details(phone_id):
    try:
        phone = phones_collection.find_one({'_id': ObjectId(phone_id)})
        if not phone:
            return jsonify({'error': 'Phone not found'}), 404
        
        # Нормализуем данные для фронтенда
        normalized_phone = {
            '_id': str(phone['_id']),
            'name': phone.get('Name', 'Unknown Phone'),
            'image_url': phone.get('Image_URL', ''),
            'specs': {key: value for key, value in phone.items() 
                     if key not in ['_id', 'Name', 'Image_URL']}
        }
        
        return jsonify(normalized_phone)
    except Exception as e:
        return jsonify({'error': 'Invalid phone ID'}), 400

# Обновленный маршрут для AI анализа
@app.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    data = request.json
    phone1 = data.get('phone1')
    phone2 = data.get('phone2')
    
    if not phone1 or not phone2:
        return jsonify({'error': 'Both phones are required'}), 400
    
    try:
        # Подготовка промпта для AI
        phone1_name = phone1.get('name', 'Unknown')
        phone2_name = phone2.get('name', 'Unknown')
        
        # Собираем все характеристики телефонов
        phone1_specs = "\n".join([f"{key}: {value}" for key, value in phone1.get('specs', {}).items()])
        phone2_specs = "\n".join([f"{key}: {value}" for key, value in phone2.get('specs', {}).items()])
        
        prompt = f"""
            გთხოვთ, შეადაროთ ორი სმარტფონი: {phone1_name} და {phone2_name}.
            
            პირველი ტელეფონის მონაცემები:
            {phone1_specs}
            
            მეორე ტელეფონის მონაცემები:
            {phone2_specs}
            
            გაანალიზეთ შემდეგი კატეგორიები:
            - შესრულება (პროცესორი, RAM, GPU)
            - დისპლეი (ზომა, გაფართოება, ტექნოლოგია)
            - კამერები (მთავარი, ფრონტალური, ფუნქციები)
            - ბატარეის ხანგრძლივობა
            - დიზაინი და აშენების ხარისხი
            - დამატებითი ფუნქციები
            - ფასი და ღირებულება
            
            გთხოვთ, მოგვაწოდოთ დეტალური ანალიზი ქართულ ენაზე და გამოავლინოთ რომელი ტელეფონია უკეთესი თითოეულ კატეგორიაში.
            დასასრულს, გამოაცხადეთ საერთო გამარჯვებული და ახსენით თქვენი არჩევანი.
        """
        
        # Вызов DeepSeek API
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
        response.raise_for_status()
        
        ai_response = response.json()
        content = ai_response['choices'][0]['message']['content']
        
        # Сохранение сравнения в БД
        comparison_record = {
            'phone1': phone1_name,
            'phone2': phone2_name,
            'timestamp': datetime.utcnow(),
            'ai_response': content
        }
        comparisons_collection.insert_one(comparison_record)
        
        return jsonify({'analysis': content})
    
    except requests.exceptions.RequestException as e:
        app.logger.error(f"DeepSeek API error: {str(e)}")
        return jsonify({'error': 'AI service unavailable'}), 500
    except Exception as e:
        app.logger.error(f"AI analysis error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Новый маршрут для сравнения телефонов
@app.route('/compare')
def compare_phones():
    return render_template('compare.html')

# ======================================
# Визуальное управление MongoDB
# ======================================

@app.route('/admin/db')
@admin_required
def db_management():
    """Главная страница управления БД"""
    try:
        collections = db.list_collection_names()
        return render_template(
            'admin.html',
            db_management_section=True,
            db_content='db_management',
            collections=collections
        )
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/db/<collection_name>', methods=['GET', 'POST'])
@admin_required
def collection_view(collection_name):
    """Просмотр и управление коллекцией"""
    try:
        # Обработка удаления документов
        if request.method == 'POST':
            doc_id = request.form.get('doc_id')
            if doc_id:
                try:
                    db[collection_name].delete_one({'_id': ObjectId(doc_id)})
                    flash('Document deleted successfully', 'success')
                except Exception as e:
                    flash(f'Error deleting document: {str(e)}', 'danger')
            return redirect(url_for('collection_view', collection_name=collection_name))
        
        # Пагинация
        page = int(request.args.get('page', 1))
        per_page = 20
        skip = (page - 1) * per_page
        
        # Получение документов
        documents = list(db[collection_name].find().skip(skip).limit(per_page))
        total = db[collection_name].count_documents({})
        
        # Преобразование ObjectId
        for doc in documents:
            doc['_id'] = str(doc['_id'])
        
        return render_template(
            'admin.html',
            db_management_section=True,
            db_content='collection_view',
            collection_name=collection_name,
            documents=documents,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        app.logger.error(f"Collection view error: {str(e)}")
        flash(f'Error loading collection: {str(e)}', 'danger')
        return redirect(url_for('db_management'))

@app.route('/admin/db/<collection_name>/edit/<doc_id>', methods=['GET', 'POST'])
@admin_required
def edit_document(collection_name, doc_id):
    """Редактирование документа"""
    try:
        doc = db[collection_name].find_one({'_id': ObjectId(doc_id)})
        if not doc:
            flash('Document not found', 'danger')
            return redirect(url_for('collection_view', collection_name=collection_name))
        
        if request.method == 'POST':
            try:
                # Собираем данные формы
                form_data = {}
                for key, value in request.form.items():
                    if key.startswith('field_'):
                        field_name = key[6:]
                        form_data[field_name] = value
                
                # Обновление документа
                db[collection_name].update_one(
                    {'_id': ObjectId(doc_id)},
                    {'$set': form_data}
                )
                flash('Document updated successfully', 'success')
                return redirect(url_for('collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error updating document: {str(e)}', 'danger')
        
        # Преобразование ObjectId для отображения
        doc['_id'] = str(doc['_id'])
        
        return render_template(
            'admin.html',
            db_management_section=True,
            db_content='edit_document',
            collection_name=collection_name,
            doc_id=doc_id,
            document=doc
        )
    except Exception as e:
        app.logger.error(f"Edit document error: {str(e)}")
        flash(f'Error loading document: {str(e)}', 'danger')
        return redirect(url_for('collection_view', collection_name=collection_name))

@app.route('/admin/db/<collection_name>/add', methods=['GET', 'POST'])
@admin_required
def add_document(collection_name):
    """Добавление нового документа"""
    try:
        if request.method == 'POST':
            try:
                # Собираем данные формы
                form_data = {}
                for key, value in request.form.items():
                    if key.startswith('field_'):
                        field_name = key[6:]
                        form_data[field_name] = value
                
                # Вставка нового документа
                result = db[collection_name].insert_one(form_data)
                flash(f'Document added successfully with ID: {result.inserted_id}', 'success')
                return redirect(url_for('collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error adding document: {str(e)}', 'danger')
        
        return render_template(
            'admin.html',
            db_management_section=True,
            db_content='add_document',
            collection_name=collection_name
        )
    except Exception as e:
        app.logger.error(f"Add document error: {str(e)}")
        flash(f'Error loading form: {str(e)}', 'danger')
        return redirect(url_for('collection_view', collection_name=collection_name))

# ======================================
# Управление администраторами
# ======================================

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    """Управление пользователями админки"""
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role', 'admin')
            
            if not username or not password:
                flash('Username and password are required', 'danger')
                return redirect(url_for('manage_users'))
            
            if users_collection.find_one({'username': username}):
                flash('User already exists', 'danger')
                return redirect(url_for('manage_users'))
            
            users_collection.insert_one({
                'username': username,
                'password': generate_password_hash(password),
                'role': role,
                'created_at': datetime.utcnow()
            })
            flash('User created successfully', 'success')
            return redirect(url_for('manage_users'))
        
        users = list(users_collection.find({}, {'password': 0}))
        for user in users:
            user['_id'] = str(user['_id'])
            user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
        
        return render_template(
            'admin.html',
            db_management_section=True,
            db_content='manage_users',
            users=users
        )
    except Exception as e:
        app.logger.error(f"User management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/delete/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Удаление пользователя"""
    try:
        # Нельзя удалить текущего пользователя или суперадмина
        current_user = request.authorization.username
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            flash('User not found', 'danger')
        elif user['username'] == current_user:
            flash('You cannot delete yourself', 'danger')
        elif user['role'] == 'superadmin':
            flash('Cannot delete superadmin', 'danger')
        else:
            users_collection.delete_one({'_id': ObjectId(user_id)})
            flash('User deleted successfully', 'success')
    except Exception as e:
        app.logger.error(f"Delete user error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
