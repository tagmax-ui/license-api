import requests

def add_credits():
    url = "https://license-api-h5um.onrender.com/admin_add_credits_xyz"
    data = {
        "license_id": "agency123",
        "amount": 50000,
        "secret": "TOPSECRET123"
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            print(f"✅ Crédit ajouté avec succès!")
            print(f"Nouveau solde : {result['new_balance']} crédits")
        else:
            print(f"❌ Échec : {result.get('error')}")

    except requests.RequestException as e:
        print(f"❌ Erreur réseau : {e}")

if __name__ == "__main__":
    add_credits()
