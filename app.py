from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)

MERCHANT_KEY = "test"
transactions = {}

ERRORS = {
    'AUTH': {'code': -32504, 'message': "Недостаточно привилегий для выполнения метода."},
    'ORDER_NOT_FOUND': {'code': -31050, 'message': {"ru": "Заказ не найден", "uz": "Buyurtma topilmadi", "en": "Order not found"}},
    'ALREADY_PAID': {'code': -31099, 'message': {"ru": "Платеж на этот заказ на данный момент уже осуществляется", "uz": "Buyurtma to'lovi hozirda amalga oshirilmoqda", "en": "Order payment is already being processed"}},
    'INVALID_AMOUNT': {'code': -31001, 'message': {"ru": "Неверная сумма", "uz": "Noto'g'ri summa", "en": "Invalid amount"}},
}

@app.before_request
def check_auth():
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {MERCHANT_KEY}":
        return jsonify({"error": ERRORS['AUTH']}), 401

@app.route("/", methods=["POST"])
def index():
    data = request.get_json()
    method = data.get("method")
    params = data.get("params", {})

    if method == "CheckPerformTransaction":
        return check_perform(params, data.get("id"))
    elif method == "CreateTransaction":
        return create_transaction(params, data.get("id"))
    elif method == "PerformTransaction":
        return perform_transaction(params, data.get("id"))
    elif method == "CancelTransaction":
        return cancel_transaction(params, data.get("id"))
    elif method == "CheckTransaction":
        return check_transaction(params, data.get("id"))
    elif method == "GetStatement":
        return get_statement(params, data.get("id"))
    elif method == "ChangePassword":
        return change_password(params, data.get("id"))
    else:
        return jsonify({"error": {"code": -32601, "message": "Method not found"}})

def check_perform(params, req_id):
    account = params.get("account", {}).get("account")
    amount = params.get("amount")
    if account != "7":
        return jsonify({"id": req_id, "error": ERRORS['ORDER_NOT_FOUND']})
    if amount != 56000:
        return jsonify({"id": req_id, "error": ERRORS['INVALID_AMOUNT']})
    return jsonify({"id": req_id, "result": {"allow": True}})

def create_transaction(params, req_id):
    trans_id = params.get("id")
    account = params.get("account", {}).get("account")
    amount = params.get("amount")

    if trans_id in transactions:
        return jsonify({"id": req_id, "result": transactions[trans_id]})

    if account != "7":
        return jsonify({"id": req_id, "error": ERRORS['ORDER_NOT_FOUND']})
    if amount != 56000:
        return jsonify({"id": req_id, "error": ERRORS['INVALID_AMOUNT']})

    transaction_data = {
        "create_time": int(datetime.now().timestamp() * 1000),
        "transaction": str(uuid.uuid4()),
        "state": 1
    }
    transactions[trans_id] = transaction_data
    return jsonify({"id": req_id, "result": transaction_data})

def perform_transaction(params, req_id):
    trans_id = params.get("id")
    if trans_id not in transactions:
        return jsonify({"id": req_id, "error": ERRORS['ORDER_NOT_FOUND']})

    transactions[trans_id]["state"] = 2
    transactions[trans_id]["perform_time"] = int(datetime.now().timestamp() * 1000)
    return jsonify({"id": req_id, "result": transactions[trans_id]})

def cancel_transaction(params, req_id):
    trans_id = params.get("id")
    reason = params.get("reason", 0)
    if trans_id not in transactions:
        return jsonify({"id": req_id, "error": ERRORS['ORDER_NOT_FOUND']})

    transactions[trans_id]["state"] = -2
    transactions[trans_id]["cancel_time"] = int(datetime.now().timestamp() * 1000)
    transactions[trans_id]["reason"] = reason
    return jsonify({"id": req_id, "result": transactions[trans_id]})

def check_transaction(params, req_id):
    trans_id = params.get("id")
    if trans_id not in transactions:
        return jsonify({"id": req_id, "error": ERRORS['ORDER_NOT_FOUND']})
    return jsonify({"id": req_id, "result": transactions[trans_id]})

def get_statement(params, req_id):
    return jsonify({"id": req_id, "result": list(transactions.values())})

def change_password(params, req_id):
    return jsonify({"id": req_id, "result": {"success": True}})

if __name__ == "__main__":
import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=True)
