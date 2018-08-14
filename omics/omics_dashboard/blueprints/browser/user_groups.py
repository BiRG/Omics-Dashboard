from flask import request, redirect, url_for, render_template, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception_browser
user_groups = Blueprint('user_groups', __name__, url_prefix='/user_groups')


@user_groups.route('/', methods=['GET'])
def render_user_group_list():
    try:
        get_user_id()
        user_group_list = dt.user_groups.get_user_groups()
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'createdBy': 'Created By'}
        return render_template('list.html', data=user_group_list, type='User Groups', headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@user_groups.route('/<group_id>', methods=['GET', 'DELETE'])
def render_user_group(group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'DELETE':
            dt.user_groups.delete_user_group(user_id, group_id)
            return redirect(url_for('user_groups.render_user_group_list'))
        user_group = dt.user_groups.get_user_group(group_id)
        del user_group['members']
        return render_template('entry.html', type='User Group', data=user_group, all_users=dt.users.get_users())
    except Exception as e:
        return handle_exception_browser(e)


@user_groups.route('/create', methods=['GET', 'POST'])
def render_create_user_group():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            other_user_ids = [int(uid) for uid in request.form.getlist('user')]
            print(other_user_ids)
            user_group = dt.user_groups.create_user_group(user_id, request.form.to_dict())
            for other_user_id in other_user_ids:
                dt.user_groups.attach_user(user_id, other_user_id, user_group['id'])
            return redirect(url_for('user_groups.render_user_group', group_id=user_group['id']))
        return render_template('createbase.html', type='User Group', users=dt.users.get_users(),
                               endpoint='user_groups.render_create_user_group')
    except Exception as e:
        return handle_exception_browser(e)
