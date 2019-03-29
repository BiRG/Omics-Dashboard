import os

from flask import render_template, Blueprint, request, redirect, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from data_tools.jobserver_control import start_job
from data_tools.sample_creation import create_sample_creation_workflow
from data_tools.sample_groups import get_sample_group, get_sample_groups, update_sample_group, delete_sample_group, \
    create_sample_group
from data_tools.samples import get_sample, delete_sample
from data_tools.template_data.entry_page import SampleGroupPageData
from data_tools.template_data.form import SampleCreateFormData
from data_tools.template_data.list_table import ListTableData
from data_tools.util import UPLOADDIR, AuthException
from helpers import handle_exception_browser, get_current_user, process_input_dict

sample_groups = Blueprint('sample_groups', __name__, url_prefix='/sample_groups')


@sample_groups.route('/', methods=['GET', 'POST'])
@login_required
def render_sample_group_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_sample_groups(current_user), 'Sample Groups'))
    except Exception as e:
        return handle_exception_browser(e)


@sample_groups.route('/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def render_sample_group(sample_group_id=None):
    try:
        current_user = get_current_user()
        sample_group = get_sample_group(current_user, sample_group_id)
        if request.method == 'DELETE':
            samples_to_delete = [sample for sample in sample_group.samples if len(sample.sample_groups) < 2]
            print(f'samples_to_delete: {samples_to_delete}')
            delete_sample_group(current_user, sample_group)
            print(f'samples_to_delete: {samples_to_delete}')
            for sample in samples_to_delete:
                try:
                    delete_sample(current_user, sample)
                except AuthException:
                    pass
            return redirect(url_for('sample_groups.render_sample_group_list'))
        if request.method == 'POST':
            update_sample_group(current_user, sample_group, request.form)
        return render_template('pages/sample_group_entry.html',
                               page_data=SampleGroupPageData(current_user, sample_group))
    except Exception as e:
        return handle_exception_browser(e)


@sample_groups.route('/create', methods=['GET', 'POST'])
@login_required
def render_upload_sample_group():
    try:
        current_user = get_current_user()
        if request.method == 'POST':
            files = request.files.getlist('files')
            filenames = [os.path.join(UPLOADDIR, secure_filename(file.filename)) for file in files]
            [file.save(filename) for file, filename in zip(files, filenames)]
            metadata = process_input_dict(request.form.to_dict(), True)
            workflow_data = create_sample_creation_workflow(current_user, filenames, metadata)
            metadata['samples'] = [get_sample(current_user, sample_id) for sample_id in workflow_data['output_ids']]
            sample_group = create_sample_group(current_user, metadata)
            job = start_job(workflow_data['workflow'], workflow_data['job'], current_user, 'upload')
            update_sample_group(current_user, sample_group, {'upload_job_id': job.id})
            return redirect(url_for('sample_groups.render_sample_group', sample_group_id=sample_group.id))
        return render_template('pages/create.html',
                               page_data=SampleCreateFormData(current_user))
    except Exception as e:
        return handle_exception_browser(e)
