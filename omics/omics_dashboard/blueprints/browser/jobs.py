from flask import render_template, Blueprint, request
from flask_login import login_required

from data_tools.access_wrappers.jobserver_control import get_jobs, get_job
from data_tools.template_data.entry_page import JobPageData
from data_tools.template_data.list_table import ListTableData
from data_tools.util import NotFoundException
from helpers import get_current_user
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
        return render_template('pages/help.html')
    except Exception as e:
        return handle_exception_browser(e)
