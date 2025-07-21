import os
import json
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from db_logger import DBLogger


print(">>>> INIT DE LICENSE_SERVER !!!!!!!")
app = Flask(__name__)
db_logger = DBLogger()
load_dotenv()
admin_password = os.getenv("ADMIN_PASSWORD")
USER_KEYS_DIR = os.environ.get("USER_KEYS_DIR", "./user_keys")
TARIFF_TYPES = json.loads(os.getenv("TARIFF_TYPES_JSON", '{}'))  # dict of key: label
LICENSES_FILE = "/data/licenses.json"


@app.route("/download_logs", methods=["GET"])
def download_logs():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    import io, csv
    from flask import Response

    logs = db_logger.all_logs()  # Ajoute cette méthode à ta classe DBLogger si besoin
    if not logs:
        return Response("Aucune donnée.", mimetype="text/plain")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=logs[0].keys())
    writer.writeheader()
    writer.writerows(logs)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-disposition": "attachment; filename=logs.csv"}
    )


@app.route("/get_tariff_types", methods=["GET"])
def get_tariff_types():
    # TARIFF_TYPES est déjà chargé depuis l'env au démarrage du serveur
    return jsonify(TARIFF_TYPES)

def user_file_path(username):
    return os.path.join(USER_KEYS_DIR, f"{username}.json")


def load_licenses():
    if os.path.exists(LICENSES_FILE):
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_licenses():
    with open(LICENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=2, ensure_ascii=False)

licenses = load_licenses()
app.licenses = licenses

@app.route("/")
def home():
    return "🎉 Bienvenue sur l’API de facturation/dette. Tout fonctionne!"

import os
import json

TARIFF_TYPES = json.loads(os.getenv("TARIFF_TYPES_JSON", '{}'))

@app.route("/add_agency", methods=["POST"])
def add_agency():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Invalid or empty JSON"}), 400

    agency_name = data.get("agency_name")
    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency_name"}), 400

    if agency_name in licenses:
        return jsonify({"success": False, "error": "Agency already exists"}), 409

    try:
        agency_entry = {"debt": 0}
        for key in TARIFF_TYPES:
            agency_entry[key] = float(data.get(key, 0))
        licenses[agency_name] = agency_entry
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid tariff value: {e}"}), 400

    save_licenses()
    return jsonify({"success": True, "message": f"Agency '{agency_name}' added."})


@app.route("/charge", methods=["POST"])
def charge():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    client = auth.split("Bearer ")[1].strip()
    agency_info = licenses.get(client)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    data = request.get_json()
    service = data.get("service")
    order = data.get("order", "")
    user = data.get("user", "")
    filename = data.get("filename", "")
    words = data.get("words", 0)
    tariff = None

    # Si les noms ne sont pas là, fallback:
    if words is None:
        if service == "valuechecker":
            words = data.get("raw_word_count", 0)
        else:
            words = data.get("weighted_word_count", 0)

    # Chercher le tarif depuis la config agence
    tariff = agency_info.get(service)
    if tariff is None:
        return jsonify({"success": False, "error": f"No tariff set for type {service}"}), 400

    # Calcul du montant
    amount = round(words * tariff, 2)
    agency_info["debt"] = agency_info.get("debt", 0) + amount
    balance = agency_info["debt"]
    save_licenses()

    # Log
    db_logger.log(
        client=client,
        service=service,
        order=order,
        user=user,
        filename=filename,
        words=words,
        tariff=tariff,
        amount=amount,
        balance=balance
    )

    return jsonify({
        "success": True,
        "debited": amount,
        "new_debt": balance,
        "tariff": tariff
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
    db_logger.log(
        client=agency_name,
        service="payment",
        order="",
        user="",
        filename="",
        words=0,
        tariff=0,
        amount=-payment,
        balance=agency_info["debt"]
    )

    return jsonify({
        "success": True,
        "new_debt": agency_info["debt"]
    })

@app.route("/get_debt", methods=["POST"])
def get_debt():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    client = auth.split("Bearer ")[1].strip()

    agency_info = licenses.get(client)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404
    debt = agency_info.get("debt", 0)

    # DRY: retourner tous les tarifs connus côté config/env
    tariffs = {
        key: agency_info.get(key, "")
        for key in TARIFF_TYPES
    }

    greeting = agency_info.get("greeting", "")
    disabled_items = agency_info.get("disabled_items", "")

    return jsonify({
        "success": True,
        "debt": debt,
        "tariffs": tariffs,
        "greeting": greeting,
        "disabled_items": disabled_items,
    })

@app.route("/list_agencies", methods=["GET"])
def list_agencies():
    return jsonify(list(licenses.keys()))



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
    print("DATA:", data)
    agency_name = data.get("agency_name")
    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency name"}), 400

    agency_info = licenses.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    try:
        for key in TARIFF_TYPES:
            if key in data and data[key] is not None:
                agency_info[key] = float(data[key])
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid tariff value: {e}"}), 400

    if "greeting" in data:
        agency_info["greeting"] = data["greeting"]

    # Si une liste d’objets à désactiver est envoyée, on l’enregistre
    disabled = data.get("disabled_items", "")
    agency_info["disabled_items"] = disabled

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

from jargonnaire_routes import jargonnaire_blueprint
app.register_blueprint(jargonnaire_blueprint, url_prefix='/jargonnaire')

print("\n======= ROUTES FLASK =======")
for rule in app.url_map.iter_rules():
    print(rule)
print("============================\n")


def clean_none_values(logs):
    cleaned = []
    for row in logs:
        cleaned_row = {k if k is not None else "": v if v is not None else "" for k, v in row.items()}
        cleaned.append(cleaned_row)
    return cleaned

@app.route("/history", methods=["GET"])
def get_agency_history():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403
    agency = auth.split("Bearer ")[1].strip()

    history = db_logger.history(agency)
    return jsonify({"success": True, "history": history})


@app.route("/delete_transactions", methods=["POST"])
def delete_transactions():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    start = data.get("start_timestamp")
    end = data.get("end_timestamp")

    if start is None or end is None:
        return jsonify({"success": False, "error": "Missing timestamps"}), 400

    db_logger.delete_transactions_between(start, end)
    return jsonify({"success": True, "message": "Transactions supprimées."})


@app.route("/reset_logs", methods=["POST"])
def reset_logs():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        db_logger.reset()
        return jsonify({"success": True, "message": "Logs réinitialisés."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
