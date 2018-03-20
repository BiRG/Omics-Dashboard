from flask import Flask, redirect, request, jsonify, g, session, render_template, url_for, make_response, send_from_directory
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename
import datamanip
from passlib.hash import pbkdf2_sha256
import os
import shutil
from flask_cors import CORS
import datetime
import traceback
import jwt
import base64
import uuid
from cgi import parse_header
from flask_swagger_ui import get_swaggerui_blueprint
SWAGGER_URL = '/api/docs'
API_FILE = '/app/swagger.yml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_FILE,
    config = {'app_name': 'Omics Dashboard'}
)

app = Flask(__name__)
CORS(app)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


DATADIR = os.environ['DATADIR']
BRAND = os.environ['BRAND'] if 'BRAND' in os.environ else ''
TMPDIR = os.environ['TMPDIR'] if 'TMPDIR' in os.environ else DATADIR + '/tmp'
MODULEDIR = os.environ['MODULEDIR'] if 'MODULEDIR' in os.environ else DATADIR + '/modules'
log_file_name = f'{DATADIR}/logs/omics.log'
app.permanent_session_lifetime = 86400  # sessions expire in 24h
app.config['UPLOAD_DIR'] = TMPDIR + '/uploads'
app.secret_key = os.environ['SECRET']



@app.before_request
def make_session_permanent():
    session.permanent = True


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'message': 'Method not allowed'}), 405


@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': 'Route not found'}), 404


@app.errorhandler(500)
def internal_error(e):
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
    if e is datamanip.AuthException:
        log_exception(403, e)
        return jsonify({'message': str(e)}), 403
    if e is LoginError:
        log_exception(401, e)
        return jsonify({'message': str(e)}), 401
    log_exception(500, e)
    tb = traceback.format_exc()
    return jsonify({'message': str(e), 'traceback': tb}), 500


def handle_exception_browser(e):
    if e is datamanip.AuthException:
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
    return render_template('error.html', fa_type='fa-exclamation-circle', tb=tb, error_msg=error_msg, error_title=error_title), 500


def validate_login(email, password):
    pwhash = datamanip.get_user_password_hash(email)['password']
    if pwhash is None or not pbkdf2_sha256.verify(password, pwhash):
        raise ValueError('Invalid username/password')
    return True


# returns a str value containing JWT (we handle everything in unicode and convert request bodies to JSON)
def get_jwt(email, password):
    validate_login(email, password)
    user = datamanip.get_user_by_email(email)
    user['exp'] = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    return jwt.encode(user, os.environ['SECRET'], algorithm='HS256').decode('utf-8')


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
        except Exception as e:
            raise LoginError('not authenticated')
    raise LoginError('Not logged in')


def get_user_name(user_id):
    return datamanip.get_user(user_id)['name']


def get_profile_link(user_id):
    return url_for('render_user_profile', user_id=user_id)


def get_item_link(record_type, item):
    if record_type.lower() == 'collections' or record_type.lower() == 'collection':
        return url_for('render_collection', collection_id=item['id'])
    elif record_type.lower() == 'samples' or record_type.lower() == 'sample':
        return url_for('render_sample', sample_id=item['id'])
    elif record_type.lower() == 'users' or record_type.lower() == 'user':
        return url_for('render_user_profile', user_id=item['id'])
    elif record_type.lower() == 'user group' or record_type.lower() == 'user groups':
        return url_for('render_user_group',group_id=item['id'])
    elif record_type.lower() == 'analyses' or record_type.lower() == 'analysis':
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
    elif record_type.lower() == 'analyses' or record_type.lower() == 'analysis':
        return url_for('get_analysis', analysis_id=item['id'])
    elif record_type.lower() == 'workflow' or record_type.lower() == 'workflows':
        return url_for('get_workflow', workflow_id=item['id'])
    elif record_type.lower() == 'job' or record_type.lower() == 'jobs':
        return url_for('render_job', job_id=item['id'])
    elif record_type.lower() == 'user group' or record_type.lower() == 'user groups':
        return url_for('get_user_group', group_id=item['id'])
    return '#'


USERKEYS = ['createdBy', 'owner', 'userId']
app.jinja_env.globals.update(USERKEYS=USERKEYS)
app.jinja_env.globals.update(get_preprocessing_modules=datamanip.get_preprocessing_modules)
app.jinja_env.globals.update(get_parsing_modules=datamanip.get_parsing_modules)
app.jinja_env.globals.update(get_samples=datamanip.get_samples)
app.jinja_env.globals.update(get_analyses=datamanip.get_analyses)
app.jinja_env.globals.update(get_collections=datamanip.get_collections)
app.jinja_env.globals.update(get_user_name=get_user_name)
app.jinja_env.globals.update(datetime=datetime.datetime)
app.jinja_env.globals.update(get_item_link=get_item_link)
app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(str=str)
app.jinja_env.globals.update(get_profile_link=get_profile_link)
app.jinja_env.globals.update(is_write_permitted=datamanip.is_write_permitted)
app.jinja_env.globals.update(get_user_id=get_user_id)
app.jinja_env.globals.update(get_update_url=get_update_url)
app.jinja_env.globals.update(get_included_groups=datamanip.get_included_groups)
app.jinja_env.globals.update(BRAND=BRAND)

# close db connection at app close
@app.teardown_appcontext
def close_connection(exception):
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
            datamanip.register_user(invitation, new_data)
            return redirect(url_for('browser_login'))
    except Exception as e:
        return render_template('register.html', error=str(e))


@app.route('/login', methods=['GET', 'POST'])
def browser_login(msg=None, error=None, next_template='render_dashboard'):
    try:
        if request.method == 'POST':
            if validate_login(request.form['email'], request.form['password']):
                session['user'] = datamanip.get_user_by_email(request.form['email'])
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
        data = datamanip.get_all_sample_metadata(get_user_id())
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Samples', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/samples/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = datamanip.get_sample_metadata(get_user_id(), sample_id)
            datasets = datamanip.list_sample_paths(user_id, sample_id)
            return render_template('collectionentry.html', type='Sample', data=data, datasets=datasets)
        if request.method == 'DELETE':
            datamanip.delete_collection(get_user_id(), sample_id)
            return redirect(url_for('render_sample_list'))
        if request.method == 'POST':
            datamanip.update_sample(get_user_id(), sample_id, request.form)
            data = datamanip.get_sample_metadata(get_user_id(), sample_id)
            datasets = datamanip.list_sample_paths(user_id, sample_id)
            return render_template('collectionentry.html', type='Sample', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/samples/create', methods=['GET', 'POST'])
def render_upload_sample():
    try:
        if request.method == 'POST':
            user_id = get_user_id()
            files = request.files.getlist('files')
            filenames = [os.path.join(app.config['UPLOAD_DIR'], secure_filename(file.filename)) for file in files]
            [file.save(filename) for file, filename in zip(files, filenames)]
            metadata = request.form.to_dict()
            metadata['owner'] = user_id
            metadata['createdBy'] = user_id
            workflow_data = datamanip.create_sample_creation_workflow(filenames, metadata)
            datamanip.start_job(workflow_data['workflow_filename'], workflow_data['job'], workflow_data['token'],
                                data_type='sample', owner=user_id)
            return redirect(url_for('render_job_list'))
        return render_template('createbase.html', type='Sample', endpoint='render_upload_sample')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/collections', methods=['GET', 'POST'])
def render_collection_list():
    try:
        data = datamanip.get_all_collection_metadata(get_user_id())
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Collections', headings=headings, data=data)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/collections/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def render_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = datamanip.get_collection_metadata(get_user_id(), collection_id)
            datasets = datamanip.list_collection_paths(user_id, collection_id)
            return render_template('collectionentry.html', type='Collection', data=data, datasets=datasets)
        if request.method == 'DELETE':
            datamanip.delete_collection(get_user_id(), collection_id)
            return redirect(url_for('render_sample_list'))
        if request.method == 'POST':
            datamanip.update_collection(get_user_id(), collection_id, request.form)
            data = datamanip.get_collection_metadata(get_user_id(), collection_id)
            datasets = datamanip.list_collection_paths(user_id, collection_id)
            return render_template('collectionentry.html', type='Collection', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/collections/create', methods=['GET', 'POST'])
def render_create_collection():
    try:
        if request.method == 'POST':
            #print('get form data:\n')
            form_data = request.form.to_dict()
            with open('/data/logs/omics.log', 'a+') as log_file:
                log_file.write(f'form_data:\n{form_data}\n')
            sample_ids = [int(sample_id) for sample_id in request.form.getlist('sample')]
            del form_data['sample']
            sort_by = form_data['sortBy']
            del form_data['sortBy']
            data = datamanip.create_collection(get_user_id(), sample_ids, form_data)
            collection_id = data['id']
            return redirect(url_for('render_collection', collection_id=collection_id))
        return render_template('createbase.html', type='Collection', endpoint='render_create_collection')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/analyses', methods=['GET', 'POST'])
def render_analysis_list():
    try:
        user_id = get_user_id()
        analyses = datamanip.get_analyses(user_id)
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=analyses, headings=headings, type='Analyses')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/analyses/create', methods=['GET', 'POST'])
def render_create_analysis():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            collection_ids = [int(collection_id) for collection_id in request.form.getlist('collection')]
            analysis = datamanip.create_analysis(user_id, request.form.to_dict())
            for collection_id in collection_ids:
                datamanip.attach_collection(user_id, analysis['id'], collection_id)
            return redirect(url_for('render_analysis', analysis_id=analysis['id']))
        return render_template('createbase.html', type='Analysis', groups=datamanip.get_user_groups(), endpoint='render_create_analysis')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/analyses/<analysis_id>', methods=['GET'])
def render_analysis(analysis_id=None):
    try:
        user_id = get_user_id()
        collection_headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        collections = datamanip.get_attached_collections(user_id, analysis_id)
        analysis = datamanip.get_analysis(user_id, analysis_id)
        return render_template('entry.html', data=analysis, type='Analysis',
                               collections=collections, collection_headings=collection_headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/usergroups', methods=['GET'])
def render_user_group_list():
    try:
        user_id = get_user_id()
        user_groups = datamanip.get_user_groups()
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'createdBy': 'Created By'}
        return render_template('list.html', data=user_groups, type='User Groups', headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/usergroups/<group_id>', methods=['GET', 'DELETE'])
def render_user_group(group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'DELETE':
            datamanip.delete_user_group(user_id, group_id)
            return redirect(url_for('render_user_group_list'))
        user_group = datamanip.get_user_group(group_id)
        del user_group['members']
        return render_template('entry.html', type='User Group', data=user_group, all_users=datamanip.get_users())
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/usergroups/create', methods=['GET', 'POST'])
def render_create_user_group():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            other_user_ids = [int(uid) for uid in request.form.getlist('user')]
            print(other_user_ids)
            user_group = datamanip.create_user_group(user_id, request.form.to_dict())
            for other_user_id in other_user_ids:
                datamanip.attach_user(user_id, other_user_id, user_group['id'])
            return redirect(url_for('render_user_group', group_id=user_group['id']))
        return render_template('createbase.html', type='User Group', users=datamanip.get_users(), endpoint='render_create_user_group')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows', methods=['GET', 'POST'])
def render_workflow_list():
    try:
        user_id = get_user_id()
        workflows = datamanip.get_workflows(user_id)
        headings = {'id': 'id', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=workflows, headings=headings, type='Workflows')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def render_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        workflow = datamanip.get_workflow(user_id, workflow_id)
        return render_template('entry.html', type='Workflow', data=workflow)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/workflows/create', methods=['GET', 'POST', 'DELETE'])
def render_create_workflow():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            workflow = datamanip.create_workflow(user_id, request.form.to_dict())
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
        #print('datamanip.get_jobs()')
        data = datamanip.get_jobs()
        #print(f'data:\n{data}\n')
        headings = {'id': 'ID', 'name': 'Name', 'state': 'State', 'owner': 'Owner'}
        #headings = {'id': 'ID', 'workflow': 'Workflow', 'status': 'Status', 'options': 'Options'}
        #print('render_template')
        return render_template('list.html', data=data, headings=headings, type='Jobs')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/jobs/<job_id>', methods=['GET'])
def render_job(job_id=None):
    try:
        job = datamanip.get_job(job_id)

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
            datamanip.update_user(get_user_id(), get_user_id(), new_data)
            # update session with new data
            if 'password' in new_data:
                # invalidate session on password change
                browser_logout()
                return redirect(url_for('browser_login', msg=msg, next_template='render_settings'))
            session['user'] = datamanip.get_user(get_user_id())
            return render_template('settings.html', msg=msg)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/users', methods=['GET'])
def render_user_list():
    try:
        get_user_id()
        users = datamanip.get_users()
        headings = {'id': 'ID', 'name': 'Name', 'admin': 'Admin'}
        return render_template('list.html', type='Users', headings=headings, data=users)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/users/<user_id>', methods=['GET'])
def render_user_profile(user_id=None):
    try:
        get_user_id()
        user = datamanip.get_user(user_id)
        return render_template('entry.html', type='User', data=user)
    except Exception as e:
        return handle_exception_browser(e)



# ROUTES FOR NON-BROWSER Clients
# These routes can be authenticated using the session cookie or a JWT in the Authentication header
# login/logout used for sessions, authenticate used for JWT
# deauthenticating a JWT isn't possible. JWTs expire in 24 hours.

@app.route('/api/login', methods=['POST'])
def login():
    credentials = request.get_json(force=True)
    if validate_login(credentials['email'], credentials['password']):
        session['user'] = datamanip.get_user_by_email(credentials['email'])
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
    if validate_login(credentials['email'], credentials['password']):
        token = get_jwt(credentials['email'], credentials['password'])
        return jsonify({'token': str(token)}), 200
    return jsonify({"message": "authentication failed"}), 403


@app.route('/api/currentuser')
def get_current_user():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.get_user(user_id)), 200
    except Exception as e:
        return handle_exception(e)


@app.route('/api/')
def send_ok():
    return jsonify({'message': 'API works! See documentation.'}), 200


@app.route('/api/users', methods=['GET', 'POST'])
def list_users():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(datamanip.create_user(user_id, data))
        return jsonify(datamanip.get_users())
    except Exception as e:
        return handle_exception(e)


@app.route('/api/users/<user_id>', methods=['GET', 'POST', 'DELETE'])
def edit_user(user_id=None):
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_user(user_id))
        if request.method == 'POST':
            return jsonify(datamanip.update_user(current_user_id, user_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_user(current_user_id, user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections', methods=['GET', 'POST'])
def list_collections():
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_collections(current_user_id))
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(datamanip.create_collection(current_user_id, data['sampleIds'], data))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def get_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_collection(user_id, collection_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            return jsonify(datamanip.update_collection(user_id, collection_id, new_data))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_collection(user_id, collection_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections/download/<collection_id>', methods=['GET'])
def download_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.args.get('path', ''):
            path = request.args.get('path', '')
            out = datamanip.download_collection_dataset(user_id, collection_id, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype='text/csv'
            return response
        out = datamanip.download_collection(user_id, collection_id)
        return send_from_directory('%s/collections' % DATADIR, out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@app.route('/api/collections/upload/', methods=['POST'])
def upload_collection():
    with open('/data/debuglog', 'w') as logfile:
        try:
            content_type = parse_header(request.headers.get('Content-Type'))[0]
            user_id = get_user_id()
            if content_type == 'multipart/form-data':
                new_data = dict(request.form)
                # with multipart/form-data, everything is a list for some reason
                # we can't use lists of unicode strings as attributes in hdf5
                # our preferred schema doesn't allow for non-scalar attributes anyway
                new_data = {key: value[0] if type(value) is list else value for key, value in new_data.items()}
                if 'file' not in request.files:
                    raise ValueError('No file uploaded')
                collection_file = request.files['file']
                if collection_file.filename == '':
                    raise ValueError('No file uploaded')
                if collection_file:
                    filename = os.path.join(app.config['UPLOAD_DIR'], secure_filename(collection_file.filename))
                    collection_file.save(filename)
                    if datamanip.validate_file(filename):
                        collection_data = datamanip.upload_collection(user_id, filename, new_data)
                        return jsonify(collection_data)
                raise ValueError('uploaded file not valid')
            elif content_type == 'application/json':
                # for request from MATLAB client that doesn't support multipart/form-data
                # file is base64 encoded.
                new_data = request.get_json()
                if 'file' not in new_data:
                    raise ValueError('No file uploaded')
                collection_file_data = base64.b64decode(bytes(new_data['file'], 'utf-8'))
                del new_data['file']
                filename = os.path.join(app.config['UPLOAD_DIR'], str(uuid.uuid4()))
                with open(filename, 'wb') as file:
                    file.write(collection_file_data)
                if datamanip.validate_file(filename):
                    logfile.write('file validated\n')
                    collection_data = datamanip.upload_collection(user_id, filename, new_data)
                    logfile.write('return jsonify\n')
                    return jsonify(collection_data)
                logfile.write(f'file invalid')
            logfile.write(f'wrong content type: {content_type}\n')
            raise ValueError('invalid content type')
        except Exception as e:
            return handle_exception(e)


@app.route('/api/samples', methods=['GET'])
def list_samples():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.get_samples(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_sample(user_id, sample_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            return jsonify(datamanip.update_sample(user_id, sample_id, new_data))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_sample(user_id, sample_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/common_attributes', methods=['POST'])
def get_common_attributes():
    try:
        user_id = get_user_id()
        data = request.get_json(force=True)
        samples = [datamanip.get_sample(user_id, sample_id) for sample_id in data['samples']]
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
            out = datamanip.download_sample_dataset(user_id, sample_id, path)
            response = make_response(out['csv'])
            response.headers['Content-Disposition'] = out['cd']
            response.mimetype='text/csv'
            return response
        out = datamanip.download_sample(user_id, sample_id)
        return send_from_directory('%s/samples' % DATADIR, out['filename'], as_attachment=True)
    except Exception as e:
        return handle_exception(e)


@app.route('/api/samples/upload/', methods=['POST'])
def upload_sample():
    try:
        # this one involves invoking a file parser module
        user_id = get_user_id()
        new_data = request.get_json()
    except Exception as e:
        return handle_exception(e)


@app.route('/api/analyses', methods=['GET', 'POST'])
def list_analyses():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.get_analyses(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/analyses/attach/<analysis_id>', methods=['POST'])
def attach_collection(analysis_id=None):
    try:
        user_id = get_user_id()
        data = request.get_json()
        if 'collectionIds' in data:
            for collection_id in data['collectionIds']:
                res_data = datamanip.attach_collection(user_id, analysis_id, collection_id)
        elif 'collectionId' in data:
            res_data = datamanip.attach_collection(user_id, analysis_id, data['collectionId'])
        else:
            raise ValueError('No collection id(s) specified')
        return jsonify(res_data)
    except Exception as e:
        return handle_exception(e)

@app.route('/api/analyses/<analysis_id>', methods=['GET', 'POST', 'DELETE'])
def get_analysis(analysis_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            res_data = datamanip.get_analysis(user_id, analysis_id)
            res_data['collections'] = datamanip.get_attached_collections(user_id, analysis_id)
        if request.method == 'POST':
            res_data = datamanip.update_analysis(user_id, analysis_id, request.get_json(force=True))    
        if request.method == 'DELETE':
            res_data = datamanip.delete_analysis(user_id, analysis_id)
        return jsonify(res_data)
    except Exception as e:
        return handle_exception(e)


@app.route('/api/usergroups', methods=['GET', 'POST'])
def list_user_groups():
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify({})
        if request.method == 'POST':
            return jsonify({})
    except Exception as e:
        return handle_exception(e)


@app.route('/api/usergroups/<group_id>', methods=['GET', 'POST', 'DELETE'])
def get_user_group(group_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_user_group(group_id))
        if request.method == 'POST':
            new_data = request.get_json(force=True)
            if 'users' in new_data:
                datamanip.update_user_attachments(user_id, group_id, new_data['users'])
            return jsonify(datamanip.update_user_group(user_id, group_id, new_data))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_user_group(user_id, group_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/workflows', methods=['GET', 'POST'])
def list_workflows():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.get_analyses(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def get_workflow(workflow_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify({})
        if request.method == 'POST':
            return jsonify({})
        if request.method == 'DELETE':
            return jsonify({})
    except Exception as e:
        return handle_exception(e)


@app.route('/api/jobs', methods=['GET', 'POST'])
def list_jobs():
    try:
        user_id = get_user_id()
        return jsonify({})
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
                    return jsonify(datamanip.resume_job(user_id, job_id))
                if action == 'pause':
                    return jsonify(datamanip.pause_job(user_id, job_id))
                if action == 'cancel':
                    return jsonify(datamanip.cancel_job(user_id, job_id))
        return jsonify(datamanip.get_job(job_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/api/invite', methods=['GET'])
def get_invitation():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.create_invitation(user_id))
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
        data_type = request.args['data_type']
        if data_type.lower() not in ['collection', 'sample']:
            raise ValueError('invalid data_type')

        destdir = f'{DATADIR}/{data_type.lower()}s'
        token = request.headers['Authorization']
        body = request.get_json()
        if datamanip.check_jobserver_token(token):
            outfiles = [output_file['path'] for output_file in body['output']['outputFiles']]
            next_id = datamanip.get_next_id(destdir)
            collection_ids = [i for i in range(next_id, next_id + len(outfiles))]
            collections = [f'{destdir}/{collection_id}.h5' for collection_id in collection_ids]
            [os.rename(outfile, collection) for outfile, collection in zip(outfiles, collections)]
            # delete directory containing temp files (using key in auth header)
            shutil.rmtree(f'{DATADIR}/tmp/{token}', ignore_errors=True)
        return jsonify({'paths': collections})
    except Exception as e:
        return handle_exception(e)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
