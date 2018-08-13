import json

from flask import Flask, redirect, request, jsonify, g, session, render_template, url_for, \
    make_response, send_from_directory
from werkzeug.utils import secure_filename
import os
import shutil
from flask_cors import CORS
import datetime
import traceback
import jwt
import base64
import uuid

import data_tools.sample_creation
import data_tools as dt
from data_tools.util import DATADIR, TMPDIR
from functools import reduce
app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

BRAND = os.environ['BRAND'] if 'BRAND' in os.environ else ''
log_file_name = f'{DATADIR}/logs/omics.log'
app.permanent_session_lifetime = 86400  # sessions expire in 24h
app.config['UPLOAD_DIR'] = TMPDIR + '/uploads'
app.secret_key = os.environ['SECRET']


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.errorhandler(405)
def method_not_allowed(e):
    log_exception(405, e)
    return jsonify({'message': 'Method not allowed'}), 405


@app.errorhandler(404)
def not_found(e):
    log_exception(404, e)
    return jsonify({'message': 'Route not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    log_exception(500, e)
    return jsonify({'message': 'uncaught internal error occurred'})


# exception thrown if user is not logged in
class LoginError(Exception):
    pass


def log_exception(status, e, tb=""):
    with open(log_file_name, 'a+') as log_file:
        log_file.write(f'{datetime.datetime.now().replace(microsecond=0).isoformat(" ")} [{status}]: {str(e)}\n')
        if tb:
            log_file.write(f'Traceback: \n{tb}')


# handle any exception thrown by a datamanip function
# this is used for the restful api only
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


# get user id, if user not logged in, raise an exception. Exception handler will send 401
# should use optional token option if used to protect route with JWT (in which case there is no session)
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


def get_user_name(user_id):
    return dt.users.get_user(user_id)['name']


def get_profile_link(user_id):
    return url_for('render_user_profile', user_id=user_id)


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


USERKEYS = ['createdBy', 'owner', 'userId']
# protected keys are those used by this system (samples/collections have extensible schema)
PROTECTEDKEYS = [  # these should not be generally editable
    'id',
    'dateModified',
    'maxRowCount',
    'maxColCount',
    'allPermissions',
    'groupPermissions',
    'owner',
    'createdBy',
    'userId',
    'parser',
    'preproc',
    'userGroup'
]

app.jinja_env.globals.update(USERKEYS=USERKEYS)
app.jinja_env.globals.update(PROTECTEDKEYS=PROTECTEDKEYS)
app.jinja_env.globals.update(get_preprocessing_modules=data_tools.sample_creation.get_preprocessing_modules)
app.jinja_env.globals.update(get_parsing_modules=data_tools.sample_creation.get_parsing_modules)
app.jinja_env.globals.update(get_samples=dt.samples.get_samples)
app.jinja_env.globals.update(get_analyses=dt.analyses.get_analyses)
app.jinja_env.globals.update(get_collections=dt.collections.get_collections)
app.jinja_env.globals.update(get_user_name=get_user_name)
app.jinja_env.globals.update(datetime=datetime.datetime)
app.jinja_env.globals.update(get_item_link=get_item_link)
app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(str=str)
app.jinja_env.globals.update(get_profile_link=get_profile_link)
app.jinja_env.globals.update(is_write_permitted=dt.users.is_write_permitted)
app.jinja_env.globals.update(get_user_id=get_user_id)
app.jinja_env.globals.update(get_update_url=get_update_url)
app.jinja_env.globals.update(get_included_groups=dt.user_groups.get_included_groups)
app.jinja_env.globals.update(BRAND=BRAND)


# close database connection at omics_dashboard close
@app.teardown_appcontext
def close_connection(exception):
    log_exception(500, exception, traceback.format_exc(exception))
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


#  ROUTES FOR BROWSERS
@app.route('/')
def render_root():
    return redirect(url_for('render_dashboard'))


@app.route('/register', methods=['GET', 'POST'])
def render_registration():
    try:
        invitation = request.args.get('invitation')
        if invitation is None:
            return render_template('register.html', error='You do not have a valid registration link.\n'
                                                          'Please contact an administrator')
        if request.method == 'GET':
            return render_template('register.html', invitation=invitation)
        if request.method == 'POST':
            data = {key: value[0] for key, value in dict(request.form).items()}
            change_password = not (data['password1'] == '' and data['password2'] == '')
            valid_passwords = data['password1'] == data['password2'] if change_password else False
            if not valid_passwords:
                return render_template('register.html', invitation=invitation, error='Passwords do not match')
            new_data = {'email': data['email'], 'password': data['password1'], 'name': data['name']}
            dt.users.register_user(invitation, new_data)
            return redirect(url_for('browser_login'))
    except Exception as e:
        return render_template('register.html', error=str(e))


@app.route('/login', methods=['GET', 'POST'])
def browser_login(msg=None, error=None, next_template='render_dashboard'):
    try:
        if request.method == 'POST':
            if dt.users.validate_login(request.form['email'], request.form['password']):
                session['user'] = dt.users.get_user_by_email(request.form['email'])
                session['logged_in'] = True
                return redirect(url_for(next_template))
            error = 'Invalid email/password'
    except ValueError as e:
        return render_template('login.html', error=str(e))
    return render_template('login.html', msg=msg, error=error)


@app.route('/logout', methods=['GET'])
def browser_logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return redirect(url_for('browser_login'))


@app.route('/dashboard', methods=['GET'])
def render_dashboard():
    try:
        get_user_id()
        return render_template('dashboard.html')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/samples', methods=['GET', 'POST'])
def render_sample_list():
    try:
        get_user_id()
        data = dt.samples.get_all_sample_metadata(get_user_id())
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner', 'maxRowCount': 'Rows',
                    'maxColCount': 'Columns'}
        return render_template('list.html', type='Samples', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/samples/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = dt.samples.get_sample_metadata(get_user_id(), sample_id)
            datasets = dt.samples.list_sample_paths(user_id, sample_id)
            return render_template('collectionentry.html', type='Sample', data=data, datasets=datasets)
        if request.method == 'DELETE':
            dt.samples.delete_sample(get_user_id(), sample_id)
            return redirect(url_for('render_sample_list'))
        if request.method == 'POST':
            dt.samples.update_sample(get_user_id(), sample_id, request.form)
            data = dt.samples.get_sample_metadata(get_user_id(), sample_id)
            datasets = dt.samples.list_sample_paths(user_id, sample_id)
            return render_template('collectionentry.html', type='Sample', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/sample_groups', methods=['GET', 'POST'])
def render_sample_group_list():
    try:
        get_user_id()
        data = dt.sample_groups.get_sample_groups(get_user_id())
        print(data)
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Sample Groups', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/sample_groups/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
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
            return redirect(url_for('render_sample_group_list'))
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


@app.route('/samples/create', methods=['GET', 'POST'])
def render_upload_sample():
    try:
        if request.method == 'POST':
            user_id = get_user_id()
            files = request.files.getlist('files')
            filenames = [os.path.join(app.config['UPLOAD_DIR'], secure_filename(file. filename)) for file in files]
            [file.save(filename) for file, filename in zip(files, filenames)]
            metadata = request.form.to_dict()
            metadata['owner'] = user_id
            metadata['createdBy'] = user_id
            sample_group = dt.sample_groups.create_sample_group(user_id, metadata)
            workflow_data = dt.sample_creation.create_sample_creation_workflow(user_id, filenames, metadata)
            dt.sample_groups.update_sample_group_attachments(user_id, sample_group['id'], workflow_data['outputIds'])
            job = dt.jobserver_control.start_job(workflow_data['workflow'], workflow_data['job'], user_id)
            dt.sample_groups.update_sample_group(user_id, sample_group['id'], {'uploadWorkflowId': job['id']})
            return redirect(url_for('render_sample_group', sample_group_id=sample_group['id']))
        return render_template('createbase.html', type='Sample', endpoint='render_upload_sample')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/collections', methods=['GET', 'POST'])
def render_collection_list():
    try:
        data = dt.collections.get_all_collection_metadata(get_user_id())
        headings = {
            'id': 'ID',
            'name': 'Name',
            'description': 'Description',
            'owner': 'Owner', 'maxRowCount':
            'Rows', 'maxColCount': 'Columns'
        }
        return render_template('list.html', type='Collections', headings=headings, data=data)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/collections/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def render_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = dt.collections.get_collection_metadata(get_user_id(), collection_id)
            datasets = dt.collections.list_collection_paths(user_id, collection_id)
            return render_template('collectionentry.html', type='Collection', data=data, datasets=datasets)
        if request.method == 'DELETE':
            dt.collections.delete_collection(get_user_id(), collection_id)
            return redirect(url_for('render_sample_list'))
        if request.method == 'POST':
            dt.collections.update_collection(get_user_id(), collection_id, request.form)
            data = dt.collections.get_collection_metadata(get_user_id(), collection_id)
            datasets = dt.collections.list_collection_paths(user_id, collection_id)
            return render_template('collectionentry.html', type='Collection', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/collections/create', methods=['GET', 'POST'])
def render_create_collection():
    try:
        if request.method == 'POST':
            form_data = request.form.to_dict()
            with open('/data/logs/omics.log', 'a+') as log_file:
                log_file.write(f'form_data:\n{form_data}\n')
            sample_ids = [int(sample_id) for sample_id in request.form.getlist('sample')]
            del form_data['sample']
            sort_by = form_data['sortBy']
            del form_data['sortBy']
            data = dt.collections.create_collection(get_user_id(), sample_ids, form_data, sort_by=sort_by)
            collection_id = data['id']
            return redirect(url_for('render_collection', collection_id=collection_id))
        if request.method == 'GET':
            if request.args.get('sampleIds', ''):
                sample_ids = [int(token) for token in request.args.get('sampleIds').strip('"').split(',')]
                print(sample_ids)
                return render_template('createbase.html', type='Collection', endpoint='render_create_collection',
                                       sample_ids=sample_ids)

            return render_template('createbase.html', type='Collection', endpoint='render_create_collection')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/analyses.py', methods=['GET', 'POST'])
def render_analysis_list():
    try:
        user_id = get_user_id()
        analyses = dt.analyses.get_analyses(user_id)
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=analyses, headings=headings, type='Analyses')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/analyses.py/create', methods=['GET', 'POST'])
def render_create_analysis():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            collection_ids = [int(collection_id) for collection_id in request.form.getlist('collection')]
            analysis = dt.analyses.create_analysis(user_id, request.form.to_dict())
            for collection_id in collection_ids:
                dt.analyses.attach_collection(user_id, analysis['id'], collection_id)
            return redirect(url_for('render_analysis', analysis_id=analysis['id']))
        return render_template('createbase.html', type='Analysis', groups=dt.user_groups.get_user_groups(),
                               endpoint='render_create_analysis')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/analyses.py/<analysis_id>', methods=['GET'])
def render_analysis(analysis_id=None):
    try:
        user_id = get_user_id()
        collection_headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        collections = dt.analyses.get_attached_collections(user_id, analysis_id)
        analysis = dt.analyses.get_analysis(user_id, analysis_id)
        return render_template('entry.html', data=analysis, type='Analysis',
                               collections=collections, collection_headings=collection_headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/user_groups', methods=['GET'])
def render_user_group_list():
    try:
        get_user_id()
        user_groups = dt.user_groups.get_user_groups()
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'createdBy': 'Created By'}
        return render_template('list.html', data=user_groups, type='User Groups', headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/user_groups/<group_id>', methods=['GET', 'DELETE'])
def render_user_group(group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'DELETE':
            dt.user_groups.delete_user_group(user_id, group_id)
            return redirect(url_for('render_user_group_list'))
        user_group = dt.user_groups.get_user_group(group_id)
        del user_group['members']
        return render_template('entry.html', type='User Group', data=user_group, all_users=dt.users.get_users())
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/user_groups/create', methods=['GET', 'POST'])
def render_create_user_group():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            other_user_ids = [int(uid) for uid in request.form.getlist('user')]
            print(other_user_ids)
            user_group = dt.user_groups.create_user_group(user_id, request.form.to_dict())
            for other_user_id in other_user_ids:
                dt.user_groups.attach_user(user_id, other_user_id, user_group['id'])
            return redirect(url_for('render_user_group', group_id=user_group['id']))
        return render_template('createbase.html', type='User Group', users=dt.users.get_users(),
                               endpoint='render_create_user_group')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows', methods=['GET', 'POST'])
def render_workflow_list():
    try:
        user_id = get_user_id()
        workflows = dt.workflows.get_workflows(user_id)
        headings = {'id': 'id', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=workflows, headings=headings, type='Workflows')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def render_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        workflow = dt.workflows.get_workflow(user_id, workflow_id)
        return render_template('entry.html', type='Workflow', data=workflow)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows/create', methods=['GET', 'POST', 'DELETE'])
def render_create_workflow():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            workflow = dt.workflows.create_workflow(user_id, request.form.to_dict())
            return redirect(url_for('render_workflow', workflow_id=workflow['id']))
        return render_template('createbase.html', type='Workflow', endpoint='render_create_workflow')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows/create', methods=['GET', 'POST', 'DELETE'])
def render_workflow_modules():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/jobs', methods=['GET', 'POST'])
def render_job_list():
    try:
        data = dt.jobserver_control.get_jobs()
        headings = {'id': 'ID', 'name': 'Name', 'state': 'State', 'owner': 'Owner'}
        return render_template('list.html', data=data, headings=headings, type='Jobs')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/jobs/<job_id>', methods=['GET'])
def render_job(job_id=None):
    try:
        job = dt.jobserver_control.get_job(job_id)

        return render_template('entry.html', data=job, type="Job")
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/settings', methods=['GET', 'POST'])
def render_settings():
    try:
        if request.method == 'GET':
            return render_template('settings.html')
        if request.method == 'POST':
            data = {key: value[0] for key, value in dict(request.form).items()}
            if 'changePassword1' in data:
                change_password = not (data['changePassword1'] == ''
                                       and data['changePassword2'] == ''
                                       and data['changeEmail'] == '')
                valid_passwords = data['changePassword1'] == data['changePassword2']
                if change_password:
                    if not valid_passwords:
                        return render_template('settings.html', password_change_error='Passwords do not match')
                    new_password = data['changePassword1']
                    email = data['changeEmail']
                    other_user_id = dt.users.get_user_by_email(email)['id']
                    dt.users.update_user(get_user_id(), other_user_id, {'password': new_password})
                    msg = f'Changed password for {email}'
                    return render_template('settings.html', password_change_msg=msg)
            else:
                change_password = not (data['password1'] == '' and data['password2'] == '')
                valid_passwords = data['password1'] == data['password2'] if change_password else False
                new_data = {key: value for key, value in data.items() if key in ['email', 'name'] and not value == ''}
                valid_keys = ['name', 'email', 'password']
                if change_password:
                    if not valid_passwords:
                        return render_template('settings.html', error='passwords do not match')
                    new_data['password'] = data['password1']
                msg = '\n'.join(['Changed password' if key == 'password' else 'Changed %s to %s.' % (key, value)
                                 for key, value in new_data.items() if key in valid_keys])
                dt.users.update_user(get_user_id(), get_user_id(), new_data)
                # update session with new data
                if 'password' in new_data:
                    # invalidate session on password change
                    browser_logout()
                    return redirect(url_for('browser_login', msg=msg, next_template='render_settings'))
                session['user'] = dt.users.get_user(get_user_id())
                return render_template('settings.html', msg=msg)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/users', methods=['GET'])
def render_user_list():
    try:
        get_user_id()
        users = dt.users.get_users()
        headings = {'id': 'ID', 'name': 'Name', 'admin': 'Admin'}
        return render_template('list.html', type='Users', headings=headings, data=users)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/users/<user_id>', methods=['GET'])
def render_user_profile(user_id=None):
    try:
        get_user_id()
        user = dt.users.get_user(user_id)
        return render_template('entry.html', type='User', data=user)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/apidocs')
def render_api_docs():
    return render_template('swagger.html')

# ROUTES FOR NON-BROWSER Clients
# These routes can be authenticated using the session cookie or a JWT in the Authentication header
# login/logout used for sessions, authenticate used for JWT
# deauthenticating a JWT isn't possible. JWTs expire in 24 hours.


@app.route('/api/login', methods=['POST'])
def login():
    credentials = request.get_json(force=True)
    if dt.users.validate_login(credentials['email'], credentials['password']):
        session['user'] = dt.users.get_user_by_email(credentials['email'])
        session['logged_in'] = True
        return jsonify(session['user']), 200
    else:
        return jsonify({"message": "authentication failed"}), 403


@app.route('/api/logout')
def logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return jsonify({'message': 'logged out'}), 200


@app.route('/api/authenticate', methods=['POST'])
def jwt_authenticate():
    credentials = request.get_json(force=True)
    if dt.users.validate_login(credentials['email'], credentials['password']):
        token = dt.users.get_jwt(credentials['email'], credentials['password'])
        return jsonify({'token': str(token)}), 200
    return jsonify({"message": "authentication failed"}), 403


@app.route('/api/currentuser')
def get_current_user():
    try:
        user_id = get_user_id()
        return jsonify(dt.users.get_user(user_id)), 200
    except Exception as e:
        return handle_exception(e)


@app.route('/api/')
def send_ok():
    message = f'API works! View {url_for("render_api_docs")} in your browser to see Swagger-UI documentation.'
    print(message)
    return jsonify({'message': message}), 200


@app.route('/api/users', methods=['GET', 'POST'])
def list_users():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.users.create_user(user_id, data))
        return jsonify(dt.users.get_users())
    except Exception as e:
        return handle_exception(e)


@app.route('/api/users/<user_id>', methods=['GET', 'POST', 'DELETE'])
def edit_user(user_id=None):
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.users.get_user(user_id))
        if request.method == 'POST':
            return jsonify(dt.users.update_user(current_user_id, user_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(dt.users.delete_user(current_user_id, user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections', methods=['GET', 'POST'])
def list_collections():
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.collections.get_collections(current_user_id))
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(dt.collections.create_collection(current_user_id, data['sampleIds'], data))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def get_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.collections.get_collection(user_id, collection_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            return jsonify(dt.collections.update_collection(user_id, collection_id, new_data))
        if request.method == 'DELETE':
            return jsonify(dt.collections.delete_collection(user_id, collection_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections/download/<collection_id>', methods=['GET'])
def download_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.args.get('format', '') == 'pandas':
            out = dt.collections.download_collection_dataframe(user_id, collection_id)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        if request.args.get('path', ''):
            path = request.args.get('path', '')
            out = dt.collections.download_collection_dataset(user_id, collection_id, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        out = dt.collections.download_collection(user_id, collection_id)
        return send_from_directory('%s/collections' % DATADIR, out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections/upload/', methods=['POST'])
def upload_collection():
    #  TODO: support files encoded as base64 in application/json and actual files in multipart/form-data
    try:
        user_id = get_user_id()
        # for request from MATLAB client that doesn't support multipart/form-data
        # file is base64 encoded.
        new_data = request.get_json()
        if 'file' not in new_data and 'file' not in request.files:
            raise ValueError('No file uploaded')
        filename = os.path.join(app.config['UPLOAD_DIR'], secure_filename(str(uuid.uuid4())))
        if 'file' in request.files:
            if request.files['file'].filename == '':
                raise ValueError('No file uploaded')
            request.files['file'].save(filename)
        else:
            with open(filename, 'wb') as file:
                collection_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                file.write(collection_file_data)
                del new_data['file']
        if dt.util.validate_file(filename):
            collection_data = dt.collections.upload_collection(user_id, filename, new_data)
            return jsonify(collection_data)
        raise ValueError('invalid content type')
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples', methods=['GET'])
def list_samples():
    try:
        user_id = get_user_id()
        return jsonify(dt.samples.get_samples(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.samples.get_sample(user_id, sample_id))
        if request.method == 'POST':
            if 'file' in request.files:
                print('File upload')
                print(request.files)
                filename = os.path.join(app.config['UPLOAD_DIR'], secure_filename(str(uuid.uuid4())))
                request.files['file'].save(filename)
                sample_data = dt.samples.upload_sample(user_id, filename, request.form, sample_id)
            else:
                sample_data = dt.samples.update_sample(user_id, sample_id, request.get_json(force=True))
            return jsonify(sample_data)
        if request.method == 'DELETE':
            return jsonify(dt.samples.delete_sample(user_id, sample_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/sample_groups', methods=['GET', 'POST'])
def list_sample_groups():
    try:
        return jsonify(dt.sample_groups.get_sample_groups(get_user_id()))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/sample_groups/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample_group(sample_group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.sample_groups.get_sample_group(user_id, sample_group_id))
        if request.method == 'DELETE':
            return jsonify(dt.sample_groups.delete_sample_group(user_id, sample_group_id))
        if request.method == 'POST':
            return jsonify(dt.sample_groups.update_sample_group(user_id, sample_group_id, request.form))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/common_attributes', methods=['POST'])
def get_common_attributes():
    try:
        user_id = get_user_id()
        data = request.get_json(force=True)
        samples = [dt.samples.get_sample(user_id, sample_id) for sample_id in data['samples']]
        protected_keys = ['allPermissions', 'createdBy', 'datasets', 'description', 'groupPermissions', 
                          'groups', 'id', 'name', 'owner', 'parser', 'path', 'preproc', 'userGroup']
        common_keys = [item for item in samples[0].keys() 
                       if item not in protected_keys and all([item in sample for sample in samples])]
        return jsonify(common_keys)
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/download/<sample_id>', methods=['GET'])
def download_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.args.get('path', ''):
            path = request.args.get('path', '')
            out = dt.samples.download_sample_dataset(user_id, sample_id, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype = 'text/csv'
            return response
        out = dt.samples.download_sample(user_id, sample_id)
        return send_from_directory('%s/samples' % DATADIR, out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/create', methods=['POST'])
def parse_sample():
    try:
        user_id = get_user_id()
        filename = os.path.join(app.config['UPLOAD_DIR'], secure_filename(str(uuid.uuid4())))
        data = request.get_json(force=True)
        if 'file' in request.files:
            request.files['file'].save(filename)
        else:
            file_contents = data['file']
            del data['file']
            decoded_file_contents = base64.b64decode(file_contents)
            with open(filename, 'wb') as file:
                file.write(decoded_file_contents)
        data['owner'] = user_id
        data['createdBy'] = user_id
        workflow_data = dt.sample_creation.create_sample_creation_workflow(user_id, [filename], data)
        dt.jobserver_control.start_job(workflow_data['workflow_filename'], workflow_data['job'], user_id)
        return redirect(url_for('list_jobs'))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/upload/', methods=['POST'])
def upload_sample():
    try:
        user_id = get_user_id()
        # for request from MATLAB client that doesn't support multipart/form-data
        # file is base64 encoded.
        new_data = request.get_json()
        print('upload_sample')
        filename = os.path.join(app.config['UPLOAD_DIR'], str(uuid.uuid4()))
        print('filename set')
        if 'file' not in new_data and 'file' not in request.files:
            raise ValueError('No file uploaded')
        if 'file' in request.files:
            if request.files['file'].filename == '':
                raise ValueError('No file uploaded')
            request.files['file'].save(filename)
        else:
            with open(filename, 'wb') as file:
                sample_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                file.write(sample_file_data)
                del new_data['file']
        if dt.util.validate_file(filename):
            sample_data = dt.samples.upload_sample(user_id, filename, new_data)
            return jsonify(sample_data)
        raise ValueError('invalid content type')
    except Exception as e:
        return handle_exception(e)


@app.route('/api/analyses.py', methods=['GET', 'POST'])
def list_analyses():
    try:
        user_id = get_user_id()
        return jsonify(dt.analyses.get_analyses(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/analyses.py/attach/<analysis_id>', methods=['POST'])
def attach_collection(analysis_id=None):
    try:
        user_id = get_user_id()
        data = request.get_json()
        if 'collectionIds' in data:
            for collection_id in data['collectionIds']:
                return jsonify(dt.analyses.attach_collection(user_id, analysis_id, collection_id))
        elif 'collectionId' in data:
            return jsonify(dt.analyses.attach_collection(user_id, analysis_id, data['collectionId']))
        else:
            raise ValueError('No collection id(s) specified')
    except Exception as e:
        return handle_exception(e)


@app.route('/api/analyses.py/<analysis_id>', methods=['GET', 'POST', 'DELETE'])
def get_analysis(analysis_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            res_data = dt.analyses.get_analysis(user_id, analysis_id)
            res_data['collections'] = dt.analyses.get_attached_collections(user_id, analysis_id)
            return jsonify(res_data)
        if request.method == 'POST':
            return jsonify(dt.analyses.update_analysis(user_id, analysis_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(dt.analyses.delete_analysis(user_id, analysis_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/user_groups', methods=['GET', 'POST'])
def list_user_groups():
    try:
        get_user_id()
        if request.method == 'GET':
            return jsonify({})
        if request.method == 'POST':
            return jsonify({})
    except Exception as e:
        return handle_exception(e)


@app.route('/api/user_groups/<group_id>', methods=['GET', 'POST', 'DELETE'])
def get_user_group(group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.user_groups.get_user_group(group_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            if 'users' in new_data:
                dt.user_groups.update_user_attachments(user_id, group_id, new_data['users'])
            return jsonify(dt.user_groups.update_user_group(user_id, group_id, new_data))
        if request.method == 'DELETE':
            return jsonify(dt.user_groups.delete_user_group(user_id, group_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/workflows', methods=['GET', 'POST'])
def list_workflows():
    try:
        user_id = get_user_id()
        return jsonify(dt.workflows.get_workflows(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def get_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(dt.workflows.get_workflow(user_id, workflow_id))
        if request.method == 'POST':
            return jsonify(dt.workflows.update_workflow(user_id, workflow_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(dt.workflows.delete_workflow(user_id, workflow_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/jobs', methods=['GET', 'POST'])
def list_jobs():
    try:
        return jsonify(dt.jobserver_control.get_jobs())
    except Exception as e:
        return handle_exception(e)


@app.route('/api/jobs/<job_id>', methods=['GET', 'POST'])
def get_job(job_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            action = request.args.get('method')
            if action:
                if action == 'resume':
                    return jsonify(dt.jobserver_control.resume_job(user_id, job_id))
                if action == 'cancel':
                    return jsonify(dt.jobserver_control.cancel_job(user_id, job_id))
        return jsonify(dt.jobserver_control.get_job(job_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/invite', methods=['GET'])
def get_invitation():
    try:
        user_id = get_user_id()
        return jsonify(dt.users.create_invitation(user_id))
    except Exception as e:
        return handle_exception(e)


# this is consumed by the job server to clean up files created to facilitate workflow execution
# this uses its own authorization header separate from the JWT for user-facing routes
# this should only be used by the jobserver.
# In the docker-compose set up, the jobserver only allows connections from within the 20-bit block (172.16.0.0/12),
# usually other containers. This will have to be changed to something stricter (probably related to JWT) if the
# jobserver runs on another host outside the Docker subnet.
@app.route('/api/finalize', methods=['POST'])
def finalize_job():
    try:
        user_id = get_user_id()
        print('get request')
        body = request.get_json(force=True)
        token = body['wfToken']
        path = f'{TMPDIR}/{token}'
        print('load wfdata')
        info = json.load(open(f'{path}/wfdata.json', 'r'))
        print('Check jobserver token')
        if dt.jobserver_control.check_jobserver_token(token) and dt.users.is_write_permitted(user_id, info):
            shutil.rmtree(f'{TMPDIR}/{token}', ignore_errors=True)
        print('return')
        return jsonify({'message': f'Removed {path}'})
    except Exception as e:
        return handle_exception(e)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
