# jargonnaire_routes.py

import os
import json
from flask import Blueprint, request, jsonify, g
from license_server import licenses


jargonnaire_blueprint = Blueprint('jargonnaire', __name__)

# Répertoire persistant pour stocker les dicts par agence
DATA_DIR = os.getenv('DATA_DIR', '/data')
DICT_DIR = os.path.join(DATA_DIR, 'dictionaries')
os.makedirs(DICT_DIR, exist_ok=True)


@jargonnaire_blueprint.before_app_request
def verify_agency_token():
    """Vérifie la présence et la validité de Authorization: Bearer <agency_name>."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify(success=False, error='Missing or invalid token'), 403
    agency = auth.split('Bearer ')[1].strip()
    if agency not in licenses:
        return jsonify(success=False, error='Unknown agency'), 403
    g.agency = agency


@jargonnaire_blueprint.route('/jargonnaire/entry/<entry_name>', methods=['GET'])
def get_entry(entry_name):
    """
    GET /jargonnaire/entry/foo
    → renvoie { success: True, entry: { … } } ou erreur 404 si absent.
    """
    path = os.path.join(DICT_DIR, f'{g.agency}.json')
    if not os.path.exists(path):
        return jsonify(success=False, error='Dictionary not found'), 404

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    entry = data.get(entry_name)
    if entry is None:
        return jsonify(success=False, error='Entry not found'), 404

    return jsonify(success=True, entry=entry)


@jargonnaire_blueprint.route('/jargonnaire/entry/<entry_name>', methods=['POST'])
def set_entry(entry_name):
    """
    POST /jargonnaire/entry/foo
    Body JSON → crée ou met à jour l’entrée “foo”.
    Retourne { success: True, message: … }.
    """
    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify(success=False, error='Invalid JSON body'), 400

    path = os.path.join(DICT_DIR, f'{g.agency}.json')
    # Charge l’existant ou initialise un nouveau dict
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}

    data[entry_name] = payload

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify(success=True, message=f"Entry '{entry_name}' saved."), 200


@jargonnaire_blueprint.route('/jargonnaire/entries', methods=['GET'])
def list_entries():
    """Retourne la liste de toutes les clés dans symcom20250531.json."""
    path = os.path.join(DICT_DIR, f'{g.agency}.json')
    if not os.path.exists(path):
        return jsonify(success=True, entries=[])
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(success=True, entries=list(data.keys()))


@jargonnaire_blueprint.before_app_request
def verify_agency_token():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        return jsonify(success=False, error='Missing or invalid token'), 403

    agency = auth.split('Bearer ')[1].strip()
    if agency not in licenses:
        return jsonify(success=False, error='Unknown agency'), 403

    # Créer automatiquement le JSON vide s’il n’existe pas
    path = os.path.join(DICT_DIR, f'{agency}.json')
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    g.agency = agency