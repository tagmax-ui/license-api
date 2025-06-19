import os
import shutil
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify, g, current_app
import traceback

jargonnaire_blueprint = Blueprint('jargonnaire', __name__)

HERE = os.path.dirname(__file__)
TEMPLATE_XML = os.path.join(HERE, 'data', 'default_jargonnaire_dictionary.xml')
DATA_DIR = os.getenv('DATA_DIR', '/data')
DICT_DIR = os.path.join(DATA_DIR, 'dictionaries')
print("=== JE SUIS LE BON FICHIER : jargonnaire_routes.py ===")
print(">>>> INIT DE JARGONNAIRE_ROUTES !!!!!!!")
print("=== DÉMARRAGE FLASK ===")
print("DATA_DIR =", DATA_DIR)
print("DICT_DIR =", DICT_DIR)
print("TEMPLATE_XML =", TEMPLATE_XML)
os.makedirs(DICT_DIR, exist_ok=True)
print("DICT_DIR exists or created.")

@jargonnaire_blueprint.before_request
def verify_agency_token_and_init_dict():
    print("====> [before_request] Démarré pour agency/token")

    auth = request.headers.get('Authorization', '')
    print("Header Authorization:", auth)
    if not auth.startswith('Bearer '):
        print("Refus : token manquant/malformé")
        return jsonify(success=False, error='Missing or invalid token'), 403

    agency = auth.split('Bearer ')[1].strip()
    print("Agency détectée:", agency)
    if agency not in current_app.licenses:
        print("Refus : agency inconnue")
        return jsonify(success=False, error='Unknown agency'), 403

    xml_path = os.path.join(DICT_DIR, f'{agency}.xml')
    default_path = os.path.join(DICT_DIR, 'default_jargonnaire_dictionary.xml')
    print(f"Chemin xml_path (agence) : {xml_path}")
    print(f"Chemin default_path : {default_path}")

    print("DEBUG: TEMPLATE_XML existe ?", os.path.exists(TEMPLATE_XML), TEMPLATE_XML)
    if not os.path.exists(default_path):
        print("DEBUG: Le modèle n'existe pas, tentative de copie...")
        try:
            shutil.copyfile(TEMPLATE_XML, default_path)
            print(f"DEBUG: Copié modèle depuis {TEMPLATE_XML} vers {default_path}")
        except Exception as e:
            print("ERREUR COPIE TEMPLATE_XML -> default_path:", repr(e))
        print(f"DEBUG: Contenu DICT_DIR après copie modèle:", os.listdir(DICT_DIR))

    if not os.path.exists(xml_path):
        print("DEBUG: Le XML agence n'existe pas, tentative de copie...")
        try:
            shutil.copyfile(default_path, xml_path)
            print(f"DEBUG: Copié modèle agence vers {xml_path}")
        except Exception as e:
            print("ERREUR COPIE default_path -> xml_path:", repr(e))
        print(f"DEBUG: Contenu DICT_DIR après copie agence:", os.listdir(DICT_DIR))

    g.agency = agency
    print("====> [before_request] FINISHED pour", agency)

@jargonnaire_blueprint.route(
    '/entry/<entry_name>',
    methods=['GET', 'POST'])
def entry(entry_name):
    print("--- [entry] ROUTE ATTEINTE AVEC entry_name =", entry_name)
    xml_path = os.path.join(DICT_DIR, f'{g.agency}.xml')
    print(f"--- [entry] Accès fichier: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        print(f"[entry] XML chargé avec succès : {xml_path}")
    except Exception as e:
        print(f"ERREUR ouverture XML {xml_path} :", repr(e))
        return jsonify(success=False, error=f"XML read error: {e}"), 500

    root = tree.getroot()

    if request.method == 'GET':
        print(f"[entry][GET] Requête pour entrée: {entry_name}")
        elem = root.find(f".//entry[@name='{entry_name}']")
        if elem is None:
            print("[entry][GET] Entrée non trouvée.")
            return jsonify(success=False, error='Entry not found'), 404

        result = {k: v for k, v in elem.attrib.items() if k != 'name'}
        options = [opt.attrib for opt in elem.findall('translation_option')]
        if options:
            result['translation_options'] = options
        print(f"[entry][GET] Entrée trouvée: {result}")
        return jsonify(success=True, entry=result)

    # POST
    print(f"[entry][POST] Écriture/modification pour : {entry_name}")
    payload = request.get_json()
    print(f"[entry][POST] Payload reçu: {payload}")
    if not isinstance(payload, dict):
        print("[entry][POST] JSON body non valide.")
        return jsonify(success=False, error='Invalid JSON body'), 400

    elem = root.find(f".//entry[@name='{entry_name}']")
    if elem is None:
        elem = ET.SubElement(root, 'entry', name=entry_name)
        print(f"[entry][POST] Nouvelle entrée créée: {entry_name}")

    # Reset attributes except 'name'
    for attr in list(elem.attrib):
        if attr != 'name':
            del elem.attrib[attr]
    for k, v in payload.items():
        if k != 'translation_options':
            elem.set(k, str(v))

    # Replace translation_option elements
    for old in elem.findall('translation_option'):
        elem.remove(old)
    for opt in payload.get('translation_options', []):
        ET.SubElement(elem, 'translation_option', **opt)

    try:
        tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        print(f"[entry][POST] XML sauvé après modification : {xml_path}")
    except Exception as e:
        print(f"ERREUR écriture XML {xml_path} :", repr(e))
        return jsonify(success=False, error=f"XML write error: {e}"), 500

    return jsonify(success=True, message=f"Entry '{entry_name}' saved."), 200

@jargonnaire_blueprint.route('/entries', methods=['GET'])
def list_entries():
    xml_path = os.path.join(DICT_DIR, f'{g.agency}.xml')
    print(f"[list_entries] Ouverture: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        names = [e.get('name') for e in root.findall('entry') if e.get('name')]
        print(f"[list_entries] Entrées listées: {names}")
        return jsonify(success=True, entries=names), 200
    except Exception as e:
        print(f"[list_entries] ERREUR: {repr(e)}")
        return jsonify(success=False, error=f"XML read error: {e}"), 500

@jargonnaire_blueprint.route('/debug/list_data', methods=['GET'])
def debug_list_data():
    print("[debug_list_data] Lancement du listing DATA_DIR")
    try:
        tree = {}
        for root, dirs, files in os.walk(DATA_DIR):
            rel = os.path.relpath(root, DATA_DIR)
            tree[rel] = {'dirs': sorted(dirs), 'files': sorted(files)}
            print(f"[debug_list_data] Dossier {rel}: dirs={dirs}, files={files}")
        return jsonify(success=True, tree=tree), 200
    except Exception as e:
        print(f"[debug_list_data] ERREUR: {repr(e)}")
        return jsonify(
            success=False,
            error=str(e),
            traceback=traceback.format_exc()
        ), 500


@jargonnaire_blueprint.route('/export/xml', methods=['GET'])
def export_xml():
    xml_path = os.path.join(DICT_DIR, f'{g.agency}.xml')
    try:
        with open(xml_path, 'rb') as f:
            xml_content = f.read()
        return current_app.response_class(
            response=xml_content,
            status=200,
            mimetype='text/xml'
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500