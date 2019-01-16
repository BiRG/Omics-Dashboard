import json
import shutil

from flask import request, session, jsonify, Blueprint, url_for

import data_tools as dt
from data_tools.util import TMPDIR
import helpers
from helpers import handle_exception
api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/')
def send_ok():
    message = f'API works! View {url_for("browser.render_api_docs")} in your browser to see Swagger-UI documentation.'
    print(message)
    return jsonify({'message': message}), 200


@api.route('/login', methods=['POST'])
def login():
    credentials = request.get_json(force=True)
    if dt.users.validate_login(credentials['email'], credentials['password']):
        session['user'] = dt.users.get_user_by_email(credentials['email']).to_dict()
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
        token = dt.users.get_jwt_by_email(credentials['email'], credentials['password'])
        return jsonify({'token': str(token)}), 200
    return jsonify({"message": "authentication failed"}), 403


@api.route('/invite', methods=['GET'])
def get_invitation():
    try:
        user = helpers.get_current_user()
        return jsonify(dt.users.create_invitation(user))
    except Exception as e:
        return handle_exception(e)


@api.route('/finalize', methods=['POST'])
def finalize_job():
    try:
        user = helpers.get_current_user()
        body = request.get_json(force=True)
        token = body['wf_token']
        path = f'{TMPDIR}/{token}'
        info = json.load(open(f'{path}/wfdata.json', 'r'))
        if dt.jobserver_control.check_jobserver_token(token) and dt.users.is_write_permitted(user, info):
            shutil.rmtree(f'{TMPDIR}/{token}', ignore_errors=True)
        return jsonify({'message': f'Removed {path}'})
    except Exception as e:
        return handle_exception(e)


@api.route('/current_user')
def get_current_user():
    try:
        user = helpers.get_current_user()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Not logged in'}), 401


@api.route('/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json(force=True)
        if 'invitation' not in data:
            raise ValueError('No invitation code provided.')
        if request.method == 'POST':
            change_password = not (data['password1'] == '' and data['password2'] == '')
            valid_passwords = data['password1'] == data['password2'] if change_password else False
            if not valid_passwords:
                raise ValueError('Passwords do not match.')
            new_user = dt.users.register_user(data['invitation'],
                                              {'email': data['email'],
                                               'password': data['password1'],
                                               'name': data['name']
                                               })
            return jsonify(new_user.to_dict())
    except Exception as e:
        return handle_exception(e)
