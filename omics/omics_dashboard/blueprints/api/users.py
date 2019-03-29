from flask import request, jsonify, Blueprint
from flask_login import login_required, fresh_login_required

import data_tools as dt
from data_tools.users import is_write_permitted
from helpers import get_current_user, handle_exception

users_api = Blueprint('users_api', __name__, url_prefix='/api/users')


@users_api.route('/', methods=['GET', 'POST'])
@login_required
def list_users():
    try:
        user = get_current_user()
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.users.create_user(user, data).to_dict())
        return jsonify([target_user.to_dict() for target_user in dt.users.get_users(user)])
    except Exception as e:
        return handle_exception(e)


@users_api.route('/<user_id>', methods=['GET', 'POST', 'DELETE'])
@fresh_login_required
def get_user(user_id=None):
    try:
        current_user = get_current_user()
        target_user = dt.users.get_user(current_user, user_id)
        if request.method == 'GET':
            return jsonify(
                {**target_user.to_dict(), 'is_write_permitted': is_write_permitted(current_user, target_user)})
        if request.method == 'POST':
            return jsonify(dt.users.update_user(current_user, target_user, request.get_json(force=True)).to_dict())
        if request.method == 'DELETE':
            return jsonify(dt.users.delete_user(current_user, target_user))
    except Exception as e:
        return handle_exception(e)
