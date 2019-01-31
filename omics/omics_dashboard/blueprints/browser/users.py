from flask import render_template, Blueprint
from data_tools.users import get_users, get_user
from data_tools.template_data.entry_page import UserPageData
from data_tools.template_data.list_table import ListTableData
from helpers import get_current_user, handle_exception_browser
users = Blueprint('users', __name__, url_prefix='/users')


@users.route('/', methods=['GET'])
def render_user_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_users(current_user), 'Users'))
    except Exception as e:
        return handle_exception_browser(e)


@users.route('/<user_id>', methods=['GET'])
def render_user_profile(user_id=None):
    try:
        current_user = get_current_user()
        return render_template('pages/user_entry.html',
                               page_data=UserPageData(current_user, get_user(current_user, user_id)))
    except Exception as e:
        return handle_exception_browser(e)
