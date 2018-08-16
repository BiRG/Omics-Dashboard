from flask import jsonify, request, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception
workflows_api = Blueprint('workflows_api', __name__, url_prefix='/api')


@workflows_api.route('/workflows', methods=['GET', 'POST'])
def list_workflows():
    try:
        user_id = get_user_id()
        return jsonify(dt.workflows.get_workflows(user_id))
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflow_modules')
def get_workflow_modules():
    try:
        get_user_id()
        if request.args.get('path'):
            return jsonify(dt.workflows.get_module(request.args.get('path')))
        return jsonify(dt.workflows.get_modules())
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def get_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.workflows.get_workflow(user_id, workflow_id))
        if request.method == 'POST':
            return jsonify(dt.workflows.update_workflow(user_id, workflow_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(dt.workflows.delete_workflow(user_id, workflow_id))
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflows/create')
def create_workflow():
    try:
        user_id = get_user_id()
        return jsonify(dt.workflows.create_workflow(user_id, request.get_json()))
    except Exception as e:
        return handle_exception(e)
