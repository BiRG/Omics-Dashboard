import base64
import os
import uuid

from flask import request, jsonify, Blueprint, send_from_directory
from werkzeug.utils import secure_filename

import data_tools as dt
from data_tools.users import is_write_permitted
from data_tools.util import UPLOADDIR
from helpers import get_current_user, handle_exception, process_input_dict

external_files_api = Blueprint('external_files_api', __name__, url_prefix='/api/external_files')


@external_files_api.route('/', methods=['GET', 'POST'])
def list_external_files():
    try:
        current_user = get_current_user()
        if request.method == 'GET':
            return jsonify(
                [external_file.to_dict() for external_file in dt.external_files.get_external_files(current_user)])
        if request.method == 'POST':
            # this will only create a record. the "upload" route should be used to both create the record and upload
            return jsonify(dt.external_files.create_external_file(current_user, request.get_json(force=True)).to_dict())
    except Exception as e:
        return handle_exception(e)


@external_files_api.route('/<external_file_id>', methods=['GET', 'POST', 'DELETE'])
def get_external_file(external_file_id=None):
    try:
        current_user = get_current_user()
        external_file = dt.external_files.get_external_file(current_user, external_file_id)
        if request.method == 'GET':
            return jsonify({**external_file.to_dict(),
                            'is_write_permitted': is_write_permitted(current_user, external_file)})

        if request.content_type == 'application/json':
            new_data = process_input_dict(request.get_json(force=True))
        else:
            new_data = process_input_dict(request.form.to_dict())

        if request.method == 'POST':
            move_file = 'filename' in new_data and 'move_file' in new_data and new_data['move_file']
            if 'file' in request.files or 'file' in new_data:
                filename = os.path.join(UPLOADDIR, secure_filename(str(uuid.uuid4())))
                if 'file' in request.files:
                    if request.files['file'].filename == '':
                        raise ValueError('No file uploaded')
                    request.files['file'].save(filename)
                else:
                    with open(filename, 'wb') as file:
                        external_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                        file.write(external_file_data)
                        del new_data['file']
                return jsonify(dt.external_files.update_external_file(current_user,
                                                                      external_file,
                                                                      new_data,
                                                                      move_file,
                                                                      filename).to_dict())
            return jsonify(dt.external_files.update_external_file(current_user,
                                                                  external_file,
                                                                  new_data,
                                                                  move_file).to_dict())

        if request.method == 'DELETE':
            return jsonify(dt.external_files.delete_external_file(current_user, external_file))
    except Exception as e:
        return handle_exception(e)


@external_files_api.route('/download/<external_file_id>', methods=['GET'])
def download_external_file(external_file_id=None):
    try:
        current_user = get_current_user()
        external_file = dt.external_files.get_external_file(current_user, external_file_id)
        out = dt.external_files.download_external_file(current_user, external_file)
        directory = os.path.dirname(external_file.filename)
        return send_from_directory(directory, out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@external_files_api.route('/upload', methods=['POST'])
def upload_external_file():
    try:
        user = get_current_user()
        # for request from MATLAB client that doesn't support multipart/form-data
        # file is base64 encoded.
        new_data = {}
        try:
            new_data.update(process_input_dict(request.get_json()))
        except:
            new_data.update(process_input_dict(request.form))
        if 'file' not in new_data and 'file' not in request.files:
            raise ValueError('No file uploaded')
        filename = os.path.join(UPLOADDIR, secure_filename(str(uuid.uuid4())))
        if 'file' in request.files:
            if request.files['file'].filename == '':
                raise ValueError('No file uploaded')
            print('file in request.files')
            request.files['file'].save(filename)
        else:
            with open(filename, 'wb') as file:
                collection_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                file.write(collection_file_data)
                del new_data['file']
        external_file = dt.external_files.upload_external_file(user, filename, new_data)
        return jsonify(external_file.to_dict())
    except Exception as e:
        return handle_exception(e)
