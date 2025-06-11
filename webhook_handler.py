import os
import stripe
from flask import Flask, request, jsonify

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"error": "Invalid payload or signature"}), 400

    # Обработка успешного платежа
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Здесь можно сохранять в БД логи или слать уведомления
        print(f"Payment succeeded for session {session['id']}")

    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    app.run(port=4242)
