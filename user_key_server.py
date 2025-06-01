from flask import Flask, request, jsonify
import os, json

USER_KEYS_DIR = os.environ.get("USER_KEYS_DIR", "./user_keys")

app = Flask(__name__)

def user_file_path(username):
    return os.path.join(USER_KEYS_DIR, f"{username}.json")

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
    app.run(debug=True, port=10000)  # Render va overrider le port
