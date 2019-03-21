from flask import jsonify, request, Blueprint

import data_tools as dt
from data_tools.users import is_write_permitted
from helpers import get_current_user, handle_exception

workflows_api = Blueprint('workflows_api', __name__, url_prefix='/api/workflows')


@workflows_api.route('/', methods=['GET', 'POST'])
def list_workflows():
    try:
        user = get_current_user()
        return jsonify([workflow.to_dict() for workflow in dt.workflows.get_workflows(user)])
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflow_modules')
def get_workflow_modules():
    try:
        get_current_user()
        if request.args.get('path'):
            return jsonify(dt.workflows.get_module(request.args.get('path')).to_dict())
        return jsonify([module.to_dict() for module in dt.workflows.get_modules()])
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/workflow_modules/<module_id>')
def get_workflow_module(module_id=None):
    try:
        get_current_user()
        return jsonify(dt.workflows.get_module_by_id(module_id).to_dict())
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def get_workflow(workflow_id=None):
    try:
        user = get_current_user()
        workflow = dt.workflows.get_workflow(user, workflow_id)
        if request.method == 'GET':
            return jsonify({**workflow.to_dict(), 'is_write_permitted': is_write_permitted(user, workflow)})
        if request.method == 'POST':
            return jsonify(dt.workflows.update_workflow(user, workflow, request.get_json(force=True)).to_dict())
        if request.method == 'DELETE':
            return jsonify(dt.workflows.delete_workflow(user, workflow))
    except Exception as e:
        return handle_exception(e)


@workflows_api.route('/create')
def create_workflow():
    try:
        user = get_current_user()
        return jsonify(dt.workflows.create_workflow(user, request.get_json()).to_dict())
    except Exception as e:
        return handle_exception(e)
