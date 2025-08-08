import requests

# Config
SERVER_URL = "https://license-api-h5um.onrender.com/lexicon/download"  # À adapter selon ton domaine ou localhost
AGENCY_TOKEN = "symcom_20250531"  # Mets ici le token de l'agence

# Prépare les headers d'authentification
headers = {
    "Authorization": f"Bearer {AGENCY_TOKEN}",
}

# Télécharge le fichier
response = requests.get(SERVER_URL, headers=headers)

if response.status_code == 200:
    # Sauvegarde le fichier sous le nom désiré
    filename = "lexicon2.xlsx"
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"✅ Fichier téléchargé sous {filename}")
else:
    print(f"❌ Erreur {response.status_code}: {response.text}")
