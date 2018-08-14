import os
import traceback

import jwt
from flask import url_for, session, request, render_template, redirect, jsonify

import data_tools as dt
from data_tools.util import LoginError, DATADIR
log_file_name = f'{DATADIR}/logs/omics.log'


def get_item_link(record_type, item):
    if record_type.lower() == 'collections' or record_type.lower() == 'collection':
        return url_for('render_collection', collection_id=item['id'])
    elif record_type.lower() == 'samples' or record_type.lower() == 'sample':
        return url_for('render_sample', sample_id=item['id'])
    elif record_type.lower() == 'sample groups' or record_type.lower() == 'sample group':
        return url_for('render_sample_group', sample_group_id=item['id'])
    elif record_type.lower() == 'users' or record_type.lower() == 'user':
        return url_for('render_user_profile', user_id=item['id'])
    elif record_type.lower() == 'user group' or record_type.lower() == 'user groups':
        return url_for('render_user_group', group_id=item['id'])
    elif record_type.lower() == 'analyses.py' or record_type.lower() == 'analysis':
        return url_for('render_analysis', analysis_id=item['id'])
    elif record_type.lower() == 'workflow' or record_type.lower() == 'workflows':
        return url_for('render_workflow', workflow_id=item['id'])
    elif record_type.lower() == 'job' or record_type.lower() == 'jobs':
        return url_for('render_job', job_id=item['id'])
    return '#'


def get_update_url(record_type, item):
    if record_type.lower() == 'collections' or record_type.lower() == 'collection':
        return url_for('get_collection', collection_id=item['id'])
    elif record_type.lower() == 'samples' or record_type.lower() == 'sample':
        return url_for('get_sample', sample_id=item['id'])
    elif record_type.lower() == 'sample groups' or record_type.lower() == 'sample group':
        return url_for('get_sample_group', sample_group_id=item['id'])
    elif record_type.lower() == 'analyses.py' or record_type.lower() == 'analysis':
        return url_for('get_analysis', analysis_id=item['id'])
    elif record_type.lower() == 'workflow' or record_type.lower() == 'workflows':
        return url_for('get_workflow', workflow_id=item['id'])
    elif record_type.lower() == 'job' or record_type.lower() == 'jobs':
        return url_for('render_job', job_id=item['id'])
    elif record_type.lower() == 'user group' or record_type.lower() == 'user groups':
        return url_for('get_user_group', group_id=item['id'])
    return '#'


def get_profile_link(user_id):
    return url_for('render_user_profile', user_id=user_id)


def get_user_id():
    if session.get('logged_in'):
        return session['user']['id']
    # check for authorization header
    if 'Authorization' in request.headers:
        auth_header = request.headers.get('Authorization')
        # Header should be in format "JWT <>" or "Bearer <>"
        try:
            token = auth_header.split(' ')[1]
            # if this is invalid, jwt.decode will throw. So no need to check password
            user = jwt.decode(token, os.environ['SECRET'], algorithms=['HS256'])
            if user is not None:
                return user['id']
        except:
            raise LoginError('not authenticated')
    raise LoginError('Not logged in')


def handle_exception_browser(e):
    if e is dt.util.AuthException:
        log_exception(403, e)
        error_msg = str(e)
        error_title = "403 Forbidden"
        return render_template('error.html', fa_type='fa-ban', error_msg=error_msg, error_title=error_title), 403
    if e is LoginError:
        return redirect(url_for('browser_login'))
    error_msg = str(e)
    if error_msg.lower() == 'not logged in':
        return redirect(url_for('browser_login'))
    tb = traceback.format_exc()
    error_title = '500 Internal Server Error'
    log_exception(500, e, tb)
    return render_template('error.html', fa_type='fa-exclamation-circle', tb=tb, error_msg=error_msg,
                           error_title=error_title), 500


def handle_exception(e):
    if e is dt.util.AuthException:
        log_exception(403, e)
        return jsonify({'message': str(e)}), 403
    if e is LoginError:
        log_exception(401, e)
        return jsonify({'message': str(e)}), 401
    log_exception(500, e)
    tb = traceback.format_exc()
    return jsonify({'message': str(e), 'traceback': tb}), 500


def log_exception(status, e, tb=""):
    with open(log_file_name, 'a+') as log_file:
        log_file.write(f'{datetime.datetime.now().replace(microsecond=0).isoformat(" ")} [{status}]: {str(e)}\n')
        if tb:
            log_file.write(f'Traceback: \n{tb}')