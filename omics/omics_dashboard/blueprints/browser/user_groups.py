from flask import request, redirect, url_for, render_template, Blueprint

import data_tools as dt
from helpers import get_user_id, get_current_user, handle_exception_browser
user_groups = Blueprint('user_groups', __name__, url_prefix='/user_groups')


@user_groups.route('/', methods=['GET'])
def render_user_group_list():
    try:
        user = get_current_user()
        user_group_list = [user_group.to_dict() for user_group in dt.user_groups.get_user_groups(user)]
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'creator_id': 'Created By'}
        return render_template('list.html', data=user_group_list, type='User Groups', headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@user_groups.route('/<user_group_id>', methods=['GET', 'DELETE'])
def render_user_group(user_group_id=None):
    try:
        user = get_current_user()
        user_group = dt.user_groups.get_user_group(user, user_group_id)
        if request.method == 'DELETE':
            dt.user_groups.delete_user_group(user, user_group)
            return redirect(url_for('user_groups.render_user_group_list'))
        return render_template('entry.html', type='User Group', data=user_group.to_dict(), all_users=dt.users.get_users())
    except Exception as e:
        return handle_exception_browser(e)


@user_groups.route('/create', methods=['GET', 'POST'])
def render_create_user_group():
    try:
        user = get_current_user()
        if request.method == 'POST':
            other_user_ids = [int(uid) for uid in request.form.getlist('user')]
            user_group = dt.user_groups.create_user_group(user, request.form.to_dict())
            users = [dt.users.get_user(user_id) for user_id in other_user_ids]
            dt.user_groups.update_user_attachments(user, user_group, users)
            return redirect(url_for('user_groups.render_user_group', group_id=user_group.id))
        return render_template('createbase.html', type='User Group', users=dt.users.get_users(),
                               endpoint='user_groups.render_create_user_group')
    except Exception as e:
        return handle_exception_browser(e)
