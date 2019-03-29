from flask import jsonify, request, Blueprint
from flask_login import login_required

import data_tools as dt
from helpers import handle_exception, get_current_user

jobs_api = Blueprint('jobs_api', __name__, url_prefix='/api/jobs')


@jobs_api.route('/', methods=['GET', 'POST'])
@login_required
def list_jobs():
    try:
        return jsonify([job.to_dict() for job in dt.jobserver_control.get_jobs()])
    except Exception as e:
        return handle_exception(e)


@jobs_api.route('/<job_id>', methods=['GET', 'POST'])
@login_required
def get_job(job_id=None):
    try:
        user = get_current_user()
        job = dt.jobserver_control.get_job(job_id)
        if request.method == 'POST':
            action = request.args.get('method')
            if action:
                if action == 'resume':
                    return jsonify(dt.jobserver_control.resume_job(user, job))
                if action == 'cancel':
                    return jsonify(dt.jobserver_control.cancel_job(user, job))
        return jsonify(job.to_dict())
    except Exception as e:
        return handle_exception(e)


@jobs_api.route('/<job_id>/metadata')
@login_required
def get_chart_metadata(job_id=None):
    """
    Get a JSON string containing the javascript object used in the Gantt chart
    :param job_id:
    :return:
    """
    job = dt.jobserver_control.get_job(job_id)
    return jsonify(dt.jobserver_control.get_job_chart_metadata(job))


@jobs_api.route('/submit', methods=['POST'])
@login_required
def submit_job():
    try:
        user = get_current_user()
        body = request.get_json(force=True)
        return jsonify(dt.jobserver_control.start_job(body['workflow'], body['job'], user, 'analysis').to_dict())
    except Exception as e:
        return handle_exception(e)
