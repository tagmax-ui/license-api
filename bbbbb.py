#!/usr/bin/env python3
import requests
import json
import sys

# ---- CONFIGURATION ----
BASE_URL = "https://license-api-h5um.onrender.com/"   # ← adapte ici l'URL de ton API
TOKEN    = "symcom_20250531"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}
OUTPUT_FILE = "dictionary.json"      # nom du fichier de sortie (optionnel)

def fetch_entries_list():
    url = f"{BASE_URL}/jargonnaire/entries"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success", False):
        print("Erreur lors de la récupération des clés :", payload, file=sys.stderr)
        sys.exit(1)
    return payload.get("entries", [])

def fetch_entry(name):
    url = f"{BASE_URL}/jargonnaire/entry/{name}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success", False):
        print(f"Entrée non trouvée ou erreur pour '{name}' :", payload, file=sys.stderr)
        return None
    return payload.get("entry", {})

@jargonnaire_blueprint.route('/jargonnaire/debug/list_data', methods=['GET'])
def debug_list_data():
    try:
        tree = {}
        for root, dirs, files in os.walk(DATA_DIR):
            rel = os.path.relpath(root, DATA_DIR)
            tree[rel] = {'dirs': sorted(dirs), 'files': sorted(files)}
        return jsonify(success=True, tree=tree), 200

    except Exception as e:
        # capture la stack
        tb = traceback.format_exc()
        return jsonify(success=False,
                       error=str(e),
                       traceback=tb), 500

def main():
    # 1) Récupère la liste des noms d'entrées
    entries = fetch_entries_list()
    if not entries:
        print("Le dictionnaire est vide.", file=sys.stderr)
        return

    # 2) Pour chaque entrée, on va chercher son contenu
    dictionary = {}
    for name in entries:
        entry_data = fetch_entry(name)
        if entry_data is not None:
            dictionary[name] = entry_data

    # 3) Affiche en JSON ou écris dans un fichier
    pretty = json.dumps(dictionary, ensure_ascii=False, indent=2)
    print(pretty)

    # Optionnel : sauver dans un fichier
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(pretty)
        print(f"\nDictionnaire sauvé dans '{OUTPUT_FILE}'.")
    except IOError as e:
        print(f"Erreur écriture fichier : {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
