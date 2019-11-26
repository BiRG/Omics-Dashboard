import base64
import json
import os
import uuid

from flask import request, jsonify, make_response, send_from_directory, Blueprint
from flask_login import login_required
from werkzeug.utils import secure_filename

import data_tools as dt
from data_tools.file_tools.collection_tools import validate_update
from data_tools.config import DATADIR, UPLOADDIR
from helpers import get_current_user, handle_exception, process_input_dict

collections_api = Blueprint('collections_api', __name__, url_prefix='/api/collections')


@collections_api.route('/', methods=['GET', 'POST'])
@login_required
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
            return jsonify(
                dt.collections.create_collection(current_user, samples, data).to_dict())
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/<collection_id>', methods=['GET', 'POST', 'PATCH', 'DELETE'])
@login_required
def get_collection(collection_id=None):
    try:
        user = get_current_user()
        collection = dt.collections.get_collection(user, collection_id)
        if request.method == 'GET':
            return jsonify({**collection.to_dict(),
                            'is_write_permitted': dt.users.is_write_permitted(user, collection)})

        if request.method == 'DELETE':
            return jsonify(dt.collections.delete_collection(user, collection))

        if request.content_type == 'application/json':
            new_data = process_input_dict(request.get_json(force=True))
        else:
            new_data = process_input_dict(request.form.to_dict())

        if request.method == 'POST':
            if 'file' in request.files or 'file' in new_data:
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
                    collection = dt.collections.update_collection(user, collection, new_data, filename)
                    return jsonify(collection.to_dict())
            return jsonify(dt.collections.update_collection(user, collection, new_data).to_dict())

        if request.method == 'PATCH':
            # We can have requests to change values in arrays here contents of request will be {path, i, j, new_value}
            # or list thereof (POST should be used to update entire arrays).
            if not isinstance(new_data, list):
                new_data = [new_data]
            # improperly formatted patch requests will throw error before anything changed
            for patch_data in new_data:
                validate_update(collection.filename, patch_data['path'], patch_data['i'],
                                patch_data['j'] if 'j' in patch_data else None, patch_data['new_value'])
            message = ''
            for patch_data in new_data:
                dt.collections.update_collection_array(user, collection,
                                                       patch_data['path'],
                                                       patch_data['i'],
                                                       patch_data['j'] if 'j' in patch_data else None,
                                                       patch_data['new_value'])
                message += (f'Changed value of {patch_data["path"]}[{patch_data["i"]}, '
                            f'{patch_data["j"] if "j" in patch_data else ""}] to {patch_data["new_value"]}\n')
            message += f'In collection {collection.id}'
            return jsonify({'message': message})
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/download/<collection_id>', methods=['GET'])
@login_required
def download_collection(collection_id=None):
    try:
        user = get_current_user()
        collection = dt.collections.get_collection(user, collection_id)
        if request.args.get('format', '') == 'pandas':
            single_column = request.args.get('single_column', '') == 'true'
            data_format = request.args.get('data_format') if 'data_format' in request.args else 'csv'
            if data_format not in {'json', 'csv'}:
                raise ValueError(f'Improper data format {data_format}')
            json_orient = request.args.get('orient') if 'orient' in request.args else 'records'
            out = dt.collections.download_collection_dataframe(user, collection, single_column, data_format, json_orient)
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
            out = dt.collections.download_collection_dataset(user, collection, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        out = dt.collections.download_collection(user, collection)
        return send_from_directory(f'{DATADIR}/collections', out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/upload', methods=['POST'])
@login_required
def upload_collection():
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


@collections_api.route('/copy/<collection_id>', methods=['GET'])
@login_required
def copy_collection(collection_id):
    """
    This only takes POST because it does create a record, but it doesn't take any body, so it could also be GET
    """
    try:
        current_user = get_current_user()
        return jsonify(dt.collections.copy_collection(current_user, dt.collections.get_collection(current_user, collection_id)).to_dict())
    except Exception as e:
        return handle_exception(e)


@collections_api.route('/merge', methods=['POST'])
@login_required
def merge_collections():
    try:
        current_user = get_current_user()
        # new collection keeps attributes of first collection in list
        new_data = request.get_json(force=True)
        collections = [dt.collections.get_collection(current_user, collection_id) for collection_id in new_data['collection_ids']]
        del new_data['collection_ids']
        new_collection = dt.collections.merge_collections(current_user, collections, new_data)
        return jsonify(new_collection.to_dict())
    except Exception as e:
        return handle_exception(e)
