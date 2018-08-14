from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception
users_api = Blueprint('users_api', __name__, url_prefix='/api/users')


@users_api.route('/', methods=['GET', 'POST'])
def list_users():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.users.create_user(user_id, data))
        return jsonify(dt.users.get_users())
    except Exception as e:
        return handle_exception(e)


@users_api.route('/<user_id>', methods=['GET', 'POST', 'DELETE'])
def edit_user(user_id=None):
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.users.get_user(user_id))
        if request.method == 'POST':
            return jsonify(dt.users.update_user(current_user_id, user_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(dt.users.delete_user(current_user_id, user_id))
    except Exception as e:
        return handle_exception(e)
