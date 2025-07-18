import os
import logging
import stripe
import time
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init_logger():
    """Инициализация логгера для модуля"""
    handler = logging.FileHandler('logs/stripepay.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

init_logger()

class StripePayment:
    def __init__(self, stripe_api_key, webhook_secret, users_collection, payments_collection, refunds_collection):
        self.stripe_api_key = stripe_api_key
        self.webhook_secret = webhook_secret
        self.users_collection = users_collection
        self.payments_collection = payments_collection
        self.refunds_collection = refunds_collection
        stripe.api_key = stripe_api_key
        logger.info("StripePayment initialized")

    def create_checkout_session(self, imei, service_type, amount, success_url, cancel_url, metadata=None, idempotency_key=None):
        try:
            logger.info(f"Creating checkout session for IMEI: {imei}, service: {service_type}")
            logger.info(f"Amount: {amount} (cents)")
            
            if metadata is None:
                metadata = {}
                
            metadata.update({
                'imei': imei,
                'service_type': service_type
            })
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gel',
                        'product_data': {
                            'name': f'Apple IMEI Check ({service_type.capitalize()})',
                            'description': f'IMEI: {imei}',
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata=metadata,
                success_url=success_url,
                cancel_url=cancel_url,
                idempotency_key=idempotency_key
            )
            
            # Проверка создания сессии
            if not session or not hasattr(session, 'id'):
                logger.error("Stripe session creation failed: empty response")
                raise Exception("Stripe API returned empty session object")
                
            logger.info(f"Stripe session created successfully: {session.id}")
            return session
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {e.user_message}")
            raise Exception(f"Stripe error: {e.user_message}") from e
        except Exception as e:
            logger.exception("Stripe session creation failed")
            raise Exception("Payment processing error") from e

    def create_topup_session(self, user_id, amount, success_url, cancel_url, idempotency_key=None):
        try:
            logger.info(f"Creating topup session for user: {user_id}, amount: {amount}")
            session = stripe.checkout.Session.create(
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
                    'user_id': str(user_id),
                    'type': 'balance_topup'
                },
                success_url=success_url,
                cancel_url=cancel_url,
                idempotency_key=idempotency_key
            )
            
            if not session or not hasattr(session, 'id'):
                logger.error("Stripe topup session creation failed: empty response")
                raise Exception("Stripe API returned empty session object")
            
            if session.payment_intent:
                stripe.PaymentIntent.modify(
                    session.payment_intent,
                    metadata={
                        'session_id': session.id,
                        'user_id': str(user_id),
                        'type': 'balance_topup'
                    }
                )
            
            return session
        except Exception as e:
            logger.exception(f"Topup session error: {str(e)}")
            raise

    def deduct_balance(self, user_id, amount, service_type, imei, idempotency_key):
        try:
            logger.info(f"Deducting balance for user: {user_id}, amount: {amount}")
            existing_payment = self.payments_collection.find_one({
                'idempotency_key': idempotency_key,
                'type': 'imei_check'
            })
            
            if existing_payment:
                logger.warning(f"Duplicate idempotency key: {idempotency_key}")
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
                logger.error(f"Balance deduction failed for user: {user_id}")
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
            
            logger.info(f"Balance deducted: user={user_id}, amount={amount}")
            return True
            
        except Exception as e:
            logger.exception(f"Balance deduction error: {str(e)}")
            
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
        try:
            logger.info(f"Creating refund for payment: {payment_id}")
            existing_refund = self.refunds_collection.find_one({
                'payment_id': ObjectId(payment_id),
                'idempotency_key': idempotency_key
            })
            
            if existing_refund:
                logger.warning(f"Duplicate refund attempt: {idempotency_key}")
                return {
                    'status': 'error',
                    'message': 'Refund already processed'
                }
                
            payment = self.payments_collection.find_one({'_id': ObjectId(payment_id)})
            
            if not payment:
                logger.warning(f"Payment not found: {payment_id}")
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
                    logger.error(f"Balance refund failed for user: {payment['user_id']}")
                    return {
                        'status': 'error',
                        'message': 'Failed to refund to balance'
                    }
            else:
                refund = stripe.Refund.create(
                    payment_intent=payment['stripe_payment_intent'],
                    amount=int(amount * 100),
                    currency=currency,
                    reason=reason,
                    idempotency_key=idempotency_key
                )
                
                if refund.status != 'succeeded':
                    logger.error(f"Stripe refund failed: {refund.failure_reason}")
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
            
            logger.info(f"Refund processed: payment_id={payment_id}, amount={amount}")
            return {
                'status': 'success',
                'message': 'Refund processed successfully'
            }
            
        except Exception as e:
            logger.exception(f"Refund processing error: {str(e)}")
            
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
        try:
            event_type = event['type']
            logger.info(f"Processing Stripe event: {event_type}")
            
            if event_type == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                session_id = payment_intent.get('metadata', {}).get('session_id')
                
                if not session_id:
                    logger.warning("No session_id in payment_intent metadata")
                    return {
                        'status': 'error',
                        'message': 'Missing session_id in payment_intent metadata',
                        'event_type': event_type
                    }
                    
                session = stripe.checkout.Session.retrieve(session_id)
                return self.process_topup(session)
            
            elif event_type == 'checkout.session.completed':
                session = event['data']['object']
                metadata = session.get('metadata', {})
                
                if session.get('payment_status') != 'paid':
                    logger.warning(f"Unpaid session: {session['id']}")
                    return {
                        'status': 'error',
                        'message': f'Unpaid session: {session["id"]}',
                        'session_id': session['id']
                    }
                
                if metadata.get('type') == 'balance_topup':
                    return self.process_topup(session)
                
                elif metadata.get('service_type'):
                    imei = metadata['imei']
                    service_type = metadata['service_type']
                    amount = session['amount_total'] / 100
                    currency = session['currency']
                    
                    logger.info(
                        f"Payment received: imei={imei}, "
                        f"service={service_type}, session={session['id']}"
                    )
                    
                    existing_payment = self.payments_collection.find_one({
                        'stripe_session_id': session['id']
                    })
                    if existing_payment:
                        logger.warning(f"Duplicate payment for session: {session['id']}")
                        return {
                            'status': 'error',
                            'message': f'Duplicate payment for session: {session["id"]}',
                            'session_id': session['id']
                        }
                    
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
                            logger.error(f"Invalid user ID in metadata: {metadata['user_id']}")
                    
                    if self.payments_collection.count_documents({'stripe_session_id': session['id']}) == 0:
                        self.payments_collection.insert_one(payment_record)
                        logger.info(f"Payment record created: {session['id']}")
                    else:
                        logger.warning(f"Payment record already exists: {session['id']}")
            
            elif event_type == 'checkout.session.async_payment_succeeded':
                session = event['data']['object']
                logger.info(f"Payment succeeded: {session['id']}")
                
                self.payments_collection.update_one(
                    {'stripe_session_id': session['id']},
                    {'$set': {
                        'payment_status': 'succeeded',
                        'status': 'pending_verification'
                    }}
                )
            
            elif event_type == 'checkout.session.async_payment_failed':
                session = event['data']['object']
                logger.warning(f"Payment failed: {session['id']}")
                
                self.payments_collection.update_one(
                    {'stripe_session_id': session['id']},
                    {'$set': {
                        'payment_status': 'failed',
                        'status': 'failed'
                    }}
                )
            
            elif event_type == 'charge.refunded':
                charge = event['data']['object']
                logger.info(f"Refund processed: {charge.id}")
                
                refund_data = {
                    'stripe_charge_id': charge.id,
                    'amount': charge.amount_refunded / 100,
                    'currency': charge.currency,
                    'status': 'succeeded',
                    'timestamp': datetime.utcnow(),
                    'reason': 'stripe_webhook'
                }
                
                self.refunds_collection.update_one(
                    {'stripe_charge_id': charge.id},
                    {'$setOnInsert': refund_data},
                    upsert=True
                )
                
                if charge.metadata.get('type') == 'balance_topup':
                    user_id_str = charge.metadata.get('user_id')
                    try:
                        user_id = ObjectId(user_id_str)
                    except (TypeError, InvalidId):
                        logger.error(f"Invalid user ID in charge metadata: {user_id_str}")
                        return {
                            'status': 'error',
                            'message': f'Invalid user ID: {user_id_str}',
                            'event_type': event_type
                        }
                    
                    amount = charge.amount_refunded / 100
                    
                    result = self.users_collection.update_one(
                        {'_id': user_id},
                        {'$inc': {'balance': -amount}}
                    )
                    
                    if result.modified_count:
                        logger.info(f"Adjusted balance for user {user_id}: -{amount} GEL")
                    else:
                        logger.error(f"Balance adjustment failed for user: {user_id}")
            
            return {
                'status': 'success',
                'processed_event': event_type
            }
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in webhook: {e.user_message}")
            return {
                'status': 'error',
                'message': f'Stripe error: {e.user_message}',
                'event_type': event_type
            }
        except Exception as e:
            logger.exception("Webhook processing error")
            return {
                'status': 'error',
                'message': f'Internal error: {str(e)}',
                'event_type': event_type
            }

    def process_topup(self, session):
        metadata = session.get('metadata', {})
        
        if metadata.get('type') == 'balance_topup':
            user_id_str = metadata.get('user_id')
            try:
                user_id = ObjectId(user_id_str)
            except (TypeError, InvalidId):
                logger.error(f"Invalid user ID in metadata: {user_id_str}")
                return {
                    'status': 'error',
                    'message': f'Invalid user ID: {user_id_str}',
                    'session_id': session['id']
                }
            
            amount = session['amount_total'] / 100
            
            existing_payment = self.payments_collection.find_one({
                'stripe_session_id': session['id'],
                'type': 'topup'
            })
            if existing_payment:
                logger.warning(f"Duplicate topup for session: {session['id']}")
                return {
                    'status': 'error',
                    'message': f'Duplicate topup for session: {session["id"]}',
                    'session_id': session['id']
                }
            
            logger.info(
                f"Balance topup: user={user_id}, "
                f"amount={amount}, session={session['id']}"
            )
            
            user = self.users_collection.find_one({'_id': user_id})
            if not user:
                logger.error(f"User not found: {user_id}")
                return {
                    'status': 'error',
                    'message': f'User not found: {user_id}',
                    'session_id': session['id']
                }
            
            result = self.users_collection.update_one(
                {'_id': user_id},
                {'$inc': {'balance': amount}}
            )
            
            if not result.modified_count:
                logger.error(f"Balance update failed for user: {user_id}")
                return {
                    'status': 'error',
                    'message': f'Balance update failed for user: {user_id}',
                    'session_id': session['id']
                }
            
            self.payments_collection.insert_one({
                'user_id': user_id,
                'amount': amount,
                'currency': session['currency'],
                'stripe_session_id': session['id'],
                'stripe_payment_intent': session.get('payment_intent'),
                'timestamp': datetime.utcnow(),
                'type': 'topup',
                'status': 'completed'
            })
            
            logger.info(f"Balance topup success: user={user_id}, amount={amount}")
            return {
                'status': 'success',
                'message': 'Balance topup processed',
                'session_id': session['id']
            }
        return {
            'status': 'success',
            'message': 'No topup processed',
            'session_id': session['id']
            }
