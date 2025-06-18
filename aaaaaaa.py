#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

# Charge .env si besoin
load_dotenv()

# URL de votre endpoint
API_URL_LIST_AGENCIES = os.getenv("API_URL_LIST_AGENCIES", "https://license-api-h5um.onrender.com/list_agencies")

def main():
    try:
        resp = requests.get(API_URL_LIST_AGENCIES)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Erreur HTTP : {e}")
        return

    try:
        tokens = resp.json()
    except ValueError:
        print("❌ La réponse n'est pas du JSON valide :", resp.text)
        return

    if not tokens:
        print("⚠️  Aucune agence trouvée.")
    else:
        print("Tokens (noms d'agences) :")
        for t in tokens:
            print(f" - {t}")

if __name__ == "__main__":
    main()
