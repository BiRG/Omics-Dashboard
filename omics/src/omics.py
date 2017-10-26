from flask import Flask, redirect, request, jsonify, g, send_file, session, render_template, url_for, make_response, send_from_directory
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
import datamanip
from passlib.hash import pbkdf2_sha256
import os
from flask_cors import CORS
from datetime import datetime


app = Flask(__name__)
CORS(app)
Bootstrap(app)


DATADIR = '/home/dan/omics_analysis/data'
TMPDIR = DATADIR + '/tmp'
app.permanent_session_lifetime = 86400  # sessions expire in 24h
app.config['UPLOAD_DIR'] = TMPDIR
app.secret_key = 'VERY SECRET!'  # process from environment variable


@app.before_request
def make_session_permanent():
    session.permanent=True


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


# handle any exception thrown by a datamanip function
# this is used for the restful api only
def handle_exception(e):
    if e is datamanip.AuthException:
        return jsonify({'message': str(e)}), 403
    if e is LoginError:
        return jsonify({'message': str(e)}), 401
    return jsonify({'message': str(e)}), 500


def handle_exception_browser(e):
    if e is datamanip.AuthException:
        error_msg = str(e)
        error_title = "403 Forbidden"
        return render_template('error.html', glyphicon_type='glyphicon-ban-circle', error_msg=error_msg, error_title=error_title), 403
    if e is LoginError:
        return redirect(url_for('browser_login'))
    error_msg = str(e)
    if error_msg.lower() == 'not logged in':
        return redirect(url_for('browser_login'))
    error_title = '500 Internal Server Error'
    return render_template('error.html', glyphicon_type='glyphicon-alert', error_msg=error_msg, error_title=error_title), 500


def validate_login(email, password):
    pwhash = datamanip.get_user_password_hash(email)['password']
    if pwhash is None or not pbkdf2_sha256.verify(password, pwhash):
        raise ValueError('Invalid username/password')
    return True


# get user id, if user not logged in, raise an exception. Exception handler will send 401
def get_user_id():
    if session.get('logged_in'):
        return session['user']['rowid']
    raise LoginError('Not logged in')


def get_user_name(user_id):
    return datamanip.get_user(user_id)['name']


def get_item_link(record_type, item):
    if record_type.lower() == 'collections' or record_type.lower() == 'collection':
        return url_for('render_collection', collection_id=item['id'])
    elif record_type.lower() == 'samples' or record_type.lower() == 'sample':
        return url_for('render_sample', sample_id=item['id'])
    elif record_type.lower() == 'users' or record_type.lower() == 'user':
        return url_for('render_user_profile', user_id=item['rowid'])
    elif record_type.lower() == 'analyses' or record_type.lower() == 'analysis':
        return url_for('render_analysis', analysis_id=item['rowid'])
    elif record_type.lower() == 'workflow' or record_type.lower() == 'workflows':
        return url_for('render_workflow', workflow_id=item['rowid'])
    elif record_type.lower() == 'job' or record_type.lower() == 'jobs':
        return url_for('render_job', job_id=item['rowid'])
    return '#'

USERKEYS = ['createdBy', 'owner', 'userId']

app.jinja_env.globals.update(USERKEYS=USERKEYS)
app.jinja_env.globals.update(get_user_name=get_user_name)
app.jinja_env.globals.update(datetime=datetime)
app.jinja_env.globals.update(get_item_link=get_item_link)
app.jinja_env.globals.update(int=int)


# close db connection at app close
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


#  ROUTES FOR BROWSERS
@app.route('/omics/')
def render_root():
    return redirect(url_for('render_dashboard'))


@app.route('/omics/register', methods=['GET', 'POST'])
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


@app.route('/omics/login', methods=['GET', 'POST'])
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


@app.route('/omics/logout', methods=['GET'])
def browser_logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return redirect(url_for('browser_login'))


@app.route('/omics/dashboard', methods=['GET'])
def render_dashboard():
    try:
        get_user_id()
        return render_template('dashboard.html')
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/samples', methods=['GET', 'POST'])
def render_sample_list():
    try:
        get_user_id()
        data = datamanip.get_all_sample_metadata(get_user_id())
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Sample', data=data, headings=headings)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/samples/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = datamanip.get_sample_metadata(get_user_id(), sample_id)
            datasets = datamanip.list_sample_paths(user_id, sample_id)
            return render_template('entry.html', type='Sample', data=data, datasets=datasets)
        if request.method == 'DELETE':
            datamanip.delete_collection(get_user_id(), sample_id)
            return redirect(url_for('render_sample_list'))
        if request.method == 'POST':
            datamanip.update_sample(get_user_id(), sample_id, request.form)
            data = datamanip.get_sample_metadata(get_user_id(), sample_id)
            datasets = datamanip.list_sample_paths(user_id, sample_id)
            return render_template('entry.html', type='Sample', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/samples/create')
def render_upload_sample():
    try:
        return jsonify({'not': 'implemented'})
    except Exception as e:
        handle_exception_browser(e)


@app.route('/omics/collections', methods=['GET', 'POST'])
def render_collection_list():
    try:
        data = datamanip.get_all_collection_metadata(get_user_id())
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', type='Collections', headings=headings, data=data)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/collections/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def render_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            data = datamanip.get_collection_metadata(get_user_id(), collection_id)
            datasets = datamanip.list_collection_paths(user_id, collection_id)
            return render_template('entry.html', type='Collection', data=data, datasets=datasets)
        if request.method == 'DELETE':
            datamanip.delete_collection(get_user_id(), collection_id)
            return redirect(url_for('render_sample_list'))
        if request.method == 'POST':
            datamanip.update_collection(get_user_id(), collection_id, request.form)
            data = datamanip.get_collection_metadata(get_user_id(), collection_id)
            datasets = datamanip.list_collection_paths(user_id, collection_id)
            return render_template('entry.html', type='Collection', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/collections/create', methods=['GET', 'POST'])
def render_create_collection():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/analyses', methods=['GET', 'POST'])
def render_analysis_list():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/analyses/create', methods=['GET', 'POST'])
def render_create_analysis():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/analyses/<analysis_id>', methods=['GET', 'POST', 'DELETE'])
def render_analysis(analysis_id=None):
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/workflows', methods=['GET', 'POST'])
def render_workflow_list():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/workflows/<workflow_id>', methods=['GET', 'POST', 'DELETE'])
def render_workflow(workflow_id=None):
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/workflows/create', methods=['GET', 'POST', 'DELETE'])
def render_create_workflow():
    try:
        return jsonify({'not': 'implemented'}), 501
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/settings', methods=['GET', 'POST'])
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


@app.route('/omics/users', methods=['GET'])
def render_user_list():
    try:
        get_user_id()
        users = datamanip.get_users()
        headings = {'rowid': 'ID', 'name': 'Name', 'admin': 'Admin'}
        return render_template('list.html', type='Users', headings=headings, data=users)
    except Exception as e:
        return handle_exception_browser(e)


@app.route('/omics/users/<user_id>', methods=['GET'])
def render_user_profile(user_id=None):
    try:
        get_user_id()
        user = datamanip.get_user(user_id)
        return render_template('entry.html', type='User', data=user)
    except Exception as e:
        return handle_exception_browser(e)


#  ROUTES FOR NON-BROWSER Clients
@app.route('/omics/api/login', methods=['POST'])
def login():
    credentials = request.get_json()
    if validate_login(credentials['email'], credentials['password']):
        session['user'] = datamanip.get_user_by_email(credentials['email'])
        session['logged_in'] = True
        return jsonify(session['user']), 200
    else:
        return jsonify({"message": "authentication failed"}), 403


@app.route('/omics/api/logout')
def logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return jsonify({'message': 'logged out'}), 200


@app.route('/omics/api/currentuser')
def get_current_user():
    if session.get('logged_in'):
        return jsonify(session['user']), 200
    return jsonify({'message': 'not logged in'}), 404


@app.route('/omics/api/')
def send_ok():
    return jsonify({'message': 'API works!'}), 200


@app.route('/omics/api/users', methods=['GET', 'POST'])
def list_users():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            data = request.get_json(force=True)
            return jsonify(datamanip.create_user(user_id, data))
        return jsonify(datamanip.get_users())
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/users/<user_id>', methods=['GET', 'POST', 'DELETE'])
def edit_user(user_id=None):
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_user(user_id))
        if request.method == 'POST':
            return jsonify(datamanip.update_user(current_user_id, user_id, request.json))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_user(current_user_id, user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/collections', methods=['GET', 'POST'])
def list_collections():
    try:
        current_user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_collections(current_user_id))
        if request.method == 'POST':
            data = request.get_json()
            return jsonify(datamanip.create_collection(current_user_id, data['sampleIds'], data))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/collections/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def get_collection(collection_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_collection(user_id, collection_id))
        if request.method == 'POST':
            new_data = request.get_json()
            return jsonify(datamanip.update_collection(user_id, collection_id, new_data))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_collection(user_id, collection_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/collections/download/<collection_id>', methods=['GET'])
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


@app.route('/omics/api/collections/upload/', methods=['POST'])
def upload_collection():
    try:
        user_id = get_user_id()
        new_data = request.get_json()
        if 'file' not in request.files:
            raise ValueError('No file uploaded')
        collection_file = request.files['file']
        if collection_file.filename == '':
            raise ValueError('No file uploaded')
        if collection_file:
            filename = secure_filename(collection_file.filename)
            collection_file.save(os.path.join(app.config['UPLOAD_DIR'], filename))
            if datamanip.validate_file(filename):
                return jsonify(datamanip.upload_collection(user_id, filename, new_data))
        raise ValueError('uploaded file not valid')
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/samples', methods=['GET'])
def list_samples():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.get_collections(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/samples/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample(sample_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_sample(user_id, sample_id))
        if request.method == 'POST':
            new_data = request.get_json()
            return jsonify(datamanip.update_sample(user_id, sample_id, new_data))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_sample(user_id, sample_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/sample/download/<sample_id>', methods=['GET'])
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


@app.route('/omics/api/samples/upload/', methods=['POST'])
def upload_sample():
    try:
        # this one involves invoking a file parser module
        user_id = get_user_id()
        new_data = request.get_json()
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/analyses', methods=['GET', 'POST'])
def list_analyses():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.get_analyses(user_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/analyses/<analysis_id>', methods=['GET', 'POST', 'DELETE'])
def edit_analysis(analysis_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify(datamanip.get_analysis(user_id, analysis_id))
        if request.method == 'POST':
            return jsonify(datamanip.update_analysis(user_id, analysis_id, request.json))
        if request.method == 'DELETE':
            return jsonify(datamanip.delete_user(user_id, analysis_id))
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/usergroups', methods=['GET', 'POST'])
def list_usergroups():
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            return jsonify({})
        if request.method == 'POST':
            return jsonify({})
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/usergroups/<group_id>', methods=['GET', 'POST', 'DELETE'])
def edit_usergroup(group_id=None):
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


@app.route('/omics/api/invite', methods=['GET'])
def get_invitation():
    try:
        user_id = get_user_id()
        return jsonify(datamanip.create_invitation(user_id))
    except Exception as e:
        return handle_exception(e)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
