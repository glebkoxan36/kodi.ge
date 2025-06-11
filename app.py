import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import stripe
from utils import check_imei

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Stripe конфиг
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DOMAIN = os.getenv("DOMAIN", "http://localhost:5000")

# Цены в Lari (Stripe использует центы, т.е. 2 lari = 200₾)
PRICE_TIERS = {
    4: 200,    # платная проверка — 2 lari
    205: 500,  # премиум — 5 lari
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    imei = request.form.get("imei")
    tier = int(request.form.get("tier", 4))
    amount = PRICE_TIERS.get(tier, 200)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "gel",
                "product_data": {"name": f"IMEI Check (service {tier})"},
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=DOMAIN + "/success?session_id={CHECKOUT_SESSION_ID}&imei=" + imei + "&tier=" + str(tier),
        cancel_url=DOMAIN + "/cancel",
    )
    return redirect(session.url, code=303)


@app.route("/success")
def success():
    imei = request.args.get("imei")
    tier = int(request.args.get("tier", 4))
    # Проверяем сразу после оплаты
    result = check_imei(imei, service=tier)
    return render_template("result.html", imei=imei, result=result)


@app.route("/cancel")
def cancel():
    return "<h3>Оплата отменена.</h3>"

if __name__ == "__main__":
    app.run(debug=True)
