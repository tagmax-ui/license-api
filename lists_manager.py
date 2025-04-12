from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# Vos listes (à stocker en toute sécurité sur le serveur)
masculine_exceptions = ["abaque", "abatage", "abattage", "abécédaire", "abime", "abîme", "abkhaze", "abolitionniste",
                        ...]
fe_ves_words = [
    ("knife", "knives"),
    ("wife", "wives"),
    ("life", "lives"),
    ("calf", "calves"),
    ("leaf", "leaves"),
    ("shelf", "shelves"),
    ("wolf", "wolves"),
    ("self", "selves"),
    ("thief", "thieves"),
    ("half", "halves")
]
userkey_dictionary_keys = [
    ("user_key_full_name", "Nom complet", str, True),
    ("user_key_first_name", "Prénom", str, True),
    ("user_key_family_name", "Nom de famille", str, True),
    # … autres tuples
]

# Exemple de clé API stockée dans une variable d'environnement ou en configuration sécurisée
VALID_API_KEY = "TOPSECRET123"


@app.route("/api/lists", methods=["GET"])
def get_lists():
    # On attend une clé API transmise dans les headers
    api_key = request.headers.get("Authorization")
    if not api_key or api_key != f"Bearer {VALID_API_KEY}":
        abort(401, description="Clé API invalide ou absente")

    # Regrouper vos listes dans un dictionnaire
    data = {
        "masculine_exceptions": masculine_exceptions,
        "fe_ves_words": fe_ves_words,
        "userkey_dictionary_keys": userkey_dictionary_keys
    }
    return jsonify(data)


if __name__ == "__main__":
    app.run()
