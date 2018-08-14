from flask import render_template, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception_browser
users = Blueprint('users', __name__, url_prefix='/users')


@users.route('/', methods=['GET'])
def render_user_list():
    try:
        get_user_id()
        user_list = dt.users.get_users()
        headings = {'id': 'ID', 'name': 'Name', 'admin': 'Admin'}
        return render_template('list.html', type='Users', headings=headings, data=user_list)
    except Exception as e:
        return handle_exception_browser(e)


@users.route('/<user_id>', methods=['GET'])
def render_user_profile(user_id=None):
    try:
        get_user_id()
        user = dt.users.get_user(user_id)
        return render_template('entry.html', type='User', data=user)
    except Exception as e:
        return handle_exception_browser(e)
