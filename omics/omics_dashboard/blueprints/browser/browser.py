from flask import request, render_template, redirect, url_for, Blueprint
from flask_login import login_user, logout_user, login_required, fresh_login_required

import data_tools as dt
from dashboards import dashboard_list
from data_tools.db_models import db
from data_tools.template_data.entry_page import DashboardPageData, SettingsPageData
from data_tools.template_data.form import RegisterFormData, LoginFormData
from data_tools.template_data.list_table import DashboardListTableData, NotificationListTableData
from data_tools.util import LoginError
from helpers import get_current_user, handle_exception_browser
from login_manager import authenticate_user

browser = Blueprint('browser', __name__)


@browser.route('/')
def render_root():
    return redirect(url_for('browser.render_home'))


@browser.route('/register', methods=['GET', 'POST'])
def render_registration():
    try:
        invitation = request.args.get('invitation')
        if invitation is None:
            return render_template('pages/login.html',
                                   page_data=RegisterFormData(),
                                   error='You do not have a valid registration link. Please contact an administrator')
        if request.method == 'GET':
            return render_template('pages/login.html', page_data=RegisterFormData(), invitation=invitation)
        if request.method == 'POST':
            data = {key: value for key, value in request.form.to_dict().items() if value}
            valid_passwords = 'password1' in data and 'password2' in data and data['password1'] == data['password2']
            if not valid_passwords:
                return render_template('pages/login.html', page_data=RegisterFormData(),
                                       invitation=invitation, error='Passwords do not match'), 500
            new_data = {'email': data['email'], 'password': data['password1'], 'name': data['name'], 'admin': False}
            dt.users.register_user(invitation, new_data)
            return redirect(url_for('browser.browser_login'))
    except Exception as e:
        return render_template('pages/login.html', page_data=RegisterFormData(), error=str(e))


@browser.route('/login', methods=['GET', 'POST'])
def browser_login(msg=None, error=None):
    try:
        if request.method == 'POST':
            redirect_url = request.args.get('next') if request.args.get('next') is not None \
                else url_for('browser.render_home')
            user = authenticate_user(request)
            login_user(user)
            return redirect(redirect_url)
    except (ValueError, LoginError) as e:
        return render_template('pages/login.html', page_data=LoginFormData(), error=str(e))
    return render_template('pages/login.html', page_data=LoginFormData(), msg=msg, error=error)


@browser.route('/logout', methods=['GET'])
@login_required
def browser_logout():
    dt.redis_config.clear_user_hash(get_current_user().id)
    logout_user()
    return redirect(url_for('browser.browser_login'))


@browser.route('/home', methods=['GET'])
@login_required
def render_home():
    try:
        current_user = get_current_user()
        page_data = DashboardPageData(current_user)
        return render_template('pages/home.html', page_data=page_data)
    except Exception as e:
        return handle_exception_browser(e)


@browser.route('/notifications')
@login_required
def render_notifications():
    current_user = get_current_user()
    notifications = [notif.mark_read() for notif in current_user.notifications]
    db.session.commit()
    return render_template('pages/list.html',
                           page_data=NotificationListTableData(get_current_user(),
                                                               [notif.mark_read()
                                                                   for notif in current_user.notifications]))


@browser.route('/settings', methods=['GET', 'POST'])
@fresh_login_required
def render_settings():
    try:
        current_user = get_current_user()
        if request.method == 'GET':
            return render_template('pages/settings.html', page_data=SettingsPageData(current_user))
        if request.method == 'POST':
            data = {key: value for key, value in request.form.to_dict().items() if value}
            if 'changePassword1' in data:
                if current_user.admin:
                    change_password = not (data['changePassword1'] == ''
                                           and data['changePassword2'] == ''
                                           and data['changeEmail'] == '')
                    valid_passwords = data['changePassword1'] == data['changePassword2']
                    if change_password:
                        if not valid_passwords:
                            return render_template('pages/settings.html', error='Passwords do not match')
                        new_password = data['changePassword1']
                        email = data['changeEmail']
                        other_user = dt.users.get_user_by_email(email)
                        dt.users.update_user(current_user, other_user, {'password': new_password})
                        msg = f'Changed password for {email}'
                        return render_template('pages/settings.html', page_data=SettingsPageData(current_user), msg=msg)
                return render_template('pages/settings.html',
                                       page_data=SettingsPageData(current_user),
                                       error='You are not an admin!')
            else:
                change_password = 'password1' in data and 'password2' in data
                valid_passwords = data['password1'] == data['password2'] if change_password else False
                new_data = {key: value for key, value in data.items() if key in {'email', 'name', 'theme'}}
                valid_keys = ['name', 'email', 'password', 'theme']
                if change_password:
                    if not valid_passwords:
                        return render_template('pages/settings.html', page_data=SettingsPageData(current_user),
                                               error='passwords do not match')
                    new_data['password'] = data['password1']
                msg = '\n'.join(['Changed password' if key == 'password' else 'Changed %s to %s.' % (key, value)
                                 for key, value in new_data.items() if key in valid_keys])
                dt.users.update_user(current_user, current_user, new_data)
                # update session with new data
                if 'password' in new_data:
                    # invalidate session on password change
                    browser_logout()
                    return redirect(url_for('browser.browser_login', msg=msg, next=url_for('browser.render_settings')))
                login_user(current_user)
                return redirect(url_for('browser.render_settings')) # redirect a fresh GET request
    except Exception as e:
        return handle_exception_browser(e)


@browser.route('/apidocs')
@login_required
def render_api_docs():
    return render_template('pages/swagger.html')


@browser.route('/help')
@login_required
def render_help():
    return render_template('pages/help.html')


@browser.route('/dashboards')
@login_required
def render_dashboard_list():
    return render_template('pages/list.html', page_data=DashboardListTableData(get_current_user(), dashboard_list))
