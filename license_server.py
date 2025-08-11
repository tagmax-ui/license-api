import os
import json
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from db_logger import DBLogger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from lexicon_routes import lexicon_blueprint


print(">>>> INIT DE LICENSE_SERVER !!!!!!!")
app = Flask(__name__)
app.register_blueprint(lexicon_blueprint, url_prefix='/lexicon')
db_logger = DBLogger()
load_dotenv()
admin_password = os.getenv("ADMIN_PASSWORD")
USER_KEYS_DIR = os.environ.get("USER_KEYS_DIR", "./user_keys")
TARIFF_TYPES = json.loads(os.getenv("TARIFF_TYPES_JSON", '{}'))  # dict of key: label
LICENSES_FILE = "/data/licenses.json"


@app.after_request
def add_worker_header(resp):
    try:
        resp.headers["X-Worker-PID"] = str(os.getpid())
    except Exception:
        pass
    return resp

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

TARIFF_TYPES_PATH = os.getenv("TARIFF_TYPES_PATH")
if TARIFF_TYPES_PATH and os.path.exists(TARIFF_TYPES_PATH):
    with open(TARIFF_TYPES_PATH, encoding="utf-8") as f:
        TARIFF_TYPES = json.load(f)
else:
    TARIFF_TYPES = {}


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

    # 🔁 recharge
    current = load_licenses()
    agency_info = current.get(client)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    data = request.get_json()
    service = data.get("service", "")
    order = data.get("order", "")
    profile = data.get("profile", "")
    user = data.get("user", "")
    filename = data.get("filename", "")

    words = data.get("words")
    if words is None:
        words = data.get("raw_word_count" if service == "valuechecker" else "weighted_word_count", 0)
    try:
        words = int(words or 0)
    except Exception:
        words = 0

    tariff = agency_info.get(service, None)
    if not tariff:  # None, "", 0 → gratuit
        amount = 0.0
    else:
        try:
            amount = round(words * float(tariff), 2)
        except Exception:
            amount = 0.0

    agency_info["debt"] = round(agency_info.get("debt", 0) + amount, 2)
    current[client] = agency_info

    save_licenses()  # idem, voir plus bas

    db_logger.log(client=client, service=service, order=order, profile=profile,
                  user=user, filename=filename, words=words, tariff=tariff,
                  amount=amount, balance=agency_info["debt"])

    notify_usage_by_email(client, service, order, user, profile, filename, words, amount, agency_info["debt"])
    return jsonify({"success": True, "debited": amount, "new_debt": agency_info["debt"], "tariff": tariff})



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
        profile="",
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
    # 🔁 recharge depuis disque pour éviter la dérive multi-worker
    current = load_licenses()
    agency_info = current.get(client)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    debt = agency_info.get("debt", 0)

    if TARIFF_TYPES:
        # Remonte toutes les clés connues, même absentes côté agence
        tariffs = {key: agency_info.get(key, "") for key in TARIFF_TYPES}
    else:
        excluded = {"debt", "greeting", "disabled_items"}
        tariffs = {k: v for k, v in agency_info.items() if k not in excluded}

    greeting = agency_info.get("greeting", "")
    disabled_items = agency_info.get("disabled_items", "")

    return jsonify({"success": True, "debt": debt, "tariffs": tariffs,
                    "greeting": greeting, "disabled_items": disabled_items})


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

    print("— update_tariffs() —")
    print("AUTH OK =", auth == f"Bearer {os.environ.get('ADMIN_PASSWORD')}")
    print("TARIFF_TYPES len =", len(TARIFF_TYPES))
    print("TARIFF_TYPES keys sample =", list(TARIFF_TYPES.keys())[:5])
    print("ENV TARIFF_TYPES_PATH =", os.getenv("TARIFF_TYPES_PATH"))
    print("ENV TARIFF_TYPES_JSON present =", bool(os.getenv("TARIFF_TYPES_JSON")))
    print("[STEP1] /update_tariffs called")
    print("[STEP1] len(TARIFF_TYPES) =", len(TARIFF_TYPES))
    print("[STEP1] 'apply_jargonary' in TARIFF_TYPES ->", 'apply_jargonary' in TARIFF_TYPES)
    print("[STEP1] incoming keys (sample) =", list(data.keys())[:8], "... total:", len(data))

    agency_name = data.get("agency_name")

    print("agency_name =", agency_name)
    print("incoming data keys =", sorted(data.keys()))

    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency name"}), 400

    # 🔁 recharge l’état courant (multi-worker safe-ish)
    current = load_licenses()
    agency_info = current.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    candidate_keys = set(TARIFF_TYPES.keys()) | {
        k for k in data.keys() if k not in ("agency_name", "greeting", "disabled_items")
    }

    for key in candidate_keys:
        value = data.get(key, "")
        try:
            agency_info[key] = "" if value in ("", None) else float(value)
        except Exception:
            agency_info[key] = ""

    if "greeting" in data:
        agency_info["greeting"] = data["greeting"]
    agency_info["disabled_items"] = data.get("disabled_items", "")

    current[agency_name] = agency_info
    # 🔒 écriture atomique recommandée
    save_licenses()  # utilise l’objet global `licenses` ? -> remplace par un save de `current` (voir plus bas)

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


@app.route("/send_email", methods=["POST"])
def send_email_route():
    data = request.get_json()
    to = data.get("to")
    subject = data.get("subject")
    content = data.get("content")

    if not all([to, subject, content]):
        return jsonify({"success": False, "error": "Paramètres requis : to, subject, content"}), 400

    status = send_email(to, subject, content)
    if status and status < 300:
        return jsonify({"success": True, "status_code": status})
    return jsonify({"success": False, "error": "Échec de l’envoi"}), 500

def notify_usage_by_email(client, service, order, user, profile, filename, words, amount, balance):
    subject = f"[TAGmax] {client} a utilisé le service {service}"
    html_content = f"""
        <p>L’agence <strong>{client}</strong> vient d’utiliser le service <strong>{service}</strong>.</p>
        <ul>
            <li>Commande : <strong>{order or "(aucun numéro)"}</strong></li>
            <li>Utilisateur : <strong>{user or "(inconnu)"}</strong></li>
            <li>Fichier : <strong>{filename or "(sans nom)"}</strong></li>
            <li>Mots facturés : <strong>{words}</strong></li>
            <li>Montant débité : <strong>{amount:.2f} $</strong></li>
            <li>Dette actuelle : <strong>{balance:.2f} $</strong></li>
        </ul>
    """

    try:
        message = Mail(
            from_email='jessylapointe@gmail.com',  # ton adresse vérifiée SendGrid
            to_emails='jessylapointe@gmail.com',   # destinataire (toi-même)
            subject=subject,
            html_content=html_content
        )
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        print("[Erreur lors de l’envoi du courriel de notification]", e)

def send_email(to_email, subject, html_content):
    try:
        message = Mail(
            from_email='jessylapointe@gmail.com',
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        return response.status_code
    except Exception as e:
        print(f"[Erreur SendGrid] {e}")
        return None


@app.route("/delete_transactions_by_user", methods=["POST"])
def delete_transactions_by_user():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    username = data.get("user")
    if not username:
        return jsonify({"success": False, "error": "Missing user"}), 400

    try:
        # Tu dois ajouter cette méthode à DBLogger si elle n'existe pas.
        deleted_count = db_logger.delete_transactions_by_user(username)
        return jsonify({"success": True, "message": f"{deleted_count} transactions supprimées pour l'utilisateur '{username}'."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/delete_transactions_by_service", methods=["POST"])
def delete_transactions_by_service():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    service = data.get("service")
    if not service:
        return jsonify({"success": False, "error": "Missing service"}), 400

    try:
        deleted_count = db_logger.delete_transactions_by_service(service)
        return jsonify({"success": True, "message": f"{deleted_count} transactions supprimées pour le service '{service}'."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/__diag_ttypes", methods=["GET"])
def __diag_ttypes():
    env_str = os.getenv("TARIFF_TYPES_JSON")
    path = os.getenv("TARIFF_TYPES_PATH")
    return jsonify({
        "ttypes_len": len(TARIFF_TYPES),
        "ttypes_keys_sample": list(TARIFF_TYPES.keys())[:5],
        "has_env": env_str is not None,
        "env_preview": (env_str[:120] + "...") if env_str and len(env_str) > 120 else env_str,
        "path": path,
        "path_exists": (os.path.exists(path) if path else None)
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
