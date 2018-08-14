from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception
sample_groups_api = Blueprint('sample_groups_api', __name__, url_prefix='/api/sample_groups')


@sample_groups_api.route('/', methods=['GET', 'POST'])
def list_sample_groups():
    try:
        return jsonify(dt.sample_groups.get_sample_groups(get_user_id()))
    except Exception as e:
        return handle_exception(e)


@sample_groups_api.route('/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample_group(sample_group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.sample_groups.get_sample_group(user_id, sample_group_id))
        if request.method == 'DELETE':
            return jsonify(dt.sample_groups.delete_sample_group(user_id, sample_group_id))
        if request.method == 'POST':
            return jsonify(dt.sample_groups.update_sample_group(user_id, sample_group_id, request.form))
    except Exception as e:
        return handle_exception(e)
