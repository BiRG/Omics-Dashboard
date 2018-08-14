from flask import render_template, request, redirect, url_for, jsonify, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception_browser
import ruamel.yaml as yaml
from io import StringIO

workflows = Blueprint('workflows', __name__)


@workflows.route('/workflows', methods=['GET', 'POST'])
def render_workflow_list():
    try:
        user_id = get_user_id()
        workflow_list = dt.workflows.get_workflows(user_id)
        headings = {'id': 'id', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=workflow_list, headings=headings, type='Workflows')
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def render_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        workflow = dt.workflows.get_workflow(user_id, workflow_id)
        return render_template('entry.html', type='Workflow', data=workflow)
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/workflows/create', methods=['GET', 'POST', 'DELETE'])
def render_create_workflow():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            workflow = dt.workflows.create_workflow(user_id, request.form.to_dict())
            return redirect(url_for('workflows.render_workflow', workflow_id=workflow['id']))
        return render_template('createbase.html', type='Workflow', endpoint='workflows.render_create_workflow')
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/workflow_modules')
def render_workflow_module_list():
    try:
        get_user_id()
        if request.args.get('path'):
            path = request.args.get('path')
            module = dt.workflows.get_module(path)
            with open(path, 'r') as file:
                module_contents = file.read()
            module = {key: module[key] for key in ['label', 'doc', 'id']}
            module['path'] = path
            return render_template('entry.html', type='Workflow Module',
                                   data=module,
                                   module_contents=module_contents)
        modules = dt.workflows.get_modules()
        headings = {
            'label': 'Label',
            'description': 'Description',
            'subPackageName': 'Package',
            'packageName': 'Parent Package'
        }
        [print(module) for module in modules]
        return render_template('list.html', type='Workflow Modules', headings=headings, data=modules)
    except Exception as e:
        return handle_exception_browser(e)
