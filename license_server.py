import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
admin_password = os.getenv("ADMIN_SECRET")

# 🔁 Chargement et sauvegarde des licences persistantes
LICENSES_FILE = "licenses.json"

def load_licenses():
    if os.path.exists(LICENSES_FILE):
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_licenses():
    with open(LICENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=2, ensure_ascii=False)

licenses = load_licenses()

@app.route("/")
def home():
    return "🎉 Bienvenue sur l’API de licence. Tout fonctionne!"

@app.route("/use_credits", methods=["POST"])
def use_credits():
    data = request.get_json()
    agency_name = data.get("agency_name")
    units = data.get("units", 1000)

    agency_info = licenses.get(agency_name)

    if not agency_info:
        return jsonify({"success": False, "error": "License not found"}), 404

    if agency_info.get("matrix_balance", 0) < units:
        return jsonify({"success": False, "error": "Insufficient credits"}), 402

    agency_info["matrix_balance"] -= units
    save_licenses()
    return jsonify({
        "success": True,
        "matrix_balance": agency_info["matrix_balance"]
    })

@app.route("/modify_credits", methods=["POST"])
def modify_credits():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    agency_name = data.get("agency_name")
    amount = data.get("amount", 0)
    balance_type = data.get("balance_type")  # 'matrix_balance' ou 'weighter_balance'

    agency_info = licenses.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "License not found"}), 404

    if balance_type not in ("matrix_balance", "weighter_balance"):
        return jsonify({"success": False, "error": "Invalid balance type"}), 400

    agency_info[balance_type] = agency_info.get(balance_type, 0) + amount

    save_licenses()

    return jsonify({
        "success": True,
        "new_balance": agency_info[balance_type]
    })

@app.route("/list_agencies", methods=["GET"])
def list_agencies():
    return jsonify(list(licenses.keys()))

@app.route("/add_agency", methods=["POST"])
def add_agency():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    agency_name = data.get("agency_name")
    matrix_balance = data.get("matrix_balance", 0)
    weighter_balance = data.get("weighter_balance", 0)

    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency_name"}), 400

    if agency_name in licenses:
        return jsonify({"success": False, "error": "Agency already exists"}), 409

    licenses[agency_name] = {
        "matrix_balance": matrix_balance,
        "weighter_balance": weighter_balance
    }

    save_licenses()

    return jsonify({"success": True, "message": f"Agency '{agency_name}' added."})

@app.route("/reset_all_licenses", methods=["POST"])
def reset_all_licenses():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    licenses.clear()
    save_licenses()

    return jsonify({"success": True, "message": "Toutes les licences ont été supprimées."})


@app.route("/get_balance", methods=["POST"])
def get_balance():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    agency_name = data.get("agency_name")
    agency_info = licenses.get(agency_name)

    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    return jsonify({
        "success": True,
        "matrix_balance": agency_info.get("matrix_balance", 0),
        "weighter_balance": agency_info.get("weighter_balance", 0)
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
