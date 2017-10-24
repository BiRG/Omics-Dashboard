# To Maintainer: You can make fun of me for not using SQLAlchemy!


from flask import Flask, redirect, request, jsonify, g, send_file, session, render_template, url_for
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
import datamanip
import bcrypt
import os
from flask_cors import CORS


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
def handle_exception(e):
    if e is datamanip.AuthException:
        return jsonify({'message': str(e)}), 403
    if e is LoginError:
        return jsonify({'message': str(e)}), 401
    return jsonify({'message': str(e)}), 500


def validate_login(email, password):
    data = datamanip.get_user_password_hash(email)

    if data is None:
        raise ValueError('Username does not exist')
    # the bcrypt library only works with python2 'bytes' strings
    # but SQLite3 string types are UTF-8
    if bcrypt.checkpw(bytes(password, 'utf8'), bytes(data['password'], 'utf8')):
        return True
    else:
        raise ValueError('Password incorrect')


# get user id, if user not logged in, raise an exception. Exception handler will send 401
def get_user_id():
    if session.get('logged_in'):
        return session['user']['rowid']
    raise LoginError('Not logged in')


# close db connection at app close
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


#  ROUTES FOR BROWSERS
@app.route('/omics/login', methods=['GET', 'POST'])
def browser_login():
    error = None
    if request.method == 'POST':
        print('method == POST')
        print('email: %s, password: %s' % (request.form['email'], request.form['password']))
        if validate_login(request.form['email'], request.form['password']):
            session['user'] = datamanip.get_user_by_email(request.form['email'])
            session['logged_in'] = True
            return redirect(url_for('render_dashboard'))
        error = 'Invalid email/password'
    return render_template('login.html')


@app.route('/omics/logout', methods=['GET'])
def browser_logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return redirect('/omics/login')


@app.route('/omics/dashboard', methods=['GET'])
def render_dashboard():
    if session.get('logged_in'):
        return render_template('dashboard.html')
    return redirect('/omics/login')


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
        out = datamanip.download_collection(user_id, collection_id)
        return send_file(out['path'])
    except Exception as e:
        return handle_exception(e)


@app.route('/omics/api/collections/upload/', methods=['POST'])
def upload_collection(collection_id=None):
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
        out = datamanip.download_sample(user_id, sample_id)
        return send_file(out['path'])
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)

