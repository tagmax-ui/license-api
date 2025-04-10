from flask import Flask, request, jsonify
from datetime import datetime
import os

# Import the ExcelLogger class from licence_manager.py
from licence_manager import ExcelLogger

app = Flask(__name__)

# Dummy licenses dictionary and save_licenses() function for demonstration.
licenses = {
    "example_agency": {
        "matrix_balance": 5000,
        "weighter_balance": 3000
    }
}


def save_licenses():
    # Dummy function to simulate persistence.
    pass


# Re-use the global ExcelLogger instance from licence_manager.py.
excel_logger = ExcelLogger()


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
    excel_logger.log(client, balance_type, item_name, -abs(units))

    return jsonify({
        "success": True,
        "remaining": agency_info[balance_type]
    })


if __name__ == "__main__":
    app.run(debug=True)
