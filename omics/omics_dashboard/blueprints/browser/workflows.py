from flask import render_template, request, redirect, url_for, jsonify, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception_browser
workflows = Blueprint('workflows', __name__, url_prefix='/workflows')


@workflows.route('/', methods=['GET', 'POST'])
def render_workflow_list():
    try:
        user_id = get_user_id()
        workflow_list = dt.workflows.get_workflows(user_id)
        headings = {'id': 'id', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=workflow_list, headings=headings, type='Workflows')
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def render_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        workflow = dt.workflows.get_workflow(user_id, workflow_id)
        return render_template('entry.html', type='Workflow', data=workflow)
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/create', methods=['GET', 'POST', 'DELETE'])
def render_create_workflow():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            workflow = dt.workflows.create_workflow(user_id, request.form.to_dict())
            return redirect(url_for('render_workflow', workflow_id=workflow['id']))
        return render_template('createbase.html', type='Workflow', endpoint='render_create_workflow')
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/modules', methods=['GET', 'POST', 'DELETE'])
def render_workflow_modules():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)
