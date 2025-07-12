import os
import stripe
import time
from datetime import datetime
from bson import ObjectId, InvalidId
from flask import url_for, current_app

class StripePayment:
    def __init__(self, stripe_api_key, webhook_secret, users_collection, payments_collection, refunds_collection):
        self.stripe_api_key = stripe_api_key
        self.webhook_secret = webhook_secret
        self.users_collection = users_collection
        self.payments_collection = payments_collection
        self.refunds_collection = refunds_collection
        stripe.api_key = stripe_api_key

    def create_checkout_session(self, imei, service_type, amount, success_url, cancel_url, metadata=None, idempotency_key=None):
        try:
            if metadata is None:
                metadata = {}
                
            metadata.update({
                'imei': imei,
                'service_type': service_type
            })
            
            return stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gel',
                        'product_data': {
                            'name': f'Apple IMEI Check ({service_type.capitalize()})',
                            'description': f'IMEI: {imei}',
                        },
                        'unit_amount': int(amount * 100),  # Исправлено: преобразование в центы
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata=metadata,
                success_url=success_url,
                cancel_url=cancel_url,
                idempotency_key=idempotency_key
            )
        except Exception as e:
            current_app.logger.error(f"Stripe session error: {str(e)}")
            raise

    def create_topup_session(self, user_id, amount, success_url, cancel_url, idempotency_key=None):
        try:
            return stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gel',
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
                    'user_id': str(user_id),  # Сохраняем как строку
                    'type': 'balance_topup'
                },
                success_url=success_url,
                cancel_url=cancel_url,
                idempotency_key=idempotency_key
            )
        except Exception as e:
            current_app.logger.error(f"Topup session error: {str(e)}")
            raise

    def deduct_balance(self, user_id, amount, service_type, imei, idempotency_key):
        """Атомарное списание средств с баланса с защитой от гонок"""
        try:
            existing_payment = self.payments_collection.find_one({
                'idempotency_key': idempotency_key,
                'type': 'imei_check'
            })
            
            if existing_payment:
                current_app.logger.warning(f"Duplicate idempotency key: {idempotency_key}")
                return False
                
            result = self.users_collection.update_one(
                {
                    '_id': ObjectId(user_id),
                    'balance': {'$gte': amount}
                },
                {
                    '$inc': {'balance': -amount},
                    '$set': {'last_updated': datetime.utcnow()}
                }
            )
            
            if result.modified_count == 0:
                current_app.logger.error(f"Balance deduction failed for user: {user_id}")
                return False
            
            payment_data = {
                'user_id': ObjectId(user_id),
                'amount': -amount,
                'currency': 'gel',
                'type': 'imei_check',
                'service_type': service_type,
                'imei': imei,
                'timestamp': datetime.utcnow(),
                'status': 'completed',
                'idempotency_key': idempotency_key
            }
            
            self.payments_collection.insert_one(payment_data)
            
            audit_log = {
                'action': 'balance_deduction',
                'user_id': ObjectId(user_id),
                'amount': amount,
                'service_type': service_type,
                'imei': imei,
                'timestamp': datetime.utcnow(),
                'status': 'success'
            }
            self.payments_collection.insert_one(audit_log)
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Balance deduction error: {str(e)}")
            
            audit_log = {
                'action': 'balance_deduction',
                'user_id': ObjectId(user_id),
                'amount': amount,
                'service_type': service_type,
                'imei': imei,
                'timestamp': datetime.utcnow(),
                'status': 'failed',
                'error': str(e)
            }
            self.payments_collection.insert_one(audit_log)
            
            return False

    def create_refund(self, payment_id, amount, currency, reason, idempotency_key):
        """Создание возврата средств"""
        try:
            existing_refund = self.refunds_collection.find_one({
                'payment_id': ObjectId(payment_id),
                'idempotency_key': idempotency_key
            })
            
            if existing_refund:
                current_app.logger.warning(f"Duplicate refund attempt: {idempotency_key}")
                return {
                    'status': 'error',
                    'message': 'Refund already processed'
                }
                
            payment = self.payments_collection.find_one({'_id': ObjectId(payment_id)})
            
            if not payment:
                return {
                    'status': 'error',
                    'message': 'Payment not found'
                }
                
            if payment.get('payment_method') == 'balance':
                result = self.users_collection.update_one(
                    {'_id': payment['user_id']},
                    {'$inc': {'balance': amount}}
                )
                
                if result.modified_count == 0:
                    return {
                        'status': 'error',
                        'message': 'Failed to refund to balance'
                    }
            else:
                # Исправлено: преобразование суммы в центы
                refund = stripe.Refund.create(
                    payment_intent=payment['stripe_payment_intent'],
                    amount=int(amount * 100),
                    currency=currency,
                    reason=reason,
                    idempotency_key=idempotency_key
                )
                
                if refund.status != 'succeeded':
                    return {
                        'status': 'error',
                        'message': f'Stripe refund failed: {refund.failure_reason}'
                    }
            
            refund_data = {
                'payment_id': ObjectId(payment_id),
                'amount': amount,
                'currency': currency,
                'reason': reason,
                'status': 'completed',
                'timestamp': datetime.utcnow(),
                'idempotency_key': idempotency_key
            }
            
            self.refunds_collection.insert_one(refund_data)
            
            self.payments_collection.update_one(
                {'_id': ObjectId(payment_id)},
                {'$set': {'refund_status': 'refunded'}}
            )
            
            return {
                'status': 'success',
                'message': 'Refund processed successfully'
            }
            
        except Exception as e:
            current_app.logger.error(f"Refund processing error: {str(e)}")
            
            refund_data = {
                'payment_id': ObjectId(payment_id),
                'amount': amount,
                'currency': currency,
                'reason': reason,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow(),
                'idempotency_key': idempotency_key
            }
            
            self.refunds_collection.insert_one(refund_data)
            
            return {
                'status': 'error',
                'message': str(e)
            }

    def handle_webhook(self, event):
        """Обрабатывает верифицированные вебхуки от Stripe"""
        try:
            event_type = event['type']
            current_app.logger.info(f"Processing Stripe event: {event_type}")
            
            # Обработка события
            if event_type == 'checkout.session.completed':
                session = event['data']['object']
                metadata = session.get('metadata', {})
                
                # Проверка статуса платежа
                if session.get('payment_status') != 'paid':
                    current_app.logger.warning(f"Unpaid session: {session['id']}")
                    return event
                
                # Пополнение баланса
                if metadata.get('type') == 'balance_topup':
                    user_id_str = metadata.get('user_id')
                    try:
                        user_id = ObjectId(user_id_str)
                    except (TypeError, InvalidId):
                        current_app.logger.error(f"Invalid user ID in metadata: {user_id_str}")
                        return event
                    
                    amount = session['amount_total'] / 100
                    
                    # Проверка на дубликат
                    existing_payment = self.payments_collection.find_one({
                        'stripe_session_id': session['id'],
                        'type': 'topup'
                    })
                    if existing_payment:
                        current_app.logger.warning(f"Duplicate topup for session: {session['id']}")
                        return event
                    
                    current_app.logger.info(
                        f"Balance topup: user={user_id}, "
                        f"amount={amount}, session={session['id']}"
                    )
                    
                    user = self.users_collection.find_one({'_id': user_id})
                    if not user:
                        current_app.logger.error(f"User not found: {user_id}")
                        return event
                    
                    # Атомарное обновление баланса
                    result = self.users_collection.update_one(
                        {'_id': user_id},
                        {'$inc': {'balance': amount}}
                    )
                    
                    if not result.modified_count:
                        current_app.logger.error(f"Balance update failed for user: {user_id}")
                    
                    # Запись о платеже
                    self.payments_collection.insert_one({
                        'user_id': user_id,
                        'amount': amount,
                        'currency': session['currency'],
                        'stripe_session_id': session['id'],
                        'timestamp': datetime.utcnow(),
                        'type': 'topup',
                        'status': 'completed'
                    })
                
                # Обычная оплата проверки
                elif metadata.get('service_type'):
                    imei = metadata['imei']
                    service_type = metadata['service_type']
                    amount = session['amount_total'] / 100
                    currency = session['currency']
                    
                    current_app.logger.info(
                        f"Payment received: imei={imei}, "
                        f"service={service_type}, session={session['id']}"
                    )
                    
                    # Проверка на дубликат
                    existing_payment = self.payments_collection.find_one({
                        'stripe_session_id': session['id']
                    })
                    if existing_payment:
                        current_app.logger.warning(f"Duplicate payment for session: {session['id']}")
                        return event
                    
                    payment_record = {
                        'stripe_session_id': session['id'],
                        'imei': imei,
                        'service_type': service_type,
                        'amount': amount,
                        'currency': currency,
                        'payment_status': 'paid',
                        'timestamp': datetime.utcnow(),
                        'type': 'imei_check',
                        'status': 'pending_verification'
                    }
                    
                    if 'user_id' in metadata:
                        try:
                            payment_record['user_id'] = ObjectId(metadata['user_id'])
                        except (TypeError, InvalidId):
                            current_app.logger.error(f"Invalid user ID in metadata: {metadata['user_id']}")
                    
                    self.payments_collection.insert_one(payment_record)
            
            # Обновление статуса платежа
            elif event_type == 'checkout.session.async_payment_succeeded':
                session = event['data']['object']
                current_app.logger.info(f"Payment succeeded: {session['id']}")
                
                self.payments_collection.update_one(
                    {'stripe_session_id': session['id']},
                    {'$set': {
                        'payment_status': 'succeeded',
                        'status': 'pending_verification'
                    }}
                )
            
            elif event_type == 'checkout.session.async_payment_failed':
                session = event['data']['object']
                current_app.logger.warning(f"Payment failed: {session['id']}")
                
                self.payments_collection.update_one(
                    {'stripe_session_id': session['id']},
                    {'$set': {
                        'payment_status': 'failed',
                        'status': 'failed'
                    }}
                )
            
            # Обработка возвратов
            elif event_type == 'charge.refunded':
                charge = event['data']['object']
                current_app.logger.info(f"Refund processed: {charge.id}")
                
                # Поиск или создание записи о возврате
                refund_data = {
                    'stripe_charge_id': charge.id,
                    'amount': charge.amount_refunded / 100,
                    'currency': charge.currency,
                    'status': 'succeeded',
                    'timestamp': datetime.utcnow(),
                    'reason': 'stripe_webhook'
                }
                
                # Обновляем или создаем запись
                self.refunds_collection.update_one(
                    {'stripe_charge_id': charge.id},
                    {'$setOnInsert': refund_data},
                    upsert=True
                )
                
                # Если возврат связан с пополнением баланса
                if charge.metadata.get('type') == 'balance_topup':
                    user_id_str = charge.metadata.get('user_id')
                    try:
                        user_id = ObjectId(user_id_str)
                    except (TypeError, InvalidId):
                        current_app.logger.error(f"Invalid user ID in charge metadata: {user_id_str}")
                        return event
                    
                    amount = charge.amount_refunded / 100
                    
                    # Атомарное вычитание баланса
                    result = self.users_collection.update_one(
                        {'_id': user_id},
                        {'$inc': {'balance': -amount}}
                    )
                    
                    if result.modified_count:
                        current_app.logger.info(f"Adjusted balance for user {user_id}: -{amount} GEL")
                    else:
                        current_app.logger.error(f"Balance adjustment failed for user: {user_id}")
            
            return event
        
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error in webhook: {e.user_message}")
            raise e
        except Exception as e:
            current_app.logger.exception("Webhook processing error")
            raise e
