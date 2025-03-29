import os
from flask import Flask, request, jsonify

app = Flask(__name__)
admin_password = os.getenv("ADMIN_SECRET")

# Fake in-memory "database" of licenses
licenses = {
    "agency123": {
        "remaining": 150000,
        "active": True
    },
    "agencyXYZ": {
        "remaining": 5000,
        "active": False
    }
}

@app.route("/")
def home():
    return "🎉 Bienvenue sur l’API de licence. Tout fonctionne!"

@app.route("/use_credits", methods=["POST"])
def use_credits():
    data = request.get_json()
    license_id = data.get("license_id")
    units = data.get("units", 1000)

    license_info = licenses.get(license_id)

    if not license_info:
        return jsonify({"success": False, "error": "License not found"}), 404

    if not license_info["active"]:
        return jsonify({"success": False, "error": "License inactive"}), 403

    if license_info["remaining"] < units:
        return jsonify({"success": False, "error": "Insufficient credits"}), 402

    license_info["remaining"] -= units
    return jsonify({
        "success": True,
        "remaining": license_info["remaining"]
    })

@app.route("/modify_credits", methods=["POST"])
def modify_credits():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {admin_password}":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    license_id = data.get("license_id")
    amount = data.get("amount", 0)

    license_info = licenses.get(license_id)
    if not license_info:
        return jsonify({"success": False, "error": "License not found"}), 404

    license_info["remaining"] += amount

    # ✅ Affichage dans les logs de Render
    print(f"✔ Crédits modifiés: {amount} pour {license_id}. Nouveau solde: {license_info['remaining']}")

    return jsonify({
        "success": True,
        "new_balance": license_info["remaining"]
    })


@app.route("/list_agencies", methods=["GET"])
def list_agencies():
    return jsonify(list(licenses.keys()))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
