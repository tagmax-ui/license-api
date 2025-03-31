import requests

url = "https://license-api-h5um.onrender.com/add_agency"
headers = {
    "Authorization": "Bearer TOPSECRET123",
    "Content-Type": "application/json"
}
data = {
    "agency_name": "test_agency_abcd",
    "matrix_balance": 100000,
    "web_weighter_balance": 50000
}

response = requests.post(url, json=data, headers=headers)

print("✅ Code HTTP :", response.status_code)
print("🛰 Contenu brut de la réponse :", response.text)

try:
    result = response.json()
    if result.get("success"):
        print("🎉 Ajout réussi :", result.get("message"))
    else:
        print("❌ Échec :", result.get("error"))
except Exception as e:
    print("⚠️ Erreur JSON :", e)
