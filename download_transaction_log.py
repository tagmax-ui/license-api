#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Charge le contenu du fichier .env
admin_password = os.getenv("ADMIN_PASSWORD")

def main():
    # Récupérer le token admin depuis l'environnement
    admin_token = os.getenv("ADMIN_PASSWORD")
    if not admin_token:
        print("Erreur : la variable d'environnement ADMIN_PASSWORD n'est pas définie.")
        return

    # URL de l'endpoint sécurisé pour télécharger les logs
    API_URL = "https://license-api-h5um.onrender.com/download_logs"

    headers = {
        "Authorization": f"Bearer {admin_token}"
    }

    try:
        response = requests.get(API_URL, headers=headers)
    except Exception as e:
        print("Erreur lors de la connexion à l'API :", e)
        return

    if response.status_code == 200:
        # Sauvegarde du contenu dans un fichier local
        with open("downloaded_logs.csv", "wb") as f:
            f.write(response.content)
        print("Les logs ont bien été téléchargés sous le nom 'downloaded_logs.csv'.")
    else:
        print(f"Erreur {response.status_code} : {response.text}")

if __name__ == "__main__":
    main()
