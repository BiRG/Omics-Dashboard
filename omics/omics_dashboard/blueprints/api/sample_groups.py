from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_current_user, handle_exception
sample_groups_api = Blueprint('sample_groups_api', __name__, url_prefix='/api/sample_groups')


@sample_groups_api.route('/', methods=['GET', 'POST'])
def list_sample_groups():
    try:
        return jsonify([sample_group.to_dict()
                        for sample_group in dt.sample_groups.get_sample_groups(get_current_user())])
    except Exception as e:
        return handle_exception(e)


@sample_groups_api.route('/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample_group(sample_group_id=None):
    try:
        user = get_current_user()
        sample_group = dt.sample_groups.get_sample_group(user, sample_group_id)
        if request.method == 'GET':
            return jsonify(sample_group.to_dict())
        if request.method == 'DELETE':
            return jsonify(dt.sample_groups.delete_sample_group(user, sample_group))
        if request.method == 'POST':
            return jsonify(dt.sample_groups
                           .update_sample_group(user, sample_group, request.get_json(force=True))
                           .to_dict())
    except Exception as e:
        return handle_exception(e)
