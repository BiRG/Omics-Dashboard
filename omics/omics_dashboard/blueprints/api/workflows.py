import base64
import os
import uuid

from flask import jsonify, request, Blueprint
from flask_login import login_required
from werkzeug.utils import secure_filename

import data_tools as dt
from data_tools.config import UPLOADDIR
from helpers import get_current_user, handle_exception, process_input_dict

workflows_api = Blueprint('workflows_api', __name__, url_prefix='/api/workflows')


@workflows_api.route('/', methods=['GET', 'POST'])
@login_required
def list_workflows():
    try:
        user = get_current_user()
        if request.method == 'POST':
            return jsonify(dt.workflows.create_workflow(user, request.get_json()).to_dict())
        return jsonify([workflow.to_dict() for workflow in dt.workflows.get_workflows(user)])
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflow_modules')
@login_required
def get_workflow_modules():
    try:
        get_current_user()
        if request.args.get('path'):
            return jsonify(dt.workflows.get_module(request.args.get('path')).to_dict())
        return jsonify([module.to_dict() for module in dt.workflows.get_modules()])
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflow_modules/<module_id>')
@login_required
def get_workflow_module(module_id=None):
    try:
        get_current_user()
        return jsonify(dt.workflows.get_module_by_id(module_id).to_dict())
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def get_workflow(workflow_id=None):
    try:
        user = get_current_user()
        workflow = dt.workflows.get_workflow(user, workflow_id)
        if request.method == 'GET':
            return jsonify({**workflow.to_dict(), 'is_write_permitted': dt.users.is_write_permitted(user, workflow)})

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
                        workflow_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                        file.write(workflow_file_data)
                        del new_data['file']
                return jsonify(
                    dt.workflows.update_workflow(user, workflow, new_data, filename).to_dict())
            return jsonify(dt.workflows.update_workflow(user, workflow, new_data).to_dict())

        if request.method == 'DELETE':
            return jsonify(dt.workflows.delete_workflow(user, workflow))
    except Exception as e:
        return handle_exception(e)
