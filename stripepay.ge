import os
import stripe
from flask import url_for
from datetime import datetime
from bson import ObjectId

class StripePayment:
    def __init__(self, stripe_api_key, webhook_secret, users_collection, payments_collection):
        """
        Инициализация платежной системы Stripe
        
        :param stripe_api_key: Секретный ключ Stripe
        :param webhook_secret: Секрет для верификации вебхуков
        :param users_collection: Коллекция пользователей MongoDB
        :param payments_collection: Коллекция платежей MongoDB
        """
        self.stripe_api_key = stripe_api_key
        self.webhook_secret = webhook_secret
        self.users_collection = users_collection
        self.payments_collection = payments_collection
        
        # Настройка Stripe
        stripe.api_key = stripe_api_key

    def create_checkout_session(self, imei, service_type, amount, success_url, cancel_url):
        """
        Создает сессию оплаты для проверки IMEI
        
        :param imei: Номер IMEI устройства
        :param service_type: Тип услуги (например, 'paid', 'premium')
        :param amount: Стоимость услуги в центах
        :param success_url: URL для перенаправления после успешной оплаты
        :param cancel_url: URL для перенаправления при отмене оплаты
        :return: Объект сессии Stripe
        """
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Device Check ({service_type.capitalize()})',
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

    def create_topup_session(self, user_id, amount, success_url, cancel_url):
        """
        Создает сессию для пополнения баланса
        
        :param user_id: ID пользователя
        :param amount: Сумма пополнения в долларах
        :param success_url: URL для перенаправления после успешной оплаты
        :param cancel_url: URL для перенаправления при отмене оплаты
        :return: Объект сессии Stripe
        """
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Balance Topup',
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

    def handle_webhook(self, payload, sig_header):
        """
        Обрабатывает вебхуки от Stripe
        
        :param payload: Тело запроса вебхука
        :param sig_header: Заголовок подписи Stripe
        :return: Результат обработки события
        """
        try:
            # Верификация вебхука
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError as e:
            raise e
        except stripe.error.SignatureVerificationError as e:
            raise e

        # Обработка события "сессия оплаты завершена"
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            metadata = session.get('metadata', {})
            
            # Пополнение баланса
            if metadata.get('type') == 'balance_topup':
                user_id = metadata.get('user_id')
                amount = session['amount_total'] / 100  # Конвертация в доллары
                
                # Обновление баланса пользователя
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
        
        return event
