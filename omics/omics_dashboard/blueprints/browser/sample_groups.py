from flask import render_template, Blueprint, request, redirect, url_for
import data_tools as dt
from helpers import handle_exception_browser, get_current_user, get_user_id
from functools import reduce
sample_groups = Blueprint('sample_groups', __name__, url_prefix='/sample_groups')


@sample_groups.route('/', methods=['GET', 'POST'])
def render_sample_group_list():
    try:
        user = get_current_user()
        data = [sample_group.to_dict() for sample_group in dt.sample_groups.get_sample_groups(user)]
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Sample Groups', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@sample_groups.route('/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample_group(sample_group_id=None):
    try:
        user = get_current_user()
        sample_group = dt.sample_groups.get_sample_group(user, sample_group_id)
        if request.method == 'GET':
            data = sample_group.to_dict()
            samples = data['samples']
            del data['samples']
            sample_headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
            return render_template('entry.html', type='Sample Group', data=data,
                                   samples=samples, sample_headings=sample_headings)
        if request.method == 'DELETE':
            dt.sample_groups.delete_sample_group(user, sample_group)
            return redirect(url_for('sample_groups.render_sample_group_list'))
        if request.method == 'POST':
            dt.sample_groups.update_sample_group(user, sample_group, request.form)
            data = dt.sample_groups.get_sample_group(user, sample_group).to_dict()
            samples = data['samples']
            del data['samples']
            sample_headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
            return render_template('entry.html', type='Sample', data=data,
                                   samples=samples, sample_headings=sample_headings)
    except Exception as e:
        return handle_exception_browser(e)
