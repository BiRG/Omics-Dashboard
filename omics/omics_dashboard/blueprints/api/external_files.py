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
            return jsonify({'foo': 'bar'})
    except Exception as e:
        return handle_exception(e)
