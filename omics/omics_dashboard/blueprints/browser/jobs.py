from flask import render_template, Blueprint

import data_tools as dt
from helpers import handle_exception_browser
jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/', methods=['GET', 'POST'])
def render_job_list():
    try:
        data = dt.jobserver_control.get_jobs()
        headings = {'id': 'Name', 'type': 'Type', 'status': 'Status', 'owner': 'Owner'}
        return render_template('list.html', data=data, headings=headings, type='Jobs')
    except Exception as e:
        return handle_exception_browser(e)


@jobs.route('/<job_id>', methods=['GET'])
def render_job(job_id=None):
    try:
        job = dt.jobserver_control.get_job(job_id)
        chart_data = dt.jobserver_control.get_job_chart_metadata(job_id)
        return render_template('entry.html', data=job, type="Job", chart_data=chart_data)
    except Exception as e:
        return handle_exception_browser(e)
