import datetime
import os
import traceback

from flask import Flask, jsonify, send_from_directory, session
from flask_login import current_user, login_required
from blueprints.browser import browser_blueprints
from blueprints.api import api_blueprints
from dashboards import dashboard_list
from data_tools.db_models import db, User
from config.config import DATADIR, UPLOADDIR, REDIS_URL
from helpers import log_exception, make_valid_tag, make_tag_from_name
from login_manager import login_manager
from config.socket_config import socketio
from config.rq_config import rq


app = Flask(__name__)
app.config['RQ_REDIS_URL'] = REDIS_URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI'] if 'DB_URI' in os.environ else f'sqlite:///{DATADIR}/omics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

for blueprint in api_blueprints + browser_blueprints:
    app.register_blueprint(blueprint)

app.permanent_session_lifetime = 86400  # sessions expire in 24h
app.config['UPLOAD_DIR'] = UPLOADDIR
app.secret_key = os.environ['SECRET']


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


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


# Jinja2 template globals
app.jinja_env.globals.update(USERKEYS=['creator_id', 'owner_id', 'user_id'])
app.jinja_env.globals.update(PROTECTEDKEYS=['id', 'dateModified', 'maxRowCount', 'maxColCount', 'allPermissions',
                                            'groupPermissions', 'owner', 'createdBy', 'userId', 'parser', 'preproc',
                                            'userGroup'])
app.jinja_env.globals.update(datetime=datetime.datetime)
app.jinja_env.globals.update(current_user=current_user)
app.jinja_env.filters['make_valid_tag'] = make_valid_tag
app.jinja_env.filters['make_tag_from_name'] = make_tag_from_name
app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(str=str)
app.jinja_env.globals.update(bool=bool)
app.jinja_env.globals.update(len=len)
app.jinja_env.globals.update(isinstance=isinstance)
app.jinja_env.globals.update(BRAND=os.environ['BRAND'] if 'BRAND' in os.environ else '')
app.jinja_env.globals.update(session=session)


with app.app_context():
    login_manager.init_app(app)
    rq.init_app(app)
    socketio.init_app(app)
    db.init_app(app)

    # create DB tables if necessary
    db.create_all()
    # if this is the first time running, create default user account
    if User.query.filter_by(admin=True).first() is None:
        new_user = User(email='admin@admin.admin', name='Default Admin (!)', admin=True, active=True)
        new_user.set_password('password')
        db.session.add(new_user)
        db.session.commit()
        print('No admin user found. Created default admin user {email: "admin@admin.admin", password: "password"}')

    # initialize dashboards
    for app_type in dashboard_list:
        try:
            app_type.create_dash_app(app)
        except Exception as e:
            traceback.print_exc()

    # protect dashboard views
    for view_func in app.view_functions:
        if view_func.startswith('/dashboards'):
            app.view_functions[view_func] = login_required(app.view_functions[view_func])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
