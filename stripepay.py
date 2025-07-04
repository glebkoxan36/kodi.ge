import os
import stripe
import time
from datetime import datetime
from bson import ObjectId
from flask import url_for, current_app

class StripePayment:
    def __init__(self, stripe_api_key, webhook_secret, users_collection, payments_collection):
        self.stripe_api_key = stripe_api_key
        self.webhook_secret = webhook_secret
        self.users_collection = users_collection
        self.payments_collection = payments_collection
        stripe.api_key = stripe_api_key

    def create_checkout_session(self, imei, service_type, amount, success_url, cancel_url):
        try:
            return stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Device Check ({service_type.capitalize()})',
                            'description': f'IMEI: {imei}',
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata={
                    'imei': imei,
                    'service_type': service_type
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except Exception as e:
            current_app.logger.error(f"Stripe session error: {str(e)}")
            raise

    def create_topup_session(self, user_id, amount, success_url, cancel_url):
        try:
            return stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Balance Topup',
                            'description': f'User ID: {user_id}',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata={
                    'user_id': user_id,
                    'type': 'balance_topup'
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except Exception as e:
            current_app.logger.error(f"Topup session error: {str(e)}")
            raise

    def deduct_balance(self, user_id, amount):
        try:
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id), 'balance': {'$gte': amount}},
                {'$inc': {'balance': -amount}}
            )
            
            if result.modified_count > 0:
                self.payments_collection.insert_one({
                    'user_id': ObjectId(user_id),
                    'amount': -amount,
                    'currency': 'usd',
                    'type': 'imei_check',
                    'timestamp': datetime.utcnow(),
                    'description': f'Оплата проверки IMEI'
                })
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"Balance deduction error: {str(e)}")
            return False

    def handle_webhook(self, payload, sig_header):
        """Обрабатывает вебхуки от Stripe"""
        try:
            current_app.logger.info("Processing Stripe webhook...")
            
            if not sig_header:
                current_app.logger.error("Missing Stripe-Signature header")
                raise ValueError("Missing signature header")
            
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                self.webhook_secret,
                tolerance=300
            )
            
            current_app.logger.info(f"Webhook event: {event['type']}")
            
            # Обработка события
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                metadata = session.get('metadata', {})
                
                # Пополнение баланса
                if metadata.get('type') == 'balance_topup':
                    user_id = metadata.get('user_id')
                    amount = session['amount_total'] / 100
                    
                    current_app.logger.info(f"Balance topup: user={user_id}, amount={amount}")
                    
                    # Обновление баланса
                    self.users_collection.update_one(
                        {'_id': ObjectId(user_id)},
                        {'$inc': {'balance': amount}}
                    )
                    
                    # Запись о платеже
                    self.payments_collection.insert_one({
                        'user_id': ObjectId(user_id),
                        'amount': amount,
                        'currency': session['currency'],
                        'stripe_session_id': session['id'],
                        'timestamp': datetime.utcnow(),
                        'type': 'topup'
                    })
                
                # Обычная оплата проверки
                elif metadata.get('service_type'):
                    imei = metadata['imei']
                    service_type = metadata['service_type']
                    amount = session['amount_total'] / 100
                    currency = session['currency']
                    
                    current_app.logger.info(f"Payment received: imei={imei}, service={service_type}")
                    
                    # Запись о платеже
                    payment_record = {
                        'stripe_session_id': session['id'],
                        'imei': imei,
                        'service_type': service_type,
                        'amount': amount,
                        'currency': currency,
                        'payment_status': session.get('payment_status', 'pending'),
                        'timestamp': datetime.utcnow(),
                        'type': 'imei_check'
                    }
                    
                    # Добавляем user_id если есть
                    if 'user_id' in metadata:
                        payment_record['user_id'] = ObjectId(metadata['user_id'])
                    
                    self.payments_collection.insert_one(payment_record)
            
            # Обновление статуса платежа
            elif event['type'] == 'checkout.session.async_payment_succeeded':
                session = event['data']['object']
                current_app.logger.info(f"Payment succeeded: {session['id']}")
                
                self.payments_collection.update_one(
                    {'stripe_session_id': session['id']},
                    {'$set': {'payment_status': 'succeeded'}}
                )
            
            elif event['type'] == 'checkout.session.async_payment_failed':
                session = event['data']['object']
                current_app.logger.warning(f"Payment failed: {session['id']}")
                
                self.payments_collection.update_one(
                    {'stripe_session_id': session['id']},
                    {'$set': {'payment_status': 'failed'}}
                )
            
            return event
        
        except ValueError as e:
            current_app.logger.error(f"Webhook value error: {str(e)}")
            raise e
        except stripe.error.SignatureVerificationError as e:
            current_app.logger.error(f"Webhook signature error: {str(e)}")
            current_app.logger.error(f"Expected secret: {self.webhook_secret[:6]}...")
            current_app.logger.error(f"Payload start: {str(payload)[:100]}...")
            raise e
        except Exception as e:
            current_app.logger.error(f"Webhook processing error: {str(e)}")
            raise e
