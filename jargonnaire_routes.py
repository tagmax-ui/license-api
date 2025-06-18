# jargonnaire_routes.py

import os
import json
from flask import Blueprint, request, jsonify, g, current_app

jargonnaire_blueprint = Blueprint('jargonnaire', __name__)

# Répertoire persistant pour stocker les dicts par agence
DATA_DIR = os.getenv('DATA_DIR', '/data')
DICT_DIR = os.path.join(DATA_DIR, 'dictionaries')
os.makedirs(DICT_DIR, exist_ok=True)


@jargonnaire_blueprint.before_request
def verify_agency_token_and_init_dict():
    """
    1) Vérifie Authorization: Bearer <agency> pour TOUTES les routes du blueprint
    2) Crée /data/dictionaries/<agency>.json vide si besoin
    """
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify(success=False, error='Missing or invalid token'), 403

    agency = auth.split('Bearer ')[1].strip()
    licenses = current_app.licenses
    if agency not in licenses:
        return jsonify(success=False, error='Unknown agency'), 403

    # initialise le JSON vide si nécessaire
    path = os.path.join(DICT_DIR, f'{agency}.json')
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    g.agency = agency


@jargonnaire_blueprint.route('/jargonnaire/entry/<entry_name>', methods=['GET'])
def get_entry(entry_name):
    """Récupère une seule entrée du dictionnaire."""
    path = os.path.join(DICT_DIR, f'{g.agency}.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    entry = data.get(entry_name)
    if entry is None:
        return jsonify(success=False, error='Entry not found'), 404

    return jsonify(success=True, entry=entry)


@jargonnaire_blueprint.route('/jargonnaire/entry/<entry_name>', methods=['POST'])
def set_entry(entry_name):
    """Crée ou met à jour une seule entrée."""
    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify(success=False, error='Invalid JSON body'), 400

    path = os.path.join(DICT_DIR, f'{g.agency}.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    data[entry_name] = payload

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify(success=True, message=f"Entry '{entry_name}' saved."), 200


@jargonnaire_blueprint.route('/jargonnaire/entries', methods=['GET'])
def list_entries():
    """Liste toutes les clés du dictionnaire de l’agence."""
    path = os.path.join(DICT_DIR, f'{g.agency}.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(success=True, entries=list(data.keys())), 200
