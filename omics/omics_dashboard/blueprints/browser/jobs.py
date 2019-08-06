from flask import render_template, Blueprint, request, redirect, url_for
from flask_login import login_required

from data_tools.access_wrappers.jobserver_control import get_jobs, get_job, start_job, prepare_job_params
from data_tools.access_wrappers.workflows import get_workflow
from data_tools.template_data.entry_page import JobPageData
from data_tools.template_data.form import SubmitFormData
from data_tools.template_data.list_table import ListTableData
from data_tools.util import NotFoundException
from helpers import get_current_user, process_input_dict
from helpers import handle_exception_browser

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/', methods=['GET', 'POST'])
@login_required
def render_job_list():
    try:
        return render_template('pages/list.html',
                               page_data=ListTableData(get_current_user(), get_jobs(), 'Jobs'))
    except Exception as e:
        return handle_exception_browser(e)


@jobs.route('/<job_id>', methods=['GET'])
@login_required
def render_job(job_id=None):
    try:
        return render_template('pages/job_entry.html',
                               page_data=JobPageData(get_current_user(), get_job(job_id)))
    except Exception as e:
        return handle_exception_browser(e)


@jobs.route('/submit', methods=['GET', 'POST'])
@login_required
def render_submit_job():
    try:
        if request.args.get('workflow_id') is None:
            raise NotFoundException(f'No workflow id provided')
        current_user = get_current_user()
        workflow = get_workflow(current_user, request.args.get('workflow_id'))
        workflow_data = workflow.get_file_info()
        if request.method == 'POST':
            job_params, workflow_data, labels, options = prepare_job_params(workflow_data,
                                                                            process_input_dict(request.form),
                                                                            current_user, workflow.id)
            job = start_job(workflow_data, job_params, current_user, 'analysis', labels, options)
            return redirect(url_for('jobs.render_job', job_id=job.id))
        page_data = SubmitFormData(current_user, workflow_data, f'Workflow {workflow.id}')
        return render_template('pages/submit_job.html', page_data=page_data)
    except Exception as e:
        return handle_exception_browser(e)
