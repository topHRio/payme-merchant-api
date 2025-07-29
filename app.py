
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

PROMO_CODES = {
    "JULY20": 0.20,
    "HR50": 0.50
}

FULL_PRICE = 6_000_000

@app.route("/payme/init", methods=["POST"])
def init_payment():
    data = request.json
    name = data.get("name")
    phone = data.get("phone")
    promo = data.get("promo", "").upper()
    half_payment = data.get("half_payment", False)

    discount = PROMO_CODES.get(promo, 0)
    price = FULL_PRICE * (1 - discount)

    if half_payment:
        price = price / 2

    order_id = f"JHR-{phone[-4:]}-{os.urandom(3).hex()}"

    response = {
        "order_id": order_id,
        "amount": int(price * 100),
        "message": f"Оплата {'в 2 этапа' if half_payment else 'полная'} за курс Junior HR. Промокод: {promo or 'нет'}"
    }
    return jsonify(response)

@app.route("/payme/check", methods=["POST"])
def check_transaction():
    req = request.json
    order_id = req["params"]["account"]["order_id"]
    amount = req["params"]["amount"]

    return jsonify({
        "result": {
            "allow": True,
            "detail": {
                "receipt_type": 0,
                "items": [{
                    "title": "Junior HR kursi",
                    "price": amount,
                    "count": 1,
                    "code": "10899002001000000",
                    "vat_percent": 0,
                    "package_code": "123456"
                }]
            }
        }
    })

@app.route("/payme/create", methods=["POST"])
def create_transaction():
    return jsonify({"result": {"create_time": int(os.urandom(2).hex(), 16)}})

@app.route("/payme/perform", methods=["POST"])
def perform_transaction():
    return jsonify({"result": {"perform_time": int(os.urandom(2).hex(), 16)}})

@app.route("/payme/cancel", methods=["POST"])
def cancel_transaction():
    return jsonify({"result": {"cancel_time": int(os.urandom(2).hex(), 16)}})

@app.route("/payme/checkstatus", methods=["POST"])
def check_transaction_status():
    return jsonify({"result": {"status": 1}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
