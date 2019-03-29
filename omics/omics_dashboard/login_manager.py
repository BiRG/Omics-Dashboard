import os

import jwt
from flask_login import LoginManager

from data_tools.db import User
from data_tools.util import LoginError

login_manager = LoginManager()
login_manager.login_view = 'browser.browser_login'
login_manager.blueprint_login_views = {
    'api': 'api.unauthorized',
    'analyses_api': 'api.unauthorized',
    'collections_api': 'api.unauthorized',
    'external_files_api': 'api.unauthorized',
    'jobs_api': 'api.unauthorized',
    'sample_groups_api': 'api.unauthorized',
    'samples_api': 'api.unauthorized',
    'user_groups_api': 'api.unauthorized',
    'users_api': 'api.unauthorized',
    'workflows_api': 'api.unauthorized'
}


@login_manager.user_loader
def user_loader(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return
    return user


@login_manager.request_loader
def request_loader(req):
    if 'Authorization' in req.headers:
        auth_header = req.headers.get('Authorization')
        # Header should be in format "JWT <>" or "Bearer <>"
        token = auth_header.split(' ')[1]
        # if this is invalid, jwt.decode will throw. So no need to check password
        user_data = jwt.decode(token, os.environ['SECRET'], algorithms=['HS256'])
        return User.query.filter_by(id=user_data['id']).first()


def authenticate_user(req):
    # This can be either a form with email and password fields or a JSON object
    if req.content_type == 'application/json':
        data = req.get_json(force=True)
        email = data['email']
        password = data['password']
    else:
        email = req.form.get('email')
        password = req.form.get('password')
    user = User.query.filter_by(email=email).first()
    if user.check_password(password):
        return user
    raise LoginError('Incorrect email/password.')
