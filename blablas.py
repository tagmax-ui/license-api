import requests

API_URL = "https://license-api-h5um.onrender.com/get_balance"
SECRET = "TOPSECRET123"  # Remplace par ton vrai mot de passe admin si besoin
AGENCY_NAME = "test_agency_123"  # Remplace par l’agence que tu veux tester

headers = {
    "Authorization": f"Bearer {SECRET}"
}
data = {
    "license_id": AGENCY_NAME
}

try:
    response = requests.post(API_URL, json=data, headers=headers)
    print("✅ Code HTTP :", response.status_code)
    print("🛰 Contenu brut de la réponse :", response.text)
    result = response.json()

    if result.get("success"):
        print(f"✔ Solde matriciel : {result['matrix_balance']} crédits")
        print(f"✔ Solde pondérateur : {result['web_weighter_balance']} crédits")
    else:
        print("❌ Erreur retournée :", result.get("error"))
except Exception as e:
    print("❌ Erreur réseau :", e)
