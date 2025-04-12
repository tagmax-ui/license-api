import requests


def fetch_lists(api_key):
    url = "https://license-api-h5um.onrender.com/lists"  # Remplacez par l'URL de votre endpoint
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        # En cas d'erreur, le programme peut s'arrêter ou utiliser un mécanisme de repli (fallback)
        raise Exception(f"Erreur lors de la récupération des listes: {e}")


# Exemple d'utilisation :
if __name__ == "__main__":
    # La clé API pourrait être fournie par l'utilisateur ou chargée de manière sécurisée depuis une variable d'environnement
    user_api_key = "TOPSECRET"
    lists = fetch_lists(user_api_key)

    # Maintenant, vous pouvez accéder aux listes récupérées
    masculine_exceptions = lists.get("masculine_exceptions", [])
    fe_ves_words = lists.get("fe_ves_words", [])
    userkey_dictionary_keys = lists.get("userkey_dictionary_keys", [])

    print("Listes récupérées avec succès !")
