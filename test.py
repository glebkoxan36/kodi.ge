import os
import logging
import stripe
import json
import time
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, session
from functools import wraps
from bson import ObjectId
from werkzeug.security import generate_password_hash
from db import (
    checks_collection, 
    regular_users_collection, 
    payments_collection,
    refunds_collection,
    prices_collection
)
from ifreeapi import perform_api_check
from stripepay import StripePayment

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля тестирования"""
    handler = logging.FileHandler('logs/test_module.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

test_bp = Blueprint('test', __name__)

# Декоратор для проверки прав администратора
def admin_test_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or session['role'] not in ['admin', 'superadmin']:
            logger.warning("Unauthorized test access attempt")
            return jsonify({
                'status': 'error',
                'message': 'Требуются права администратора'
            }), 403
        return f(*args, **kwargs)
    return decorated

def get_test_user():
    """Создает или возвращает тестового пользователя для операций"""
    try:
        # Проверяем существование тестового пользователя
        test_user = regular_users_collection.find_one({'email': 'test_admin@imei.ge'})
        
        if not test_user:
            # Создаем нового тестового пользователя
            test_user = {
                'email': 'test_admin@imei.ge',
                'first_name': 'Test',
                'last_name': 'Admin',
                'password': generate_password_hash('testpassword'),
                'balance': 1000.00,  # Начальный баланс 1000 лари
                'created_at': datetime.utcnow(),
                'is_test_account': True
            }
            result = regular_users_collection.insert_one(test_user)
            test_user['_id'] = result.inserted_id
            logger.info("Created test user account")
        else:
            # Обновляем баланс для тестов
            regular_users_collection.update_one(
                {'_id': test_user['_id']},
                {'$set': {'balance': 1000.00}}
            )
            logger.info("Reset test user balance")
        
        return str(test_user['_id'])
    except Exception as e:
        logger.error(f"Test user error: {str(e)}")
        return None

def create_stripe_test_payment(stripe_payment, user_id, amount):
    """Создает тестовый платеж через Stripe"""
    try:
        idempotency_key = f"test_topup_{datetime.utcnow().timestamp()}"
        
        # Создаем сессию для пополнения баланса
        success_url = f"{request.host_url}test/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{request.host_url}test/cancel"
        
        session = stripe_payment.create_topup_session(
            user_id=user_id,
            amount=amount,
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=idempotency_key
        )
        
        # Имитируем успешную оплату
        payment_data = {
            'user_id': ObjectId(user_id),
            'amount': amount,
            'currency': 'gel',
            'stripe_session_id': session.id,
            'payment_status': 'paid',
            'type': 'topup',
            'timestamp': datetime.utcnow(),
            'status': 'completed',
            'is_test': True
        }
        payments_collection.insert_one(payment_data)
        
        # Обновляем баланс пользователя
        regular_users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$inc': {'balance': amount}}
        )
        
        logger.info(f"Created test Stripe topup: {amount} GEL")
        return True
    except Exception as e:
        logger.error(f"Stripe test payment error: {str(e)}")
        return False

@test_bp.route('/test/paid-check', methods=['POST'])
@admin_test_required
def test_paid_check():
    """Тестирование платной проверки IMEI"""
    try:
        data = request.json
        imei = data.get('imei', '012345678901234')  # Тестовый IMEI по умолчанию
        service_type = data.get('service_type', 'fmi')
        payment_method = data.get('payment_method', 'stripe')  # stripe или balance
        
        logger.info(f"Starting paid check test: IMEI={imei}, service={service_type}, method={payment_method}")
        
        # Получаем тестового пользователя
        user_id = get_test_user()
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Не удалось создать тестового пользователя'
            }), 500
        
        # Получаем цену для услуги
        prices = prices_collection.find_one({'type': 'current'})
        if not prices:
            return jsonify({
                'status': 'error',
                'message': 'Цены не найдены'
            }), 500
            
        price_key = 'paid' if service_type in ['fmi', 'blacklist', 'activation', 'carrier'] else 'premium'
        amount = prices['prices'][price_key] / 100
        
        # Оплата через Stripe
        if payment_method == 'stripe':
            # Создаем тестовый платеж
            stripe_payment = StripePayment(
                stripe_api_key=current_app.config['STRIPE_SECRET_KEY'],
                webhook_secret=current_app.config['STRIPE_WEBHOOK_SECRET'],
                users_collection=regular_users_collection,
                payments_collection=payments_collection,
                refunds_collection=refunds_collection
            )
            
            if not create_stripe_test_payment(stripe_payment, user_id, amount):
                return jsonify({
                    'status': 'error',
                    'message': 'Ошибка создания тестового платежа Stripe'
                }), 500
        
        # Оплата с баланса
        elif payment_method == 'balance':
            # Списание средств
            idempotency_key = f"test_balance_{datetime.utcnow().timestamp()}"
            stripe_payment = StripePayment(
                stripe_api_key=current_app.config['STRIPE_SECRET_KEY'],
                webhook_secret=current_app.config['STRIPE_WEBHOOK_SECRET'],
                users_collection=regular_users_collection,
                payments_collection=payments_collection,
                refunds_collection=refunds_collection
            )
            result = stripe_payment.deduct_balance(
                user_id=user_id,
                amount=amount,
                service_type=service_type,
                imei=imei,
                idempotency_key=idempotency_key
            )
            
            if not result:
                return jsonify({
                    'status': 'error',
                    'message': 'Ошибка списания средств с баланса'
                }), 500
        
        # Выполняем проверку IMEI
        start_time = time.time()
        result = perform_api_check(imei, service_type)
        duration = time.time() - start_time
        
        # Формируем результат
        response = {
            'status': 'success',
            'test_type': 'paid_check',
            'payment_method': payment_method,
            'service_type': service_type,
            'amount': amount,
            'duration': f"{duration:.2f}s",
            'result': result
        }
        
        # Сохраняем результат проверки
        check_record = {
            'imei': imei,
            'service_type': service_type,
            'paid': True,
            'payment_method': payment_method,
            'amount': amount,
            'user_id': ObjectId(user_id),
            'timestamp': datetime.utcnow(),
            'result': result,
            'is_test': True
        }
        checks_collection.insert_one(check_record)
        
        logger.info(f"Paid check test completed: {service_type}")
        return jsonify(response)
    
    except Exception as e:
        logger.exception(f"Paid check test error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Ошибка тестирования: {str(e)}'
        }), 500

@test_bp.route('/test/topup', methods=['POST'])
@admin_test_required
def test_balance_topup():
    """Тестирование пополнения баланса"""
    try:
        data = request.json
        amount = data.get('amount', 10.00)  # Сумма по умолчанию 10 лари
        
        logger.info(f"Starting balance topup test: {amount} GEL")
        
        # Получаем тестового пользователя
        user_id = get_test_user()
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Не удалось создать тестового пользователя'
            }), 500
        
        # Создаем Stripe платеж
        stripe_payment = StripePayment(
            stripe_api_key=current_app.config['STRIPE_SECRET_KEY'],
            webhook_secret=current_app.config['STRIPE_WEBHOOK_SECRET'],
            users_collection=regular_users_collection,
            payments_collection=payments_collection,
            refunds_collection=refunds_collection
        )
        
        # Создаем тестовый платеж
        if not create_stripe_test_payment(stripe_payment, user_id, amount):
            return jsonify({
                'status': 'error',
                'message': 'Ошибка создания тестового платежа'
            }), 500
        
        # Получаем обновленный баланс
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        new_balance = user.get('balance', 0)
        
        logger.info(f"Balance topup test completed: +{amount} GEL")
        return jsonify({
            'status': 'success',
            'test_type': 'balance_topup',
            'amount': amount,
            'new_balance': new_balance
        })
    
    except Exception as e:
        logger.exception(f"Balance topup test error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Ошибка тестирования: {str(e)}'
        }), 500

@test_bp.route('/test/refund', methods=['POST'])
@admin_test_required
def test_refund():
    """Тестирование возврата средств"""
    try:
        logger.info("Starting refund test")
        
        # Получаем тестового пользователя
        user_id = get_test_user()
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Не удалось создать тестового пользователя'
            }), 500
        
        # Находим последний тестовый платеж
        payment = payments_collection.find_one({
            'user_id': ObjectId(user_id),
            'is_test': True,
            'type': 'topup'
        }, sort=[('timestamp', -1)])
        
        if not payment:
            return jsonify({
                'status': 'error',
                'message': 'Тестовый платеж не найден'
            }), 404
        
        # Создаем возврат
        stripe_payment = StripePayment(
            stripe_api_key=current_app.config['STRIPE_SECRET_KEY'],
            webhook_secret=current_app.config['STRIPE_WEBHOOK_SECRET'],
            users_collection=regular_users_collection,
            payments_collection=payments_collection,
            refunds_collection=refunds_collection
        )
        
        idempotency_key = f"test_refund_{datetime.utcnow().timestamp()}"
        refund_result = stripe_payment.create_refund(
            payment_id=str(payment['_id']),
            amount=payment['amount'],
            currency=payment['currency'],
            reason='Тестовый возврат',
            idempotency_key=idempotency_key
        )
        
        if refund_result['status'] != 'success':
            return jsonify({
                'status': 'error',
                'message': refund_result['message']
            }), 500
        
        # Получаем обновленный баланс
        user = regular_users_collection.find_one({'_id': ObjectId(user_id)})
        new_balance = user.get('balance', 0)
        
        logger.info("Refund test completed")
        return jsonify({
            'status': 'success',
            'test_type': 'refund',
            'refunded_amount': payment['amount'],
            'new_balance': new_balance
        })
    
    except Exception as e:
        logger.exception(f"Refund test error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Ошибка тестирования: {str(e)}'
        }), 500

@test_bp.route('/test/status')
@admin_test_required
def test_status():
    """Проверка статуса тестового модуля"""
    try:
        # Проверяем подключение к БД
        db_status = 'ok' if regular_users_collection is not None else 'error'
        
        # Проверяем Stripe
        stripe_status = 'ok'
        try:
            stripe.Balance.retrieve()
            stripe_status = 'ok'
        except Exception as e:
            stripe_status = f'error: {str(e)}'
        
        return jsonify({
            'status': 'ok',
            'database': db_status,
            'stripe': stripe_status,
            'test_user': get_test_user() is not None
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
