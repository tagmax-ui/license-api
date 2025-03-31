import requests
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

url = "https://license-api-h5um.onrender.com/reset_all_licenses"
headers = {
    "Authorization": f"Bearer {ADMIN_PASSWORD}"
}

response = requests.post(url, headers=headers)

try:
    result = response.json()
    print("✅ Réponse du serveur :")
    print(result)
except Exception as e:
    print("❌ Erreur :", e)
    print(response.text)
