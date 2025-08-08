import os
import shutil
import pandas as pd
from flask import Blueprint, request, jsonify, g, current_app, send_file
import contextlib
import time

lexicon_blueprint = Blueprint('lexicon', __name__)

HERE = os.path.dirname(__file__)
TEMPLATE_XLSX = os.path.join(HERE, 'data', 'default_lexicon.xlsx')
DATA_DIR = os.getenv('DATA_DIR', '/data')
DICT_DIR = os.path.join(DATA_DIR, 'dictionaries_lexicon')
os.makedirs(DICT_DIR, exist_ok=True)

LEXICON_COLUMNS = [
    'english_long_form',       # 0
    'english_short_form',      # 1
    'french_short_form_1',     # 2
    'french_short_form_2',     # 3
    'gender',                  # 4
    'nature',                  # 5
    'consonant_or_vowel',      # 6
    'grammatical_number',      # 7
    'last_modified_by',        # 8
    'last_modified_on',        # 9
]


@contextlib.contextmanager
def lexicon_file_lock(xlsx_path):
    lock_path = xlsx_path + '.lock'
    if os.path.exists(lock_path):
        raise RuntimeError("Lexicon is being modified. Please try again in a few seconds.")
    try:
        with open(lock_path, 'w') as f:
            f.write(str(time.time()))
        yield
    finally:
        if os.path.exists(lock_path):
            os.remove(lock_path)

@lexicon_blueprint.before_request
def verify_agency_token_and_init_lexicon():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify(success=False, error='Missing or invalid token'), 403

    agency = auth.split('Bearer ')[1].strip()
    if agency not in current_app.licenses:
        return jsonify(success=False, error='Unknown agency'), 403

    xlsx_path = os.path.join(DICT_DIR, f'{agency}.xlsx')
    default_path = os.path.join(DICT_DIR, 'default_lexicon.xlsx')

    # 1. Crée le modèle une fois, jamais plus.
    if not os.path.exists(default_path):
        shutil.copyfile(TEMPLATE_XLSX, default_path)

    # 2. Crée le lexique de l'agence SEULEMENT s'il n'existe pas.
    if not os.path.exists(xlsx_path):
        shutil.copyfile(default_path, xlsx_path)

    g.agency = agency

@lexicon_blueprint.route('/download', methods=['GET'])
def download_lexicon():
    """
    Permet à une agence de télécharger son fichier Excel Lexicon complet.
    """
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    if not os.path.exists(xlsx_path):
        return jsonify(success=False, error="Lexicon file not found."), 404

    try:
        return send_file(
            xlsx_path,
            as_attachment=True,
            download_name=f"{g.agency}_lexicon.xlsx"  # Flask >=2.0
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@lexicon_blueprint.route('/entry/<english_long_form>', methods=['POST'])
def update_entry(english_long_form):
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')

    # ----> LOCK ici <-----
    try:
        with lexicon_file_lock(xlsx_path):
            df = pd.read_excel(xlsx_path, header=None)
            payload = request.get_json()
            if not isinstance(payload, dict):
                return jsonify(success=False, error='Invalid JSON body'), 400
            username = payload.get('last_modified_by', 'Unknown')

            df, message = update_or_add_lexicon_entry(
                df, LEXICON_COLUMNS, english_long_form, payload, username
            )

            df.to_excel(xlsx_path, header=False, index=False)
    except RuntimeError as e:
        return jsonify(success=False, error=str(e)), 409  # 409 = Conflict
    except Exception as e:
        return jsonify(success=False, error=f"Unexpected error: {e}"), 500

    return jsonify(success=True, message=message), 200



@lexicon_blueprint.route('/upload', methods=['POST'])
def upload_lexicon():
    """
    Permet à une agence de téléverser un nouveau fichier Excel Lexicon complet.
    Remplacement du fichier seulement si la structure est OK et si le lock est disponible.
    """
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')

    # Vérifie qu'un fichier a bien été envoyé
    if 'file' not in request.files:
        return jsonify(success=False, error='No file part'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, error='No selected file'), 400

    # Upload dans un fichier temporaire d'abord, pour validation
    temp_path = xlsx_path + '.uploading'
    try:
        with lexicon_file_lock(xlsx_path):
            file.save(temp_path)
            # Vérification de structure (nombre de colonnes, etc.)
            df = pd.read_excel(temp_path, header=None)
            if df.shape[1] != len(LEXICON_COLUMNS):
                os.remove(temp_path)
                return jsonify(success=False, error=f"Lexicon file must have {len(LEXICON_COLUMNS)} columns."), 400
            # Si OK, on remplace l'ancien fichier
            shutil.move(temp_path, xlsx_path)
    except RuntimeError as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify(success=False, error=str(e)), 409
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify(success=False, error=f"Excel upload error: {e}"), 500

    return jsonify(success=True, message="Lexicon uploaded successfully.")

@lexicon_blueprint.route('/unlock', methods=['POST'])
def force_unlock():
    """
    Supprime le fichier .lock du lexique de l'agence.
    Usage : en cas de plantage ayant laissé un lock 'fantôme'.
    """
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    lock_path = xlsx_path + '.lock'

    if not os.path.exists(lock_path):
        return jsonify(success=True, message="No lock present."), 200

    try:
        os.remove(lock_path)
        return jsonify(success=True, message="Lock file removed."), 200
    except Exception as e:
        return jsonify(success=False, error=f"Unable to remove lock: {e}"), 500

def update_or_add_lexicon_entry(df, mapping, english_long_form, payload, username):
    """
    Met à jour (ou ajoute) une fiche dans le DataFrame `df` en se basant sur le mapping explicite des colonnes.
    - mapping : liste ordonnée des noms de colonnes attendus (par index)
    - english_long_form : la clé de recherche (colonne 0)
    - payload : dict avec les champs à mettre à jour
    - username : nom de la personne qui fait la modification

    Retourne le DataFrame modifié et un message.
    """
    timestamp = int(time.time())
    idx_key = mapping.index('english_long_form')
    idx_user = mapping.index('last_modified_by')
    idx_time = mapping.index('last_modified_on')

    # Recherche de la ligne
    mask = df.iloc[:, idx_key] == english_long_form
    if mask.any():
        row_idx = df.index[mask][0]
        # Met à jour chaque champ du payload (sauf la clé)
        for key, value in payload.items():
            if key in mapping and key != 'english_long_form':
                df.iat[row_idx, mapping.index(key)] = value
        df.iat[row_idx, idx_user] = username
        df.iat[row_idx, idx_time] = timestamp
        return df, "Entry updated"
    else:
        # Crée une nouvelle ligne vide
        new_row = [""] * len(mapping)
        new_row[idx_key] = english_long_form
        for key, value in payload.items():
            if key in mapping and key != 'english_long_form':
                new_row[mapping.index(key)] = value
        new_row[idx_user] = username
        new_row[idx_time] = timestamp
        df.loc[len(df)] = new_row
        return df, "Entry created"
