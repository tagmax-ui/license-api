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
    'english_long_form_plural',
    'english_long_form_singular',
    'en_short',
    'fr_short',
    'french_long_form_singular',
    'french_long_form_plural',
    'gender',
    'nature',
    'elision',
    'number',
    'active',
    'modified_by',
    'modified_on',
    'notes'
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
            df = pd.read_excel(xlsx_path, header=0)

            # Ajouté : tolérance pour colonnes manquantes
            for col in LEXICON_COLUMNS:
                if col not in df.columns:
                    df[col] = ""

            payload = request.get_json()
            if not isinstance(payload, dict):
                return jsonify(success=False, error='Invalid JSON body'), 400
            username = payload.get('modified_by', 'Inconnu')

            df, message = update_or_add_lexicon_entry(df, english_long_form, payload, username)

            df = df[[col for col in LEXICON_COLUMNS if col in df.columns] + [col for col in df.columns if
                                                                             col not in LEXICON_COLUMNS]]
            df.to_excel(xlsx_path, index=False)

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
            df = pd.read_excel(temp_path, header=0)
            for col in LEXICON_COLUMNS:
                if col not in df.columns:
                    df[col] = ""

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

@lexicon_blueprint.route('/entry/<english_long_form_singular>', methods=['DELETE'])
def delete_entry(english_long_form_singular):
    """
    Supprime une entrée (hard delete) ou la désactive (soft delete) en se basant
    sur la colonne 'english_long_form_singular' comme clé.

    - Hard delete (par défaut) : DELETE /lexicon/entry/<clé>
    - Soft delete :               DELETE /lexicon/entry/<clé>?soft=1  (met active="0")
    """
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    try:
        with lexicon_file_lock(xlsx_path):
            df = pd.read_excel(xlsx_path, header=0)

            # Robustesse : garantir la présence de toutes les colonnes attendues
            for col in LEXICON_COLUMNS:
                if col not in df.columns:
                    df[col] = ""

            key_col = 'english_long_form_singular'
            if key_col not in df.columns:
                return jsonify(success=False, error=f"Missing column '{key_col}'"), 500

            mask = df[key_col] == english_long_form_singular
            if not mask.any():
                return jsonify(success=False, message="Entry not found"), 404

            # soft delete ?soft=1 -> active="0", sinon suppression physique
            soft = request.args.get('soft', '0').lower() in ('1', 'true', 'yes', 'y')
            if soft:
                df.loc[mask, 'active'] = "0"
                message = "Entry deactivated"
            else:
                df = df[~mask]
                message = "Entry deleted"

            # Remettre l'ordre des colonnes connu en premier (comme pour POST)
            df = df[[c for c in LEXICON_COLUMNS if c in df.columns] +
                    [c for c in df.columns if c not in LEXICON_COLUMNS]]

            df.to_excel(xlsx_path, index=False)

    except RuntimeError as e:
        return jsonify(success=False, error=str(e)), 409
    except Exception as e:
        return jsonify(success=False, error=f"Unexpected error: {e}"), 500

    return jsonify(success=True, message=message), 200




def update_or_add_lexicon_entry(df, english_long_form, payload, username):
    timestamp = int(time.time())
    key_col = 'english_long_form_singular'
    user_col = 'modified_by'
    time_col = 'modified_on'

    mask = df[key_col] == english_long_form
    if mask.any():
        row_idx = df.index[mask][0]
        for key, value in payload.items():
            if key in df.columns and key != key_col:
                df.at[row_idx, key] = value
        df.at[row_idx, user_col] = username
        df.at[row_idx, time_col] = timestamp
        return df, "Entry updated"
    else:
        # Crée une nouvelle ligne vide avec tous les champs
        new_row = {col: "" for col in df.columns}
        new_row[key_col] = english_long_form
        for key, value in payload.items():
            if key in df.columns and key != key_col:
                new_row[key] = value
        new_row[user_col] = username
        new_row[time_col] = timestamp
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        return df, "Entry created"
