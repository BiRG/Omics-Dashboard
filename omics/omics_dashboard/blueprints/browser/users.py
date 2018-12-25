from flask import render_template, Blueprint

import data_tools as dt
from helpers import get_user_id, get_current_user, handle_exception_browser
users = Blueprint('users', __name__, url_prefix='/users')


@users.route('/', methods=['GET'])
def render_user_list():
    try:
        user = get_current_user()
        user_data = [target_user.to_dict() for target_user in dt.users.get_users(user)]
        headings = {'id': 'ID', 'name': 'Name', 'admin': 'Admin'}
        return render_template('list.html', type='Users', headings=headings, data=user_data)
    except Exception as e:
        return handle_exception_browser(e)


@users.route('/<user_id>', methods=['GET'])
def render_user_profile(user_id=None):
    try:
        user = get_current_user()
        target_user = dt.users.get_user(user, user_id)
        return render_template('entry.html', type='User', data=target_user.to_dict())
    except Exception as e:
        return handle_exception_browser(e)
