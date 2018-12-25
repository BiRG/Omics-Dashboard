import base64
import os
import uuid
import json

from flask import request, jsonify, make_response, send_from_directory, Blueprint
from werkzeug.utils import secure_filename

import data_tools as dt
import data_tools.file_tools.metadata_tools as mdt
from data_tools.util import DATADIR, UPLOADDIR
from helpers import get_current_user, handle_exception
import shutil
collections_api = Blueprint('collections_api', __name__, url_prefix='/api/collections')


@collections_api.route('/', methods=['GET', 'POST'])
def list_collections():
    try:
        current_user = get_current_user()
        if request.method == 'GET':
            return jsonify([collection.to_dict() for collection in dt.collections.get_collections(current_user)])
        if request.method == 'POST':
            data = request.get_json(force=True)
            if 'sample_ids' in data:
                samples = [dt.samples.get_sample(current_user, sample_id) for sample_id in data['sample_ids']]
                del data['sample_ids']
            else:
                samples = []
            return jsonify(dt.collections.create_collection(current_user, samples, data).to_dict())
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/<collection_id>', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def get_collection(collection_id=None):
    try:
        user = get_current_user()
        if request.method == 'GET':
            return jsonify(dt.collections.get_collection(user, collection_id).to_dict())

        collection = dt.collections.get_collection(user, collection_id)
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            return jsonify(dt.collections.update_collection(user, collection, new_data))
        if request.method == 'PATCH':
            # We can have requests to change values in arrays here
            # we need "path", "i" and "j" parameters and "newValue" in the body.
            if 'path' in request.args and 'i' in request.args and 'j' in request.args:
                val = request.get_json(force=True)['new_value']
                path, i, j = request.args.get('path'), request.args.get('i'), request.args.get('j')
                dt.collections.update_collection_array(user, collection, path, i, j, val)
                return jsonify({'message': f'Changed value of {path}[{i}, {j}] in collection {collection.id} to {val}'})
        if request.method == 'DELETE':
            return jsonify(dt.collections.delete_collection(user, collection))
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/download/<collection_id>', methods=['GET'])
def download_collection(collection_id=None):
    try:
        user = get_current_user()
        if request.args.get('format', '') == 'pandas':
            single_column = True if request.args.get('single_column', '') == 'true' else False
            data_format = request.args.get('data_format') if 'data_format' in request.args else 'csv'
            if data_format not in {'json', 'csv'}:
                raise ValueError(f'Improper data format {data_format}')
            json_orient = request.args.get('orient') if 'orient' in request.args else 'records'
            out = dt.collections.download_collection_dataframe(user, collection_id, single_column, data_format, json_orient)
            as_attachment = request.args.get('as_attachment') if 'as_attachment' in request.args else 'true'
            if as_attachment == 'false':
                response = jsonify({'data_frame': out[data_format]})
            else:
                if data_format == 'json':
                    out['json'] = json.dumps(out['json'])
                response = make_response(out[data_format])
                response.headers['Content-Disposition'] = out['cd']
                response.mimetype = f'text/{data_format}'
            return response
        if request.args.get('path', ''):
            path = request.args.get('path', '')
            out = dt.collections.download_collection_dataset(user, collection_id, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        out = dt.collections.download_collection(user, collection_id)
        return send_from_directory(f'{DATADIR}/collections', out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/upload', methods=['POST'])
def upload_collection():
    #  TODO: support files encoded as base64 in application/json and actual files in multipart/form-data
    try:
        user = get_current_user()
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
        if dt.util.validate_file(filename):
            collection = dt.collections.upload_collection(user, filename, new_data)
            return jsonify(collection.to_dict())
        raise ValueError('invalid content type')
    except Exception as e:
        return handle_exception(e)
