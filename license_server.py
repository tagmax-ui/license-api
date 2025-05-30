import os
import json
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv

# Logger CSV pour historique (simple exemple – à adapter à ta classe existante)
import csv
from datetime import datetime

class CSVLogger:
    def __init__(self, file):
        self.file = file
        # S'assurer que le fichier existe avec en-têtes
        if not os.path.exists(self.file):
            with open(self.file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "agency", "action", "item_name", "amount", "word_count", "tariff", "tariff_type"
                ])

    def log(self, agency, action, item_name, amount, word_count=None, tariff=None, tariff_type=None):
        with open(self.file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(), agency, action, item_name, amount, word_count, tariff, tariff_type
            ])


app = Flask(__name__)
load_dotenv()
admin_password = os.getenv("ADMIN_PASSWORD")
csv_logger = CSVLogger(file="logs.csv")  # Mets ton chemin absolu si besoin

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
    agency_name = data.get("agency_name")
    weighter_tariff = data.get("weighter_tariff", 0.019)
    terminology_tariff = data.get("terminology_tariff", 0.025)
    pretranslation_tariff = data.get("pretranslation_tariff", 0.012)

    if not agency_name:
        return jsonify({"success": False, "error": "Missing agency_name"}), 400

    if agency_name in licenses:
        return jsonify({"success": False, "error": "Agency already exists"}), 409

    licenses[agency_name] = {
        "debt": 0,
        "weighter_tariff": weighter_tariff,
        "terminology_tariff": terminology_tariff,
        "pretranslation_tariff": pretranslation_tariff
    }
    save_licenses()
    return jsonify({"success": True, "message": f"Agency '{agency_name}' added."})

@app.route("/use_words", methods=["POST"])
def use_words():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"success": False, "error": "Missing or invalid token"}), 403

    client = auth.split("Bearer ")[1].strip()
    agency_info = licenses.get(client)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    data = request.get_json()
    word_count = data.get("word_count", 0)
    tariff_type = data.get("tariff_type")  # "weighter", "terminology", "pretranslation"
    item_name = data.get("item_name", "")

    valid_tariffs = {"weighter", "terminology", "pretranslation"}
    if tariff_type not in valid_tariffs:
        return jsonify({"success": False, "error": "Invalid tariff type"}), 400

    tariff_key = f"{tariff_type}_tariff"
    tariff = agency_info.get(tariff_key)
    if tariff is None:
        return jsonify({"success": False, "error": f"No tariff set for type {tariff_type}"}), 400

    cost = word_count * tariff
    agency_info["debt"] = agency_info.get("debt", 0) + cost
    save_licenses()

    csv_logger.log(client, "debt_increase", item_name, cost, word_count=word_count, tariff=tariff, tariff_type=tariff_type)

    return jsonify({
        "success": True,
        "debited": cost,
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

    agency_name = auth.split("Bearer ")[1].strip()
    agency_info = licenses.get(agency_name)
    if not agency_info:
        return jsonify({"success": False, "error": "Agency not found"}), 404

    return jsonify({
        "success": True,
        "debt": agency_info.get("debt", 0),
        "weighter_tariff": agency_info.get("weighter_tariff", 0),
        "terminology_tariff": agency_info.get("terminology_tariff", 0),
        "pretranslation_tariff": agency_info.get("pretranslation_tariff", 0)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
