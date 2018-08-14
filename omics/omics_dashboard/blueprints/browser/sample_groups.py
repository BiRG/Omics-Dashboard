from flask import render_template, Blueprint, request, redirect, url_for
import data_tools as dt
from helpers import handle_exception_browser, get_user_id
from functools import reduce
sample_groups = Blueprint('sample_groups', __name__, url_prefix='/sample_groups')


@sample_groups.route('/', methods=['GET', 'POST'])
def render_sample_group_list():
    try:
        get_user_id()
        data = dt.sample_groups.get_sample_groups(get_user_id())
        print(data)
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Sample Groups', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@sample_groups.route('/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample_group(sample_group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = dt.sample_groups.get_sample_group(user_id, sample_group_id)
            samples = data['members']
            del data['members']
            common_keys = list(reduce(set.intersection, [set(item.keys()) for item in samples]))
            sample_headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
            sample_headings.update({key: key for key in common_keys if key not in sample_headings})
            [
                sample_headings.pop(key, None) for key in
                (
                    'preproc',
                    'parser',
                    'owner',
                    'createdBy',
                    'userGroup',
                    'groupPermissions',
                    'allPermissions',
                    'dateModified'
                )
             ]
            return render_template('entry.html', type='Sample Group', data=data,
                                   samples=samples, sample_headings=sample_headings)
        if request.method == 'DELETE':
            dt.sample_groups.delete_sample_group(user_id, sample_group_id)
            return redirect(url_for('sample_groups.render_sample_group_list'))
        if request.method == 'POST':
            dt.sample_groups.update_sample_group(user_id, sample_group_id, request.form)
            data = dt.sample_groups.get_sample_group(user_id, sample_group_id)
            samples = data['members']
            del data['members']
            sample_headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
            common_keys = list(reduce(set.intersection, [set(item.keys()) for item in samples]))
            sample_headings.update({key: key for key in common_keys if key not in sample_headings})
            return render_template('entry.html', type='Sample', data=data,
                                   samples=samples, sample_headings=sample_headings)
    except Exception as e:
        return handle_exception_browser(e)
