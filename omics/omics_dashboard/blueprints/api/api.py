import json
import os
import shutil

from flask import request, jsonify, Blueprint, url_for, send_from_directory
from flask_login import login_user, logout_user, login_required

import data_tools as dt
import helpers
from data_tools.util import TMPDIR
from helpers import handle_exception
from login_manager import authenticate_user

api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/')
def send_ok():
    message = f'API works! View {url_for("browser.render_api_docs")} in your browser to see Swagger-UI documentation.'
    print(message)
    return jsonify({'message': message}), 200


@api.route('/login', methods=['POST'])
def login():
    try:
        user = authenticate_user(request)
        login_user(user)
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({'message': 'authentication failed', 'exception': str(e)}), 403


@api.route('/logout')
@login_required
def logout():
    dt.redis.clear_user_hash(get_current_user().id)
    logout_user()
    return jsonify({'message': 'logged out'}), 200


@api.route('/authenticate', methods=['POST'])
def jwt_authenticate():
    try:
        credentials = request.get_json(force=True)
        authenticate_user(request)
        token = dt.users.get_jwt_by_email(credentials['email'], credentials['password'])
        return jsonify({'token': str(token)}), 200
    except Exception as e:
        return jsonify({'message': f'authentication failed: {e}'}), 403


@api.route('/invite', methods=['GET'])
@login_required
def create_invitation():
    #  We use 'GET' even though we're creating a record
    #  we probably shouldn't ?
    try:
        current_user = helpers.get_current_user()
        primary_user_group_id = request.args.get('primary_user_group_id')
        try:
            primary_user_group = dt.user_groups.get_user_group(current_user, primary_user_group_id) if primary_user_group_id is not None else None
        except dt.util.NotFoundException:
            primary_user_group = None
            pass
        return jsonify(dt.users.create_invitation(current_user, primary_user_group).to_dict())
    except Exception as e:
        return handle_exception(e)


@api.route('/invitations', methods=['GET'])
@login_required
def list_invitations():
    try:
        current_user = helpers.get_current_user()
        return jsonify([invitation.to_dict() for invitation in dt.users.get_invitations(current_user)])
    except Exception as e:
        return handle_exception(e)


@api.route('/invitations/<invitation_id>', methods=['GET', 'DELETE'])
@login_required
def get_invitation(invitation_id=None):
    try:
        current_user = helpers.get_current_user()
        invitation = dt.users.get_invitation(current_user, invitation_id)
        if request.method == 'DELETE':
            return jsonify(dt.users.delete_invitation(current_user, invitation))
        else:
            return jsonify(invitation.to_dict())
    except Exception as e:
        handle_exception(e)


@api.route('/finalize', methods=['POST'])
@login_required
def finalize_job():
    try:
        user = helpers.get_current_user()
        body = request.get_json(force=True)
        token = body['wf_token']
        path = f'{TMPDIR}/{token}'
        info = json.load(open(f'{path}/wfdata.json', 'r'))
        if dt.jobserver_control.check_jobserver_token(token) and (user.admin or info['owner'] == user.id):
            shutil.rmtree(f'{TMPDIR}/{token}', ignore_errors=True)
        return jsonify({'message': f'Removed {path}'})
    except Exception as e:
        print(e)
        return handle_exception(e)


@api.route('/current_user')
@login_required
def get_current_user():
    try:
        user = helpers.get_current_user()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Not logged in'}), 401


@api.route('/unauthorized')
def unauthorized():
    return jsonify({'message': 'Not authenticated.'}), 401


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


@api.route('/download_tmp')
@login_required
def download_temporary_file():
    path = request.args.get('path')
    if path is None:
        return handle_exception(ValueError('No path specified!'))
    if not os.path.isfile(path):
        print(path)
        return handle_exception(ValueError('File does not exist!'))
    return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True)
