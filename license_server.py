import os
import json
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from logger_utils import CSVLogger


app = Flask(__name__)
load_dotenv()
admin_password = os.getenv("ADMIN_PASSWORD")
csv_logger = CSVLogger(file="logs.csv")  # Mets ton chemin absolu si besoin
USER_KEYS_DIR = os.environ.get("USER_KEYS_DIR", "./user_keys")
def user_file_path(username):
    return os.path.join(USER_KEYS_DIR, f"{username}.json")
LICENSES_FILE = "licenses.json"  # Mets ton chemin absolu si besoin

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
    return "🎉 Bienvenue sur l’API de facturation/dette. Tout fonctionne!"

@app.route("/add_agency", methods=["POST"])
def add_agency():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    print("==> DONNÉES REÇUES:", data)
    if not data:
        return jsonify({"success": False, "error": "Invalid or empty JSON"}), 400

    agency_name = data.get("agency_name")
    weighter_tariff = data.get("weighter_tariff", 0.019)
    terminology_tariff = data.get("terminology_tariff", 0.025)
    pretranslation_tariff = data.get("pretranslation_tariff", 0.012)

    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency_name"}), 400

    if agency_name in licenses:
        return jsonify({"success": False, "error": "Agency already exists"}), 409

    try:
        licenses[agency_name] = {
            "debt": 0,
            "weighter_tariff": float(weighter_tariff),
            "terminology_tariff": float(terminology_tariff),
            "pretranslation_tariff": float(pretranslation_tariff)
        }
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid tariff value: {e}"}), 400

    save_licenses()
    return jsonify({"success": True, "message": f"Agency '{agency_name}' added."})

@app.route("/charge", methods=["POST"])
def charge():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    agency_name = auth.split("Bearer ")[1].strip()
    agency_info = licenses.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    data = request.get_json()
    raw_word_count = data.get("raw_word_count", 0)
    weighted_word_count = data.get("weighted_word_count", 0)
    tariff_type = data.get("tariff_type")  # "weighter", "terminology", "pretranslation"
    order_number = data.get("order_number", "")

    valid_tariffs = {"weighter", "terminology", "pretranslation"}
    if tariff_type not in valid_tariffs:
        return jsonify({"success": False, "error": "Invalid tariff type"}), 400

    tariff_key = f"{tariff_type}_tariff"
    tariff = agency_info.get(tariff_key)
    if tariff is None:
        return jsonify({"success": False, "error": f"No tariff set for type {tariff_type}"}), 400

    amount = round(weighted_word_count * tariff, 2)
    agency_info["debt"] = agency_info.get("debt", 0) + amount
    save_licenses()

    csv_logger.log(agency=agency_name,
                   order_number=order_number,
                   raw_words=raw_word_count,
                   weighted_words=weighted_word_count,
                   tariff_type=tariff_type,
                   tariff=tariff,
                   amount=amount)

    return jsonify({
        "success": True,
        "debited": amount,
        "new_debt": agency_info["debt"]
    })

@app.route("/register_payment", methods=["POST"])
def register_payment():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    agency_name = data.get("agency_name")
    payment = data.get("amount")

    agency_info = licenses.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    agency_info["debt"] = max(agency_info.get("debt", 0) - payment, 0)
    save_licenses()
    csv_logger.log(agency_name, "payment", "", -payment)

    return jsonify({
        "success": True,
        "new_debt": agency_info["debt"]
    })

@app.route("/get_debt", methods=["POST"])
def get_debt():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    client = auth.split("Bearer ")[1].strip()   # <-- MANQUAIT DANS TON CODE

    agency_info = licenses.get(client)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404
    debt = agency_info.get("debt", 0)
    return jsonify({
        "success": True,
        "debt": debt,
        "tariffs": {
            "weighter_tariff": agency_info.get("weighter_tariff", ""),
            "terminology_tariff": agency_info.get("terminology_tariff", ""),
            "pretranslation_tariff": agency_info.get("pretranslation_tariff", ""),
        }
    })

@app.route("/list_agencies", methods=["GET"])
def list_agencies():
    return jsonify(list(licenses.keys()))

@app.route("/download_logs", methods=["GET"])
def download_logs():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        csv_path = "logs.csv"
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

@app.route("/delete_agency", methods=["POST"])
def delete_agency():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    agency_name = data.get("agency_name")
    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency_name"}), 400

    if agency_name not in licenses:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    del licenses[agency_name]
    save_licenses()

    return jsonify({"success": True, "message": f"Agency '{agency_name}' deleted."})

@app.route("/update_tariffs", methods=["POST"])
def update_tariffs():
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {os.environ.get('ADMIN_PASSWORD')}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    print("DATA:", data)  # <-- pour voir ce qui arrive
    agency_name = data.get("agency_name")
    weighter_tariff = data.get("weighter_tariff")
    terminology_tariff = data.get("terminology_tariff")
    pretranslation_tariff = data.get("pretranslation_tariff")
    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency name"}), 400

    agency_info = licenses.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    try:
        if weighter_tariff is not None:
            agency_info["weighter_tariff"] = float(weighter_tariff)
        if terminology_tariff is not None:
            agency_info["terminology_tariff"] = float(terminology_tariff)
        if pretranslation_tariff is not None:
            agency_info["pretranslation_tariff"] = float(pretranslation_tariff)
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid tariff value: {e}"}), 400

    save_licenses()
    return jsonify({"success": True, "agency_info": agency_info})

@app.route("/register_user", methods=["POST"])
def register_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "Nom d'utilisateur et mot de passe obligatoires."})
    if os.path.exists(user_file_path(username)):
        return jsonify({"success": False, "error": "Nom d'utilisateur déjà utilisé."})

    user_data = {
        "username": username,
        "mot_de_passe": password,
    }
    for key, value in data.items():
        if key not in ("username", "password"):
            user_data[key] = value

    os.makedirs(USER_KEYS_DIR, exist_ok=True)
    with open(user_file_path(username), "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    return jsonify({"success": True, "message": "Utilisateur créé."})

@app.route('/get_user', methods=['POST'])
def get_user():
    username = request.json.get("username")
    password = request.json.get("password")
    filepath = user_file_path(username)
    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "User not found"})
    with open(filepath, encoding="utf-8") as f:
        user_data = json.load(f)
    if user_data.get("mot_de_passe") != password:
        return jsonify({"success": False, "error": "Bad password"})
    return jsonify({"success": True, "user": user_data})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
