from flask import Flask, request, jsonify
import base64
import datetime

app = Flask(__name__)

MERCHANT_ID = "6888b945cab302211ad14048"
TEST_KEY = "MgQkrp%EmzazcRq5GWp#KxiTQgYu1@Ymrs87"
AUTH_HEADER = "Basic " + base64.b64encode(f"{MERCHANT_ID}:{TEST_KEY}".encode()).decode()

COURSES = {
    "HRSTR": 3_000_000,
    "HRFIN": 3_000_000,
    "HRAN":  3_000_000,
    "SENHR": 8_000_000
}

transactions = {}

def get_now_timestamp():
    return int(datetime.datetime.now().timestamp() * 1000)

@app.route("/", methods=["POST"])
def merchant_api():
    auth = request.headers.get("Authorization")
    if auth != AUTH_HEADER:
        return jsonify({
    "error": {
        "code": -32504,
        "message": {
            "ru": "Неверная авторизация",
            "uz": "Noto‘g‘ri avtorizatsiya",
            "en": "Invalid authorization"
        }
    }
})


    data = request.get_json()
    method = data.get("method")
    params = data.get("params", {})
    _id = data.get("id")

    if method == "CheckPerformTransaction":
        return check_perform_transaction(_id, params)
    elif method == "CreateTransaction":
        return create_transaction(_id, params)
    elif method == "PerformTransaction":
        return perform_transaction(_id, params)
    elif method == "CancelTransaction":
        return cancel_transaction(_id, params)
    elif method == "CheckTransaction":
        return check_transaction(_id, params)
    elif method == "GetStatement":
        return get_statement(_id, params)
    else:
        return jsonify({"id": _id, "error": {"code": -32601, "message": {"ru": "Метод не найден"}}})

def check_perform_transaction(_id, params):
    account = params.get("account", {})
    order_id = account.get("order_id")
    amount = params.get("amount")

    if not order_id or not any(order_id.startswith(key) for key in COURSES):
        return jsonify({"id": _id, "error": {"code": -31050, "message": {"ru": "Неверный order_id"}}})

    course_key = order_id[:5]
    expected_amount = COURSES[course_key] * 100
    if amount != expected_amount:
        return jsonify({"id": _id, "error": {"code": -31001, "message": {"ru": "Сумма не совпадает"}}})

    receipt_detail = {
        "receipt_type": 0,
        "items": [
            {
                "title": {
                    "HRSTR": "HR стратегия",
                    "HRFIN": "HR финансы",
                    "HRAN": "HR аналитика",
                    "SENHR": "Senior HR"
                }.get(course_key, "Курс TOP HR"),
                "price": expected_amount,
                "count": 1,
                "code": "10899002001000000",
                "vat_percent": 0,
                "package_code": ""
            }
        ]
    }

    return jsonify({"id": _id, "result": {"allow": True, "detail": receipt_detail}})

def create_transaction(_id, params):
    trans_id = params.get("id")
    time = params.get("time")
    account = params.get("account", {})
    order_id = account.get("order_id")
    amount = params.get("amount")

    if trans_id in transactions:
        return jsonify({"id": _id, "result": transactions[trans_id]})

    transactions[trans_id] = {
        "create_time": time,
        "perform_time": 0,
        "cancel_time": 0,
        "id": trans_id,
        "state": 1,
        "reason": None,
        "amount": amount,
        "account": account
    }
    return jsonify({"id": _id, "result": transactions[trans_id]})

def perform_transaction(_id, params):
    trans_id = params.get("id")
    transaction = transactions.get(trans_id)

    if not transaction:
        return jsonify({"id": _id, "error": {"code": -31003, "message": {"ru": "Транзакция не найдена"}}})

    if transaction["state"] == 2:
        return jsonify({"id": _id, "result": transaction})

    transaction["perform_time"] = get_now_timestamp()
    transaction["state"] = 2
    return jsonify({"id": _id, "result": transaction})

def cancel_transaction(_id, params):
    trans_id = params.get("id")
    reason = params.get("reason")
    transaction = transactions.get(trans_id)

    if not transaction:
        return jsonify({"id": _id, "error": {"code": -31003, "message": {"ru": "Транзакция не найдена"}}})

    transaction["cancel_time"] = get_now_timestamp()
    transaction["state"] = -1
    transaction["reason"] = reason
    return jsonify({"id": _id, "result": transaction})

def check_transaction(_id, params):
    trans_id = params.get("id")
    transaction = transactions.get(trans_id)

    if not transaction:
        return jsonify({"id": _id, "error": {"code": -31003, "message": {"ru": "Транзакция не найдена"}}})

    return jsonify({"id": _id, "result": transaction})

def get_statement(_id, params):
    from_time = params.get("from")
    to_time = params.get("to")

    filtered = [
        tx for tx in transactions.values()
        if from_time <= int(tx["create_time"]) <= to_time
    ]
    return jsonify({"id": _id, "result": filtered})
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)    
