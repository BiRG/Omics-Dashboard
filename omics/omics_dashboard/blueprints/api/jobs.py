from flask import jsonify, request, Blueprint

import data_tools as dt
from helpers import handle_exception, get_current_user
jobs_api = Blueprint('jobs_api', __name__, url_prefix='/api/jobs')


@jobs_api.route('/', methods=['GET', 'POST'])
def list_jobs():
    try:
        return jsonify(dt.jobserver_control.get_jobs())
    except Exception as e:
        return handle_exception(e)


@jobs_api.route('/<job_id>', methods=['GET', 'POST'])
def get_job(job_id=None):
    try:
        user = get_current_user()
        if request.method == 'POST':
            action = request.args.get('method')
            if action:
                if action == 'resume':
                    return jsonify(dt.jobserver_control.resume_job(user, job_id))
                if action == 'cancel':
                    return jsonify(dt.jobserver_control.cancel_job(user, job_id))
        return jsonify(dt.jobserver_control.get_job(job_id))
    except Exception as e:
        return handle_exception(e)


@jobs_api.route('/<job_id>/metadata')
def get_chart_metadata(job_id=None):
    """
    Get a JSON string containing the javascript object used in the Gantt chart
    :param job_id:
    :return:
    """
    return jsonify(dt.jobserver_control.get_job_chart_metadata(job_id))


@jobs_api.route('/submit', methods=['POST'])
def submit_job():
    try:
        user = get_current_user()
        body = request.get_json(force=True)
        dt.jobserver_control.start_job(body['workflow'], body['job'], user, 'analysis')
    except Exception as e:
        return handle_exception(e)
