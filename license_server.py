from flask import Flask, request, jsonify

app = Flask(__name__)

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

    # Deduct usage
    license_info["remaining"] -= units
    return jsonify({
        "success": True,
        "remaining": license_info["remaining"]
    })

if __name__ == "__main__":
    app.run(port=5000)
