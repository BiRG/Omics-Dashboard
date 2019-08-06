import datetime
import inspect
import traceback

from flask import url_for, request, render_template, redirect, jsonify
from flask_login import current_user

import data_tools as dt
from data_tools.util import LoginError, DATADIR

log_file_name = f'{DATADIR}/logs/omics.log'


def get_user_display_data(user_id):
    return get_profile_link(user_id), dt.users.get_user_name(user_id)


def get_item_link(record):
    if isinstance(record, dt.db_models.Collection):
        return url_for('collections.render_collection', collection_id=record.id)
    elif isinstance(record, dt.db_models.Sample):
        return url_for('samples.render_sample', sample_id=record.id)
    elif isinstance(record, dt.db_models.SampleGroup):
        return url_for('sample_groups.render_sample_group', sample_group_id=record.id)
    elif isinstance(record, dt.db_models.User):
        return url_for('users.render_user_profile', user_id=record.id)
    elif isinstance(record, dt.db_models.UserGroup):
        return url_for('user_groups.render_user_group', user_group_id=record.id)
    elif isinstance(record, dt.db_models.Analysis):
        return url_for('analyses.render_analysis', analysis_id=record.id)
    elif isinstance(record, dt.db_models.Workflow):
        return url_for('workflows.render_workflow', workflow_id=record.id)
    elif isinstance(record, dt.jobserver_control.Job):
        if record.id is None:
            return url_for('jobs.render_job_list')
        return url_for('jobs.render_job', job_id=record.id)
    elif isinstance(record, dt.workflows.WorkflowModule):
        return url_for('workflows.render_workflow_module_list', path=record.path)
    elif isinstance(record, dt.db_models.ExternalFile):
        return url_for('external_files.render_external_file', external_file_id=record.id)
    elif inspect.isclass(record) and hasattr(record, 'prefix'):
        return url_for('browser.render_root') + record.prefix[1:]
    return '#'


def get_update_url(record):
    if isinstance(record, dt.db_models.Collection):
        return url_for('collections_api.get_collection', collection_id=record.id)
    elif isinstance(record, dt.db_models.Sample):
        return url_for('samples_api.get_sample', sample_id=record.id)
    elif isinstance(record, dt.db_models.SampleGroup):
        return url_for('sample_groups_api.get_sample_group', sample_group_id=record.id)
    elif isinstance(record, dt.db_models.Analysis):
        return url_for('analyses_api.get_analysis', analysis_id=record.id)
    elif isinstance(record, dt.db_models.Workflow):
        return url_for('workflows_api.get_workflow', workflow_id=record.id)
    elif isinstance(record, dt.db_models.UserGroup):
        return url_for('user_groups_api.get_user_group', user_group_id=record.id)
    elif isinstance(record, dt.db_models.User):
        return url_for('users_api.get_user', user_id=record.id)
    elif isinstance(record, dt.db_models.ExternalFile):
        return url_for('external_files_api.get_external_file', external_file_id=record.id)
    return '#'


def get_list_url(record):
    if isinstance(record, dt.db_models.Collection):
        return url_for('collections.render_collection_list')
    elif isinstance(record, dt.db_models.Sample):
        return url_for('samples.render_sample_list')
    elif isinstance(record, dt.db_models.SampleGroup):
        return url_for('sample_groups.render_sample_group_list')
    elif isinstance(record, dt.db_models.User):
        return url_for('users.render_user_list')
    elif isinstance(record, dt.db_models.UserGroup):
        return url_for('user_groups.render_user_group_list')
    elif isinstance(record, dt.db_models.Analysis):
        return url_for('analyses.render_analysis_list')
    elif isinstance(record, dt.db_models.Workflow):
        return url_for('workflows.render_workflow_list')
    elif isinstance(record, dt.jobserver_control.Job):
        return url_for('jobs.render_job_list', job_id=record.id)
    elif isinstance(record, dt.workflows.WorkflowModule):
        return url_for('workflows.render_workflow_module_list')
    elif isinstance(record, dt.db_models.ExternalFile):
        return url_for('external_files.render_external_file_list')
    return '#'


def get_download_url(record):
    if isinstance(record, dt.db_models.Collection):
        return url_for('collections_api.download_collection', collection_id=record.id)
    elif isinstance(record, dt.db_models.Sample):
        return url_for('samples_api.download_sample', sample_id=record.id)
    elif isinstance(record, dt.db_models.ExternalFile):
        return url_for('external_files_api.download_external_file', external_file_id=record.id)
    return '#'


def get_profile_link(user_id):
    return url_for('users.render_user_profile', user_id=user_id)


def get_current_user():
    return current_user


def handle_exception_browser(e):
    print('handle_exception_browser')
    if isinstance(e, dt.util.NotFoundException):
        log_exception(404, e)
        error_msg = str(e)
        error_title = '404 Not Found'
        return render_template('pages/error.html', fa_type='fa-question-circle', alert_class='alert-warning', error_msg=error_msg, error_title=error_title), 404
    if isinstance(e, dt.util.AuthException):
        log_exception(403, e)
        error_msg = str(e)
        error_title = '403 Forbidden'
        return render_template('pages/error.html', fa_type='fa-ban', alert_class='alert-secondary', error_msg=error_msg, error_title=error_title), 403
    if isinstance(e, LoginError):
        return redirect(url_for('browser.browser_login', next=request.url))
    error_msg = str(e)
    if error_msg.lower() == 'not logged in':
        return redirect(url_for('browser.browser_login'))
    tb = traceback.format_exc()
    error_title = '500 Internal Server Error'
    log_exception(500, e, tb)
    return render_template('pages/error.html', fa_type='fa-exclamation-circle', alert_class='alert-danger', tb=tb, error_msg=error_msg,
                           error_title=error_title), 500


def handle_exception(e):
    if isinstance(e, dt.util.NotFoundException):
        log_exception(404, e)
        return jsonify({'message': str(e)}), 404
    if isinstance(e, dt.util.AuthException):
        log_exception(403, e)
        return jsonify({'message': str(e)}), 403
    if isinstance(e, LoginError):
        log_exception(401, e)
        return jsonify({'message': str(e)}), 401
    tb = traceback.format_exc()
    log_exception(500, e, tb)
    return jsonify({'message': str(e), 'traceback': tb}), 500


def log_exception(status, e, tb=""):
    with open(log_file_name, 'a+') as log_file:
        log_file.write(f'\n{datetime.datetime.now().replace(microsecond=0).isoformat(" ")} [{status}]: {str(e)}\n')
        if tb:
            log_file.write(f'Traceback: \n{tb}\n')


def process_input_dict(input_dict, set_permissions=False):
    """
    Turn string values from checkboxes into booleans
    :param input_dict:
    :param set_permissions: whether or not to insert missing permissions
    :return:
    """
    # if we get a list (which is valid JSON), expand the list
    if isinstance(input_dict, list):
        return [process_input_dict(entry) for entry in input_dict]
    
    # We transform 'true' and 'false' strings (mostly from checkboxes) to True and False python boolean values.
    boolean_keys = {
        'all_can_read',
        'all_can_write',
        'group_can_read',
        'group_can_write',
        '_all_can_read',
        '_all_can_write',
        '_group_can_read',
        '_group_can_write'
    }
    # If a blank is passed from <select> for one of these, we want to set it to None
    id_keys = {
        'user_group_id',
        'primary_user_group_id',
        'sample_ids',
        'collection_ids',
        'analysis_ids',
        '_user_group_id',
        '_primary_user_group_id',
        '_sample_ids',
        '_collection_ids',
        '_analysis_ids'
    }
    new_dict = {
        key: (False if value.lower() == 'false' else True) if isinstance(value, str) and key in boolean_keys
        else (None if value == '' else value) if key in id_keys
        else value
        for key, value in input_dict.items()
    }
    if set_permissions:
        for key in boolean_keys:
            if key not in new_dict:
                new_dict[key] = False
    return new_dict


def make_valid_tag(s):
    if isinstance(s, str):
        for c in ' !"#$%&\'()*+,./:;<=>?@[\]^`{|}~':
            s = s.replace(c, '')
    return s


def make_tag_from_name(s):
    return s.lower().replace(' ', '-') if isinstance(s, str) else s
