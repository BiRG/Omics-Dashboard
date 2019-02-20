from flask import Flask, jsonify, session
import os
from flask_cors import CORS
import datetime
import bcrypt

import data_tools.sample_creation
import data_tools as dt
from data_tools.users import get_user_name
from data_tools.util import UPLOADDIR
from data_tools.db import db, User
from data_tools.util import DATADIR

from helpers import log_exception

from blueprints.api.analyses import analyses_api
from blueprints.api.api import api
from blueprints.api.collections import collections_api
from blueprints.api.jobs import jobs_api
from blueprints.api.sample_groups import sample_groups_api
from blueprints.api.samples import samples_api
from blueprints.api.user_groups import user_groups_api
from blueprints.api.users import users_api
from blueprints.api.workflows import workflows_api

from blueprints.browser.analyses import analyses
from blueprints.browser.browser import browser
from blueprints.browser.collections import collections
from blueprints.browser.jobs import jobs
from blueprints.browser.sample_groups import sample_groups
from blueprints.browser.samples import samples
from blueprints.browser.user_groups import user_groups
from blueprints.browser.users import users
from blueprints.browser.workflows import workflows

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI'] if 'DB_URI' in os.environ else f'sqlite:///{DATADIR}/omics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
with app.app_context():
    db.init_app(app)
    db.create_all()
    if User.query.filter_by(admin=True).first() is None:
        db.session.add(User(email='admin@admin.admin', name='Addison Minh',
                            password=bcrypt.hashpw(bytes('password', 'utf-8'), bcrypt.gensalt()).decode('utf-8'),
                            admin=True,
                            active=True))
        db.session.commit()
        print('No admin user found. Created default admin user {email: "admin@admin.admin", password: "password"}')

app.register_blueprint(analyses_api)
app.register_blueprint(api)
app.register_blueprint(collections_api)
app.register_blueprint(jobs_api)
app.register_blueprint(sample_groups_api)
app.register_blueprint(samples_api)
app.register_blueprint(user_groups_api)
app.register_blueprint(users_api)
app.register_blueprint(workflows_api)

app.register_blueprint(analyses)
app.register_blueprint(browser)
app.register_blueprint(collections)
app.register_blueprint(jobs)
app.register_blueprint(sample_groups)
app.register_blueprint(samples)
app.register_blueprint(user_groups)
app.register_blueprint(users)
app.register_blueprint(workflows)


# CORS(app, supports_credentials=True)
# app.config['CORS_HEADERS'] = 'Content-Type'

app.permanent_session_lifetime = 86400  # sessions expire in 24h
app.config['UPLOAD_DIR'] = UPLOADDIR
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


# Jinja2 template globals
app.jinja_env.globals.update(USERKEYS=['createdBy', 'owner', 'userId'])
app.jinja_env.globals.update(PROTECTEDKEYS=['id', 'dateModified', 'maxRowCount', 'maxColCount', 'allPermissions',
                                            'groupPermissions', 'owner', 'createdBy', 'userId', 'parser', 'preproc',
                                            'userGroup'])
app.jinja_env.globals.update(get_preprocessing_modules=data_tools.sample_creation.get_preprocessing_modules)
app.jinja_env.globals.update(get_parsing_modules=data_tools.sample_creation.get_parsing_modules)
app.jinja_env.globals.update(get_samples=dt.samples.get_samples)
app.jinja_env.globals.update(get_analyses=dt.analyses.get_analyses)
app.jinja_env.globals.update(get_collections=dt.collections.get_collections)
app.jinja_env.globals.update(get_user_name=get_user_name)
app.jinja_env.globals.update(datetime=datetime.datetime)
app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(str=str)
app.jinja_env.globals.update(bool=bool)
app.jinja_env.globals.update(isinstance=isinstance)
app.jinja_env.globals.update(BRAND=os.environ['BRAND'] if 'BRAND' in os.environ else '')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
