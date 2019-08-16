import base64
import os
import uuid

from flask import jsonify, request, make_response, send_from_directory, redirect, url_for, Blueprint
from flask_login import login_required
from werkzeug.utils import secure_filename

import data_tools as dt
from data_tools.util import UPLOADDIR
from helpers import get_current_user, handle_exception, process_input_dict

samples_api = Blueprint('samples_api', __name__, url_prefix='/api/samples')


@samples_api.route('/', methods=['GET', 'POST'])
@login_required
def list_samples():
    try:
        user = get_current_user()
        if request.method == 'POST':
            filename = os.path.join(UPLOADDIR, secure_filename(str(uuid.uuid4())))
            data = request.get_json(force=True)
            if 'file' in request.files:
                request.files['file'].save(filename)
            else:
                file_contents = data['file']
                del data['file']
                decoded_file_contents = base64.b64decode(file_contents)
                with open(filename, 'wb') as file:
                    file.write(decoded_file_contents)
            workflow_data = dt.sample_creation.create_sample_creation_workflow(user, [filename], data)
            dt.jobserver_control.start_job(workflow_data['workflow_filename'], workflow_data['job'], user)
            return redirect(url_for('jobs_api.list_jobs'))
        return jsonify([sample.to_dict() for sample in dt.samples.get_samples(user)])
    except Exception as e:
        return handle_exception(e)


@samples_api.route('/<sample_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def get_sample(sample_id=None):
    try:
        user = get_current_user()
        sample = dt.samples.get_sample(user, sample_id)
        if request.method == 'GET':
            return jsonify({**sample.to_dict(), 'is_write_permitted': dt.users.is_write_permitted(user, sample)})

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
                        sample_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                        file.write(sample_file_data)
                        del new_data['file']
                if dt.util.validate_file(filename):
                    return jsonify(
                        dt.samples.update_sample(user, sample, new_data, filename).to_dict())
            return jsonify(dt.samples.update_sample(user, sample, new_data).to_dict())

        if request.method == 'DELETE':
            return jsonify(dt.samples.delete_sample(user, dt.samples.get_sample(user, sample_id)))
    except Exception as e:
        return handle_exception(e)


@samples_api.route('/common_attributes', methods=['POST'])
@login_required
def get_common_attributes():
    try:
        user = get_current_user()
        data = request.get_json(force=True)
        samples = [dt.samples.get_sample(user, sample_id) for sample_id in data['sample_ids']]
        common_keys = [item for item in samples[0].get_file_metadata().keys()
                       if all([item in sample.get_file_metadata() for sample in samples])]
        return jsonify(common_keys)
    except Exception as e:
        return handle_exception(e)


@samples_api.route('/download/<sample_id>', methods=['GET'])
@login_required
def download_sample(sample_id=None):
    try:
        user = get_current_user()
        sample = dt.samples.get_sample(user, sample_id)
        if request.args.get('path', ''):
            path = request.args.get('path', '')
            out = dt.samples.download_sample_dataset(user, sample, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        directory, filename = os.path.split(sample.filename)
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@samples_api.route('/upload', methods=['POST'])
@login_required
def upload_sample():
    try:
        user = get_current_user()
        # for request from MATLAB client that doesn't support multipart/form-data
        # file is base64 encoded.
        new_data = {}
        try:
            new_data.update(process_input_dict(request.get_json()))
        except:
            new_data.update(process_input_dict(request.form))

        filename = os.path.join(UPLOADDIR, str(uuid.uuid4()))
        if 'file' not in new_data and 'file' not in request.files:
            raise ValueError('No file uploaded')
        if 'file' in request.files:
            if request.files['file'].filename == '':
                raise ValueError('No file uploaded')
            request.files['file'].save(filename)
        else:
            with open(filename, 'wb') as file:
                sample_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                file.write(sample_file_data)
                del new_data['file']
        if dt.util.validate_file(filename):
            return jsonify(dt.samples.upload_sample(user, filename, new_data).to_dict())
        raise ValueError('invalid content type')
    except Exception as e:
        return handle_exception(e)
