from flask import request, jsonify, Blueprint
from flask_login import login_required

import data_tools as dt
from helpers import get_current_user, handle_exception

user_groups_api = Blueprint('user_groups_api', __name__, url_prefix='/api/user_groups')


@user_groups_api.route('/', methods=['GET', 'POST'])
@login_required
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
@login_required
def get_user_group(user_group_id=None):
    try:
        user = get_current_user()
        user_group = dt.user_groups.get_user_group(user, user_group_id)
        if request.method == 'GET':
            return jsonify(
                {**user_group.to_dict(), 'is_write_permitted': dt.users.is_write_permitted(user, user_group)})
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            if 'member_ids' in new_data:
                users = [dt.users.get_user(user, user_id) for user_id in new_data['member_ids']]
                dt.user_groups.update_user_attachments(user, user_group, users)
            if 'admin_ids' in new_data:
                admin_users = [dt.users.get_user(user, user_id) for user_id in new_data['admin_ids']]
                dt.user_groups.update_admins(user, user_group, admin_users)
                for admin_user in admin_users:
                    dt.user_groups.elevate_user(user, admin_user, user_group)
            return jsonify(
                dt.user_groups.update_user_group(user, user_group, new_data).to_dict())
        if request.method == 'DELETE':
            return jsonify(dt.user_groups.delete_user_group(user, user_group))
    except Exception as e:
        return handle_exception(e)
