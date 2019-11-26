from flask import render_template, Blueprint
from flask_login import login_required

from data_tools.wrappers.users import get_users, get_user, get_mailto_all
from data_tools.template_models.entry_page import UserPageData
from data_tools.template_models.list_table import UserListTableData
from helpers import get_current_user, handle_exception_browser

users = Blueprint('users', __name__, url_prefix='/users')


@users.route('/', methods=['GET'])
@login_required
def render_user_list():
    try:
        current_user = get_current_user()
        if current_user.admin:
            mailto = get_mailto_all()
        else:
            mailto = None
        return render_template('pages/user_list.html',
                               page_data=UserListTableData(current_user, get_users(current_user), mailto))
    except Exception as e:
        return handle_exception_browser(e)


@users.route('/<user_id>', methods=['GET'])
@login_required
def render_user_profile(user_id=None):
    try:
        current_user = get_current_user()
        return render_template('pages/user_entry.html',
                               page_data=UserPageData(current_user, get_user(current_user, user_id)))
    except Exception as e:
        return handle_exception_browser(e)
