from flask import Flask, request, jsonify
import base64
import datetime
import os

app = Flask(__name__)

MERCHANT_ID = "6888b945cab302211ad14048"
TEST_KEY = "MgQkrp%EmzazcRq5GWp#KxiTQgYu1@Ymrs87"

COURSES = {
    "HRSTR": 3_000_000,
    "HRFIN": 3_000_000,
    "HRANA": 3_000_000,
    "SENHR": 8_000_000
}

transactions = {}
saved_create_results = {}  # <--- для хранения минимального ответа на CreateTransaction

def get_now_timestamp():
    return int(datetime.datetime.now().timestamp() * 1000)

def unauthorized():
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

@app.route("/", methods=["POST"])
def merchant_api():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        return unauthorized()

    try:
        decoded = base64.b64decode(auth[6:]).decode()
        username, password = decoded.split(":", 1)
    except Exception:
        return unauthorized()

    if password != TEST_KEY:
        return unauthorized()

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
        return jsonify({
            "id": _id,
            "error": {
                "code": -32601,
                "message": {
                    "ru": "Метод не найден",
                    "uz": "Ushbu metod topilmadi",
                    "en": "Method not found"
                }
            }
        })

def check_perform_transaction(_id, params):
    account = params.get("account", {})
    order_id = account.get("order_id")
    amount = params.get("amount")

    if not order_id:
        return jsonify({"id": _id, "error": {"code": -31050, "message": {
            "ru": "Отсутствует order_id", "uz": "Order_id yo'q", "en": "Missing order_id"}}})

    course_key = order_id.split("-")[0]
    if course_key not in COURSES:
        return jsonify({"id": _id, "error": {"code": -31050, "message": {
            "ru": "Неверный order_id", "uz": "Noto‘g‘ri order_id", "en": "Invalid order_id"}}})

    expected_amount = COURSES[course_key] * 100
    if amount != expected_amount:
        return jsonify({"id": _id, "error": {"code": -31001, "message": {
            "ru": "Сумма не совпадает", "uz": "Summasi mos emas", "en": "Amount mismatch"}}})

    for tx in transactions.values():
        if tx["account"]["order_id"] == order_id:
            if tx["state"] == 1:
                return jsonify({"id": _id, "error": {"code": -31099, "message": {
                    "ru": "Счёт занят", "uz": "Hisob band", "en": "Account already in use"}}})
            elif tx["state"] in (2, -1):
                return jsonify({"id": _id, "error": {"code": -31052, "message": {
                    "ru": "Счёт завершён", "uz": "Hisob tugagan", "en": "Account closed"}}})

    receipt_detail = {
        "receipt_type": 0,
        "items": [{
            "title": {
                "HRSTR": "HR стратегия",
                "HRFIN": "HR финансы",
                "HRANA": "HR аналитика",
                "SENHR": "Senior HR"
            }.get(course_key, "Курс TOP HR"),
            "price": expected_amount,
            "count": 1,
            "code": "10899002001000000",
            "vat_percent": 0,
            "package_code": ""
        }]
    }

    return jsonify({"id": _id, "result": {"allow": True, "detail": receipt_detail}})

def create_transaction(_id, params):
    trans_id = params.get("id")
    time = params.get("time")
    account = params.get("account", {})
    order_id = account.get("order_id")
    amount = params.get("amount")

    if not order_id:
        return jsonify({"id": _id, "error": {"code": -31050, "message": {
            "ru": "Отсутствует order_id", "uz": "Order_id yo'q", "en": "Missing order_id"}}})

    course_key = order_id.split("-")[0]
    if course_key not in COURSES:
        return jsonify({"id": _id, "error": {"code": -31050, "message": {
            "ru": "Неверный order_id", "uz": "Noto‘g‘ri order_id", "en": "Invalid order_id"}}})

    expected_amount = COURSES[course_key] * 100
    if int(amount) != int(expected_amount):
        return jsonify({"id": _id, "error": {"code": -31001, "message": {
            "ru": "Сумма не совпадает", "uz": "Summasi mos emas", "en": "Amount mismatch"}}})

    if trans_id in saved_create_results:
        return jsonify(saved_create_results[trans_id])

    for tx in transactions.values():
        if tx["account"]["order_id"] == order_id and tx["state"] == 1:
            return jsonify({"id": _id, "error": {"code": -31099, "message": {
                "ru": "Счёт уже занят", "uz": "Hisob band qilingan", "en": "Transaction already exists for this account"}}})

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

    saved_create_results[trans_id] = {
        "id": _id,
        "result": {
            "create_time": time,
            "transaction": trans_id,
            "state": 1
        }
    }

    return jsonify(saved_create_results[trans_id])

def perform_transaction(_id, params):
    trans_id = params.get("id")
    transaction = transactions.get(trans_id)

    if not transaction:
        return jsonify({
            "id": _id,
            "error": {
                "code": -31003,
                "message": {
                    "ru": "Транзакция не найдена",
                    "uz": "Tranzaksiya topilmadi",
                    "en": "Transaction not found"
                }
            }
        })

    if transaction["state"] == -1:
        return jsonify({
            "id": _id,
            "error": {
                "code": -31008,
                "message": {
                    "ru": "Транзакция отменена",
                    "uz": "Tranzaksiya bekor qilingan",
                    "en": "Transaction cancelled"
                }
            }
        })

    # если уже проведена — возвращаем короткий результат
    if transaction["state"] == 2:
        return jsonify({
            "id": _id,
            "result": {
                "state": 2,
                "perform_time": transaction["perform_time"],
                "transaction": trans_id
            }
        })

    # впервые проводим
    transaction["perform_time"] = get_now_timestamp()
    transaction["state"] = 2

    return jsonify({
        "id": _id,
        "result": {
            "state": 2,
            "perform_time": transaction["perform_time"],
            "transaction": trans_id
        }
    })

def cancel_transaction(_id, params):
    trans_id = params.get("id")
    reason = params.get("reason")
    transaction = transactions.get(trans_id)

    if not transaction:
        return jsonify({"id": _id, "error": {"code": -31003, "message": {
            "ru": "Транзакция не найдена", "uz": "Tranzaksiya topilmadi", "en": "Transaction not found"}}})

    transaction["cancel_time"] = get_now_timestamp()
    transaction["state"] = -1
    transaction["reason"] = reason

    return jsonify({
        "id": _id,
        "result": {
            "transaction": trans_id,
            "cancel_time": transaction["cancel_time"],
            "state": transaction["state"]
        }
    })

def check_transaction(_id, params):
    trans_id = params.get("id")
    transaction = transactions.get(trans_id)

    if not transaction:
        return jsonify({"id": _id, "error": {"code": -31003, "message": {
            "ru": "Транзакция не найдена", "uz": "Tranzaksiya topilmadi", "en": "Transaction not found"}}})

    return jsonify({"id": _id, "result": {"transaction": trans_id, **transaction}})

def get_statement(_id, params):
    from_time = params.get("from")
    to_time = params.get("to")

    filtered = [
        tx for tx in transactions.values()
        if from_time <= int(tx["create_time"]) <= to_time
    ]
    return jsonify({"id": _id, "result": filtered})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
