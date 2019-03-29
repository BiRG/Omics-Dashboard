from flask import request, redirect, url_for, render_template, Blueprint
from flask_login import login_required

from data_tools.db import User
from data_tools.template_data.entry_page import UserGroupPageData
from data_tools.template_data.form import UserGroupCreateFormData
from data_tools.template_data.list_table import ListTableData
from data_tools.user_groups import get_user_groups, get_user_group, create_user_group, delete_user_group
from data_tools.users import get_all_read_permitted_records
from helpers import get_current_user, handle_exception_browser

user_groups = Blueprint('user_groups', __name__, url_prefix='/user_groups')


@user_groups.route('/', methods=['GET'])
@login_required
def render_user_group_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_user_groups(current_user), 'User Groups'))
    except Exception as e:
        return handle_exception_browser(e)


@user_groups.route('/<user_group_id>', methods=['GET', 'DELETE'])
@login_required
def render_user_group(user_group_id=None):
    try:
        current_user = get_current_user()
        user_group = get_user_group(current_user, user_group_id)
        if request.method == 'DELETE':
            delete_user_group(current_user, user_group)
            return redirect(url_for('user_groups.render_user_group_list'))
        return render_template('pages/user_group_entry.html', page_data=UserGroupPageData(current_user, user_group))
    except Exception as e:
        return handle_exception_browser(e)


@user_groups.route('/create', methods=['GET', 'POST'])
@login_required
def render_create_user_group():
    try:
        current_user = get_current_user()
        if request.method == 'POST':
            data = {
                'admin_ids': [int(val) for val in request.form.getlist('admin_ids')],
                'member_ids': [int(val) for val in request.form.getlist('member_ids')],
                'name': request.form.get('name'),
                'description': request.form.get('description')
            }
            user_group = create_user_group(current_user, data)
            return redirect(url_for('user_groups.render_user_group', user_group_id=user_group.id))
        if request.method == 'GET':
            selected_user_ids = {int(token) for token in request.args.get('sample_ids').strip('"').split(',')} \
                if request.args.get('user_ids', '') else {}
            selected_users = get_all_read_permitted_records(current_user, User)
            return render_template('pages/create.html',
                                   page_data=UserGroupCreateFormData(current_user, selected_users))
    except Exception as e:
        return handle_exception_browser(e)
