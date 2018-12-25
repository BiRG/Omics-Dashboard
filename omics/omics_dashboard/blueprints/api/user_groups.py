from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_current_user, handle_exception
user_groups_api = Blueprint('user_groups_api', __name__, url_prefix='/api/user_groups')


@user_groups_api.route('/', methods=['GET', 'POST'])
def list_user_groups():
    try:
        user = get_current_user()
        if request.method == 'GET':
            return jsonify([user_group.to_dict() for user_group in dt.user_groups.get_user_groups(user)])
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.user_groups.create_user_group(user, data).to_dict())
    except Exception as e:
        return handle_exception(e)


@user_groups_api.route('/<user_group_id>', methods=['GET', 'POST', 'DELETE'])
def get_user_group(user_group_id=None):
    try:
        user = get_current_user()
        user_group = dt.user_groups.get_user_group(user, user_group_id)
        if request.method == 'GET':
            return jsonify(user_group.to_dict())
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            if 'user_ids' in new_data:
                users = [dt.users.get_user(user_id) for user_id in new_data['user_ids']]
                dt.user_groups.update_user_attachments(user, user_group, users)
            return jsonify(dt.user_groups.update_user_group(user, user_group, new_data))
        if request.method == 'DELETE':
            return jsonify(dt.user_groups.delete_user_group(user, user_group))
    except Exception as e:
        return handle_exception(e)
