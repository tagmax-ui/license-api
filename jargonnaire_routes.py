import os
import shutil
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify, g, current_app
import traceback

jargonnaire_blueprint = Blueprint('jargonnaire', __name__)

DATA_DIR = os.getenv('DATA_DIR', '/data')
DICT_DIR = os.path.join(DATA_DIR, 'dictionaries')
os.makedirs(DICT_DIR, exist_ok=True)


@jargonnaire_blueprint.before_request
def verify_agency_token_and_init_dict():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify(success=False, error='Missing or invalid token'), 403

    agency = auth.split('Bearer ')[1].strip()
    if agency not in current_app.licenses:
        return jsonify(success=False, error='Unknown agency'), 403

    xml_path     = os.path.join(DICT_DIR, f'{agency}.xml')
    default_path = os.path.join(DICT_DIR, 'default_jargonnaire_dictionary.xml')

    if not os.path.exists(xml_path):
        shutil.copyfile(default_path, xml_path)

    g.agency = agency


@jargonnaire_blueprint.route(
    '/jargonnaire/entry/<entry_name>',
    methods=['GET', 'POST']
)
def entry(entry_name):
    xml_path = os.path.join(DICT_DIR, f'{g.agency}.xml')
    tree = ET.parse(xml_path)
    root = tree.getroot()

    if request.method == 'GET':
        elem = root.find(f".//entry[@name='{entry_name}']")
        if elem is None:
            return jsonify(success=False, error='Entry not found'), 404

        result = {k: v for k, v in elem.attrib.items() if k != 'name'}
        options = [opt.attrib for opt in elem.findall('translation_option')]
        if options:
            result['translation_options'] = options
        return jsonify(success=True, entry=result)

    # POST
    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify(success=False, error='Invalid JSON body'), 400

    elem = root.find(f".//entry[@name='{entry_name}']")
    if elem is None:
        elem = ET.SubElement(root, 'entry', name=entry_name)

    # Reset attributes except 'name'
    for attr in list(elem.attrib):
        if attr != 'name':
            del elem.attrib[attr]
    # Set new attributes
    for k, v in payload.items():
        if k != 'translation_options':
            elem.set(k, str(v))

    # Replace translation_option elements
    for old in elem.findall('translation_option'):
        elem.remove(old)
    for opt in payload.get('translation_options', []):
        ET.SubElement(elem, 'translation_option', **opt)

    tree.write(xml_path, encoding='utf-8', xml_declaration=True)
    return jsonify(success=True, message=f"Entry '{entry_name}' saved."), 200


@jargonnaire_blueprint.route('/jargonnaire/entries', methods=['GET'])
def list_entries():
    xml_path = os.path.join(DICT_DIR, f'{g.agency}.xml')
    tree = ET.parse(xml_path)
    root = tree.getroot()
    names = [e.get('name') for e in root.findall('entry') if e.get('name')]
    return jsonify(success=True, entries=names), 200



@jargonnaire_blueprint.route(
    '/jargonnaire/debug/list_data', methods=['GET'])
def debug_list_data():
    """
    Retourne l'arborescence des dossiers et fichiers sous /data
    (protégé par le même Bearer token).
    """
    tree = {}
    for root, dirs, files in os.walk(DATA_DIR):
        rel = os.path.relpath(root, DATA_DIR)
        tree[rel] = {
            'dirs': sorted(dirs),
            'files': sorted(files)
        }
    return jsonify(success=True, tree=tree), 200


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