from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_current_user, handle_exception
users_api = Blueprint('users_api', __name__, url_prefix='/api/users')


@users_api.route('/', methods=['GET', 'POST'])
def list_users():
    try:
        user = get_current_user()
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.users.create_user(user, data).to_dict())
        return jsonify([user.to_dict() for user in dt.users.get_users()])
    except Exception as e:
        return handle_exception(e)


@users_api.route('/<user_id>', methods=['GET', 'POST', 'DELETE'])
def edit_user(user_id=None):
    try:
        current_user = get_current_user()
        target_user = dt.users.get_user(user_id)
        if request.method == 'GET':
            return jsonify(target_user.to_dict())
        if request.method == 'POST':
            return jsonify(dt.users.update_user(current_user, target_user, request.get_json(force=True)).to_dict())
        if request.method == 'DELETE':
            return jsonify(dt.users.delete_user(current_user, target_user))
    except Exception as e:
        return handle_exception(e)
