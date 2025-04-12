import os
from flask import Flask, jsonify
from lists import tagmax_and_matrix_lists

app = Flask(__name__)

@app.route("/all-lists", methods=["GET"])
def get_my_lists():
    # Créer un dictionnaire avec les données importées
    data = {
        "english_connector_list": tagmax_and_matrix_lists.generate_english_connector_list(),
        "capitalized_english_connector_list": tagmax_and_matrix_lists.generate_capitalized_english_connector_list(),
        "attributes_list": tagmax_and_matrix_lists.attributes_list,
        "GOC_clients": tagmax_and_matrix_lists.GOC_clients
    }
    return jsonify(data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
