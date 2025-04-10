import os
import json
from flask import Flask, request, jsonify, send_file
from logger_utils import CSVLogger


app = Flask(__name__)
admin_password = os.getenv("ADMIN_PASSWORD")

# 🔁 Chargement et sauvegarde des licences persistantes juste ici.
LICENSES_FILE = "/data/licenses.json"


def load_licenses():
    if os.path.exists(LICENSES_FILE):
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_licenses():
    with open(LICENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=2, ensure_ascii=False)


licenses = load_licenses()


@app.route("/download_logs", methods=["GET"])
def download_logs():
    print("admin_password from env:", admin_password, flush=True)
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        # Définir le chemin du fichier CSV dans le volume persistant :
        csv_path = "/data/logs.csv"
        return send_file(
            csv_path,
            as_attachment=True,
            download_name="logs.csv",
            mimetype="text/csv"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/download_licenses", methods=["GET"])
def download_licenses():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            data = f.read()
        return data, 200, {"Content-Type": "application/json"}
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/")
def home():
    return "🎉 Bienvenue sur l’API de licence. Tout fonctionne!"


@app.route("/use_credits", methods=["POST"])
def use_credits():
    # Get the Bearer token, which also serves as the client (agency) name.
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    client = auth.split("Bearer ")[1].strip()
    agency_info = licenses.get(client)

    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    data = request.get_json()
    units = data.get("units", 1000)
    balance_type = data.get("balance_type", "matrix_balance")  # Default is matrix_balance.
    item_name = data.get("item_name", "")

    if balance_type not in ("matrix_balance", "weighter_balance"):
        return jsonify({"success": False, "error": "Invalid balance type"}), 400

    if agency_info.get(balance_type, 0) < units:
        return jsonify({"success": False, "error": "Insufficient credits"}), 402

    # Deduct the credits.
    agency_info[balance_type] -= units
    save_licenses()

    # Log the transaction using the ExcelLogger from licence_manager.py.
    # For usage, record the units as a negative value.
    CSVLogger.log(client, balance_type, item_name, -abs(units))


    return jsonify({
        "success": True,
        "remaining": agency_info[balance_type]
    })


@app.route("/modify_credits", methods=["POST"])
def modify_credits():
    print("Entering modify_credits", flush=True)
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    data = request.get_json()
    agency_name = data.get("agency_name")
    agency_info = licenses.get(agency_name)

    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    amount = data.get("amount", 0)
    balance_type = data.get("balance_type")

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
    print("Entering get_balance", flush=True)
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    agency_name = auth.split("Bearer ")[1].strip()
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
