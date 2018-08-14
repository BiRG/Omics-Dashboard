from flask import jsonify, request, Blueprint

import data_tools as dt
from helpers import handle_exception, get_user_id
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
        user_id = get_user_id()
        if request.method == 'POST':
            action = request.args.get('method')
            if action:
                if action == 'resume':
                    return jsonify(dt.jobserver_control.resume_job(user_id, job_id))
                if action == 'cancel':
                    return jsonify(dt.jobserver_control.cancel_job(user_id, job_id))
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

