from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception
user_groups_api = Blueprint('user_groups_api', __name__, url_prefix='/api/user_groups')


@user_groups_api.route('/', methods=['GET', 'POST'])
def list_user_groups():
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.user_groups.get_user_groups())
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.user_groups.create_user_group(user_id, data))
    except Exception as e:
        return handle_exception(e)


@user_groups_api.route('/<group_id>', methods=['GET', 'POST', 'DELETE'])
def get_user_group(group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.user_groups.get_user_group(group_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            if 'users' in new_data:
                dt.user_groups.update_user_attachments(user_id, group_id, new_data['users'])
            return jsonify(dt.user_groups.update_user_group(user_id, group_id, new_data))
        if request.method == 'DELETE':
            return jsonify(dt.user_groups.delete_user_group(user_id, group_id))
    except Exception as e:
        return handle_exception(e)
