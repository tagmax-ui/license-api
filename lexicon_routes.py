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

# === NOUVELLE STRUCTURE DE COLONNES ===
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
    'sources_notes',
    'other_notes',
    'translators_notes',
    'notes',
]

KEY_PLUR = 'english_long_form_plural'
KEY_SING = 'english_long_form_singular'


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes manquantes et force le type str/NaN->'' pour stabilité."""
    for col in LEXICON_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    # homogénéiser: tout en str (sauf timestamp si on veut le garder numérique)
    for col in df.columns:
        if col == 'modified_on':
            continue
        df[col] = df[col].fillna("").astype(str)
    return df


def _display_key_series(df: pd.DataFrame) -> pd.Series:
    s = df.get(KEY_SING, "").fillna("").astype(str).str.strip()
    p = df.get(KEY_PLUR, "").fillna("").astype(str).str.strip()
    return s.mask(s == "", p).replace("", "?????")


def _sort_and_reorder(df: pd.DataFrame) -> pd.DataFrame:
    disp = _display_key_series(df)
    order = disp.str.casefold()
    df = df.loc[order.sort_values(kind='mergesort').index].reset_index(drop=True)
    df = df[[c for c in LEXICON_COLUMNS if c in df.columns] +
            [c for c in df.columns if c not in LEXICON_COLUMNS]]
    return df


def _normalize_file(xlsx_path: str) -> None:
    """Ouvre, assure les colonnes et l'ordre, puis réécrit si nécessaire (idempotent)."""
    try:
        if not os.path.exists(xlsx_path):
            return
        df = pd.read_excel(xlsx_path, header=0)
        before_cols = list(df.columns)
        df = _ensure_columns(df)
        df = _sort_and_reorder(df)
        after_cols = list(df.columns)
        # Réécriture seulement si changement structure/ordre (évite I/O inutile)
        if before_cols != after_cols:
            df.to_excel(xlsx_path, index=False)
    except Exception:
        # Ne bloque pas la requête si normalisation échoue; les routes feront le nécessaire.
        pass


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

    # 1) Crée le modèle une fois, jamais plus.
    if not os.path.exists(default_path):
        shutil.copyfile(TEMPLATE_XLSX, default_path)

    # 2) Crée le lexique de l'agence SEULEMENT s'il n'existe pas.
    if not os.path.exists(xlsx_path):
        shutil.copyfile(default_path, xlsx_path)

    # 3) Normalise la structure (ajoute les 3 nouvelles colonnes si absentes, réordonne)
    _normalize_file(xlsx_path)

    g.agency = agency


@lexicon_blueprint.route('/download', methods=['GET'])
def download_lexicon():
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    if not os.path.exists(xlsx_path):
        return jsonify(success=False, error="Lexicon file not found."), 404
    try:
        return send_file(xlsx_path, as_attachment=True,
                         download_name=f"{g.agency}_lexicon.xlsx")
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@lexicon_blueprint.route('/entry/<english_long_form>', methods=['POST'])
def update_entry(english_long_form):
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    try:
        with lexicon_file_lock(xlsx_path):
            df = pd.read_excel(xlsx_path, header=0)
            df = _ensure_columns(df)

            payload = request.get_json()
            if not isinstance(payload, dict):
                return jsonify(success=False, error='Invalid JSON body'), 400
            username = payload.get('modified_by', 'Inconnu')

            # match sur singulier, sinon pluriel
            mask = (df.get(KEY_SING, "") == english_long_form)
            if not mask.any():
                mask = (df.get(KEY_PLUR, "") == english_long_form)

            timestamp = int(time.time())
            if mask.any():
                row_idx = df.index[mask][0]
                for k, v in payload.items():
                    if k in df.columns:
                        df.at[row_idx, k] = v
                df.at[row_idx, 'modified_by'] = username
                df.at[row_idx, 'modified_on'] = timestamp
                message = "Entry updated"
            else:
                new_row = {col: "" for col in df.columns}
                new_row.update({k: v for k, v in payload.items() if k in df.columns})
                if not (str(new_row.get(KEY_SING, "")).strip() or str(new_row.get(KEY_PLUR, "")).strip()):
                    new_row[KEY_SING] = "?????"
                new_row['modified_by'] = username
                new_row['modified_on'] = timestamp
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                message = "Entry created"

            df = _sort_and_reorder(df)
            df.to_excel(xlsx_path, index=False)

    except RuntimeError as e:
        return jsonify(success=False, error=str(e)), 409
    except Exception as e:
        return jsonify(success=False, error=f"Unexpected error: {e}"), 500

    return jsonify(success=True, message=message), 200


@lexicon_blueprint.route('/upload', methods=['POST'])
def upload_lexicon():
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')

    if 'file' not in request.files:
        return jsonify(success=False, error='No file part'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, error='No selected file'), 400

    temp_path = xlsx_path + '.uploading'
    try:
        with lexicon_file_lock(xlsx_path):
            file.save(temp_path)
            df = pd.read_excel(temp_path, header=0)
            df = _ensure_columns(df)
            df = _sort_and_reorder(df)
            # Écrit la version normalisée sur le fichier final
            df.to_excel(xlsx_path, index=False)
            # Nettoie le temporaire (il a déjà été « consommé »)
            if os.path.exists(temp_path):
                os.remove(temp_path)
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
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    lock_path = xlsx_path + '.lock'

    if not os.path.exists(lock_path):
        return jsonify(success=True, message="No lock present."), 200
    try:
        os.remove(lock_path)
        return jsonify(success=True, message="Lock file removed."), 200
    except Exception as e:
        return jsonify(success=False, error=f"Unable to remove lock: {e}"), 500


@lexicon_blueprint.route('/entry/<english_key>', methods=['DELETE'])
def delete_entry(english_key):
    xlsx_path = os.path.join(DICT_DIR, f'{g.agency}.xlsx')
    try:
        with lexicon_file_lock(xlsx_path):
            df = pd.read_excel(xlsx_path, header=0)
            df = _ensure_columns(df)

            mask = (df.get(KEY_SING, "") == english_key)
            if not mask.any():
                mask = (df.get(KEY_PLUR, "") == english_key)

            if not mask.any():
                return jsonify(success=False, message="Entry not found"), 404

            soft = request.args.get('soft', '0').lower() in ('1', 'true', 'yes', 'y')
            if soft:
                df.loc[mask, 'active'] = "0"
                message = "Entry deactivated"
            else:
                df = df[~mask]
                message = "Entry deleted"

            df = _sort_and_reorder(df)
            df.to_excel(xlsx_path, index=False)

    except RuntimeError as e:
        return jsonify(success=False, error=str(e)), 409
    except Exception as e:
        return jsonify(success=False, error=f"Unexpected error: {e}"), 500

    return jsonify(success=True, message=message), 200


# (Facultatif) utilitaire conservé, harmonisé avec la nouvelle structure
def update_or_add_lexicon_entry(df, english_long_form, payload, username):
    timestamp = int(time.time())
    mask = (df.get(KEY_SING, "") == english_long_form)
    if not mask.any():
        mask = (df.get(KEY_PLUR, "") == english_long_form)

    if mask.any():
        row_idx = df.index[mask][0]
        for key, value in payload.items():
            if key in df.columns:
                df.at[row_idx, key] = value
        df.at[row_idx, 'modified_by'] = username
        df.at[row_idx, 'modified_on'] = timestamp
        return df, "Entry updated"
    else:
        new_row = {col: "" for col in df.columns}
        # on initialise au moins une clé
        if english_long_form:
            new_row[KEY_SING] = english_long_form
        for key, value in payload.items():
            if key in df.columns:
                new_row[key] = value
        if not (str(new_row.get(KEY_SING, "")).strip() or str(new_row.get(KEY_PLUR, "")).strip()):
            new_row[KEY_SING] = "?????"
        new_row['modified_by'] = username
        new_row['modified_on'] = timestamp
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        return df, "Entry created"
