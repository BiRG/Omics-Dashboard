from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_current_user, handle_exception

external_files_api = Blueprint('external_files_api', __name__, url_prefix='/api/external_files')


@external_files_api.route('/', methods=['GET', 'POST'])
def list_external_files():
    try:
        current_user = get_current_user()
        if request.method == 'GET':
            return jsonify(
                [external_file.to_dict() for external_file in dt.external_files.get_external_files(current_user)])
        if request.method == 'POST':
            # this will only create a record. the "upload" route should be used to both create the record and upload a file
            return jsonify(dt.external_files.create_external_file(current_user, request.get_json(force=True)).to_dict())
    except Exception as e:
        return handle_exception(e)


@external_files_api.route('/<external_file_id>', methods=['GET', 'POST', 'DELETE'])
def get_external_file(external_file_id=None):
    try:
        current_user = get_current_user()
        external_file = dt.external_files.get_external_file(current_user, external_file_id)
        if request.method == 'GET':
            return jsonify(external_file.to_dict())
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            move_file = 'filename' in new_data and 'move_file' in new_data and new_data['move_file']
            return jsonify(
                dt.external_files.update_external_file(current_user, external_file, new_data, move_file).to_dict())
        if request.method == 'DELETE':
            return jsonify(dt.external_files.delete_external_file(current_user, external_file))
    except Exception as e:
        return handle_exception(e)
