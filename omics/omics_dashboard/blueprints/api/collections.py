import base64
import os
import uuid
import json

from flask import request, jsonify, make_response, send_from_directory, Blueprint
from werkzeug.utils import secure_filename

import data_tools as dt
import data_tools.file_tools.metadata_tools as mdt
from data_tools.util import DATADIR, UPLOADDIR
from helpers import get_user_id, handle_exception
collections_api = Blueprint('collections_api', __name__, url_prefix='/api/collections')
import shutil


@collections_api.route('/', methods=['GET', 'POST'])
def list_collections():
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.collections.get_collections(current_user_id))
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.collections.create_collection(current_user_id, data['sampleIds'], data))
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/<collection_id>', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def get_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.collections.get_collection(user_id, collection_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            return jsonify(dt.collections.update_collection(user_id, collection_id, new_data))
        if request.method == 'PATCH':
            # We can have requests to change values in arrays here
            # we need "path", "i" and "j" parameters and "newValue" in the body.
            if 'path' in request.args and 'i' in request.args and 'j' in request.args:
                val = request.get_json(force=True)['newValue']
                path, i, j = request.args.get('path'), request.args.get('i'), request.args.get('j')
                print(f'Path: {path}, i: {i}, j: {j}')
                dt.collections.update_collection_array(user_id, collection_id, path, i, j, val)
                return jsonify({'message': f'Changed value of {path}[{i}, {j}] in collection {collection_id} to {val}'})
        if request.method == 'DELETE':
            return jsonify(dt.collections.delete_collection(user_id, collection_id))
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/download/<collection_id>', methods=['GET'])
def download_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.args.get('format', '') == 'pandas':
            single_column = True if request.args.get('singleColumn', '') == 'true' else False
            data_format = request.args.get('dataFormat') if 'dataFormat' in request.args else 'csv'
            if data_format not in {'json', 'csv'}:
                raise ValueError(f'Improper data format {data_format}')
            json_orient = request.args.get('orient') if 'orient' in request.args else 'records'
            out = dt.collections.download_collection_dataframe(user_id, collection_id, single_column, data_format, json_orient)
            as_attachment = request.args.get('asAttachment') if 'asAttachment' in request.args else 'true'
            if as_attachment == 'false':
                response = jsonify({'dataFrame': out[data_format]})
            else:
                if data_format == 'json':
                    out['json'] = json.dumps(out['json'])
                response = make_response(out[data_format])
                response.headers['Content-Disposition'] = out['cd']
                response.mimetype = f'text/{data_format}'
            return response
        if request.args.get('path', ''):
            path = request.args.get('path', '')
            out = dt.collections.download_collection_dataset(user_id, collection_id, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        out = dt.collections.download_collection(user_id, collection_id)
        return send_from_directory(f'{DATADIR}/collections', out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/upload', methods=['POST'])
def upload_collection():
    #  TODO: support files encoded as base64 in application/json and actual files in multipart/form-data
    try:
        user_id = get_user_id()
        # for request from MATLAB client that doesn't support multipart/form-data
        # file is base64 encoded.
        new_data = request.get_json()
        if 'file' not in new_data and 'file' not in request.files:
            raise ValueError('No file uploaded')
        filename = os.path.join(UPLOADDIR, secure_filename(str(uuid.uuid4())))
        if 'file' in request.files:
            if request.files['file'].filename == '':
                raise ValueError('No file uploaded')
            request.files['file'].save(filename)
        else:
            with open(filename, 'wb') as file:
                collection_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                file.write(collection_file_data)
                del new_data['file']
            # Apply required attributes
            shutil.copyfile(filename, '/data/test.h5')
            collection_data = mdt.get_collection_info(filename)
            collection_data = mdt.update_metadata(filename, {"owner": user_id})
            if 'userGroup' not in collection_data:
                collection_data = mdt.update_metadata(filename, {'userGroup': -1})
        if dt.util.validate_file(filename):
            collection_data = dt.collections.upload_collection(user_id, filename, new_data)
            return jsonify(collection_data)
        raise ValueError('invalid content type')
    except Exception as e:
        return handle_exception(e)
