import requests
import os


# Remplace par ton URL Render réel
BASE_URL = "https://license-api-h5um.onrender.com"
SECRET = os.getenv("ADMIN_PASSWORD")

def register_user(username, password, **kwargs):
    data = {"username": username, "password": password}
    data.update(kwargs)
    r = requests.post(f"{BASE_URL}/register_user", json=data)
    print("Register user:", r.status_code, r.text)  # Affiche le texte brut
    try:
        print(r.json())
    except Exception as e:
        print(f"Impossible de parser la réponse JSON: {e}")

def get_user(username, password):
    r = requests.post(f"{BASE_URL}/get_user", json={"username": username, "password": password})
    print("Get user:", r.status_code, r.text)  # Affiche le texte brut
    try:
        print(r.json())
    except Exception as e:
        print(f"Impossible de parser la réponse JSON: {e}")

# Exemple d’utilisation :
if __name__ == "__main__":
    register_user("Jessy2", "motdepasse123", user_key_email="jessy@example.com", user_key_full_name="Jessy LaPointe")
    get_user("Jessy", "motdepasse123")
    get_user("Jessy", "fauxmotdepasse")