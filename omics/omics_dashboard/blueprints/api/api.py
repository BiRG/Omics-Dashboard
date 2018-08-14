import json
import shutil

from flask import request, session, jsonify, Blueprint, url_for

import data_tools as dt
from data_tools.util import TMPDIR
from helpers import get_user_id, handle_exception
api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/')
def send_ok():
    message = f'API works! View {url_for("render_api_docs")} in your browser to see Swagger-UI documentation.'
    print(message)
    return jsonify({'message': message}), 200


@api.route('/login', methods=['POST'])
def login():
    credentials = request.get_json(force=True)
    if dt.users.validate_login(credentials['email'], credentials['password']):
        session['user'] = dt.users.get_user_by_email(credentials['email'])
        session['logged_in'] = True
        return jsonify(session['user']), 200
    else:
        return jsonify({"message": "authentication failed"}), 403


@api.route('/logout')
def logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return jsonify({'message': 'logged out'}), 200


@api.route('/authenticate', methods=['POST'])
def jwt_authenticate():
    credentials = request.get_json(force=True)
    if dt.users.validate_login(credentials['email'], credentials['password']):
        token = dt.users.get_jwt(credentials['email'], credentials['password'])
        return jsonify({'token': str(token)}), 200
    return jsonify({"message": "authentication failed"}), 403


@api.route('/invite', methods=['GET'])
def get_invitation():
    try:
        user_id = get_user_id()
        return jsonify(dt.users.create_invitation(user_id))
    except Exception as e:
        return handle_exception(e)


@api.route('/finalize', methods=['POST'])
def finalize_job():
    try:
        user_id = get_user_id()
        body = request.get_json(force=True)
        token = body['wfToken']
        path = f'{TMPDIR}/{token}'
        info = json.load(open(f'{path}/wfdata.json', 'r'))
        if dt.jobserver_control.check_jobserver_token(token) and dt.users.is_write_permitted(user_id, info):
            shutil.rmtree(f'{TMPDIR}/{token}', ignore_errors=True)
        return jsonify({'message': f'Removed {path}'})
    except Exception as e:
        return handle_exception(e)


@api.route('/currentuser')
def get_current_user():
    try:
        user_id = get_user_id()
        return jsonify(dt.users.get_user(user_id)), 200
    except Exception as e:
        return handle_exception(e)
