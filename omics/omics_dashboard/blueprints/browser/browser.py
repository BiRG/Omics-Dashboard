from flask import request, render_template, redirect, url_for, session, Blueprint

import data_tools as dt
from data_tools.template_data.entry_page import DashboardPageData, SettingsPageData
from data_tools.template_data.form import RegisterFormData, LoginFormData
from helpers import get_user_id, get_current_user, handle_exception_browser
browser = Blueprint('browser', __name__)


@browser.route('/')
def render_root():
    return redirect(url_for('browser.render_dashboard'))


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
            print('method=POST')
            data = {key: value for key, value in request.form.to_dict if value}
            print(data)
            valid_passwords = 'password1' in data and 'password2' in data and data['password1'] == data['password2']
            if not valid_passwords:
                print('invalid passwords')
                return render_template('pages/login.html', page_data=RegisterFormData(),
                                       invitation=invitation, error='Passwords do not match')
            new_data = {'email': data['email'], 'password': data['password1'], 'name': data['name'], 'admin': False}
            print('registering user')
            dt.users.register_user(invitation, new_data)
            return redirect(url_for('browser.browser_login'))
    except Exception as e:
        return render_template('pages/login.html', page_data=RegisterFormData(), error=str(e))


@browser.route('/login', methods=['GET', 'POST'])
def browser_login(msg=None, error=None):
    try:
        if request.method == 'POST':
            redirect_url = request.args.get('redirect') if request.args.get('redirect') is not None \
                else url_for('browser.render_dashboard')
            if dt.users.validate_login(request.form['email'], request.form['password']):
                print(dt.users.get_user_by_email(request.form['email']))
                session['user'] = dt.users.get_user_by_email(request.form['email']).to_dict()
                session['logged_in'] = True
                return redirect(redirect_url)
            error = 'Invalid email/password'
    except ValueError as e:
        return render_template('pages/login.html', page_data=LoginFormData(), error=str(e))
    return render_template('pages/login.html', page_data=LoginFormData(), msg=msg, error=error)


@browser.route('/logout', methods=['GET'])
def browser_logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return redirect(url_for('browser.browser_login'))


@browser.route('/dashboard', methods=['GET'])
def render_dashboard():
    try:
        current_user = get_current_user()
        page_data = DashboardPageData(current_user)
        return render_template('pages/dashboard.html', page_data=page_data)
    except Exception as e:
        print('Dashboard exception')
        return handle_exception_browser(e)


@browser.route('/settings', methods=['GET', 'POST'])
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
                        other_user_id = dt.users.get_user_by_email(email)['id']
                        dt.users.update_user(get_user_id(), other_user_id, {'password': new_password})
                        msg = f'Changed password for {email}'
                        return render_template('pages/settings.html', page_data=SettingsPageData(current_user), msg=msg)
                return render_template('pages/settings.html',
                                       page_data=SettingsPageData(current_user),
                                       error='You are not an admin!')
            else:
                change_password = 'password1' in data and 'password2' in data
                valid_passwords = data['password1'] == data['password2'] if change_password else False
                new_data = {key: value for key, value in data.items() if key in {'email', 'name'}}
                valid_keys = ['name', 'email', 'password']
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
                    return redirect(url_for('browser.browser_login', msg=msg, redirect=url_for('browser.render_settings')))
                session['user'] = current_user.to_dict()
                return render_template('pages/settings.html', page_data=SettingsPageData(current_user), msg=msg)
    except Exception as e:
        return handle_exception_browser(e)


@browser.route('/apidocs')
def render_api_docs():
    return render_template('swagger.html')


@browser.route('/help')
def render_help():
    return render_template('pages/help.html')
