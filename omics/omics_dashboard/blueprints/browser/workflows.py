from flask import render_template, request, redirect, url_for, Blueprint

from data_tools.workflows import get_workflow, get_workflows, get_modules, get_module, create_workflow, get_workflow_template
from data_tools.template_data.form import WorkflowCreateFormData
from data_tools.template_data.entry_page import WorkflowPageData, WorkflowModulePageData
from data_tools.template_data.list_table import ListTableData
from helpers import get_current_user, handle_exception_browser, process_input_dict

workflows = Blueprint('workflows', __name__, url_prefix='/workflows')


@workflows.route('/', methods=['GET', 'POST'])
def render_workflow_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_workflows(current_user), 'Workflows'))
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/<workflow_id>', methods=['GET'])
def render_workflow(workflow_id=None):
    try:
        current_user = get_current_user()
        return render_template('pages/workflow_entry.html',
                               page_data=WorkflowPageData(current_user, get_workflow(current_user, workflow_id)))
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/create', methods=['GET', 'POST', 'DELETE'])
def render_create_workflow():
    try:
        current_user = get_current_user()
        if request.method == 'POST':
            req_data = process_input_dict(request.form.to_dict())
            workflow = create_workflow(current_user, process_input_dict(request.form.to_dict(), True))
            return redirect(url_for('workflows.render_workflow', workflow_id=workflow.id))
        return render_template('pages/create.html',
                               page_data=WorkflowCreateFormData(current_user))
    except Exception as e:
        return handle_exception_browser(e)


@workflows.route('/workflow_modules')
def render_workflow_module_list():
    try:
        current_user = get_current_user()
        if request.args.get('path'):
            path = request.args.get('path')
            module = get_module(path)
            return render_template('pages/workflow_module_entry.html',
                                   page_data=WorkflowModulePageData(current_user, module))
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_modules(), 'Workflow Modules'))
    except Exception as e:
        return handle_exception_browser(e)
