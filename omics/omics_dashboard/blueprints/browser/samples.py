import os

from flask import request, render_template, redirect, url_for, Blueprint
from werkzeug.utils import secure_filename

import data_tools as dt
from data_tools.util import UPLOADDIR
from helpers import get_user_id, get_current_user, handle_exception_browser
samples = Blueprint('samples', __name__, url_prefix='/samples')


@samples.route('/', methods=['GET', 'POST'])
def render_sample_list():
    try:
        get_user_id()
        data = dt.samples.get_all_sample_metadata(get_user_id())
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner', 'maxRowCount': 'Rows',
                    'maxColCount': 'Columns'}
        return render_template('list.html', type='Samples', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@samples.route('/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample(sample_id=None):
    try:
        user = get_current_user()
        sample = dt.samples.get_sample(user, sample_id)
        if request.method == 'GET':
            data = dt.samples.get_sample_metadata(user, sample)
            datasets = dt.samples.list_sample_paths(user, sample)
            return render_template('collectionentry.html', type='Sample', data=data, datasets=datasets)
        if request.method == 'DELETE':
            dt.samples.delete_sample(user, sample)
            return redirect(url_for('samples.render_sample_list'))
        if request.method == 'POST':
            dt.samples.update_sample(user, sample, request.form)
            data = dt.samples.get_sample_metadata(user, sample)
            datasets = dt.samples.list_sample_paths(user, sample)
            return render_template('collectionentry.html', type='Sample', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@samples.route('/create', methods=['GET', 'POST'])
def render_upload_sample():
    try:
        if request.method == 'POST':
            user = get_current_user()
            user_id = get_user_id()
            files = request.files.getlist('files')
            filenames = [os.path.join(UPLOADDIR, secure_filename(file. filename)) for file in files]
            [file.save(filename) for file, filename in zip(files, filenames)]
            metadata = request.form.to_dict()
            metadata['owner'] = user_id
            metadata['createdBy'] = user_id
            sample_group = dt.sample_groups.create_sample_group(user, metadata)
            workflow_data = dt.sample_creation.create_sample_creation_workflow(user_id, filenames, metadata)
            new_samples = [dt.samples.get_sample(user, sample_id) for sample_id in workflow_data['output_ids']]
            dt.sample_groups.update_sample_group_attachments(user, sample_group, new_samples)
            job = dt.jobserver_control.start_job(workflow_data['workflow'], workflow_data['job'], user)
            dt.sample_groups.update_sample_group(user, sample_group, {'upload_workflow_id': job['id']})
            return redirect(url_for('sample_groups.render_sample_group', sample_group_id=sample_group.id))
        return render_template('createbase.html', type='Sample', endpoint='samples.render_upload_sample')
    except Exception as e:
        return handle_exception_browser(e)
