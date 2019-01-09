from flask import request, render_template, redirect, url_for, session, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception_browser
browser = Blueprint('browser', __name__)


@browser.route('/')
def render_root():
    return redirect(url_for('browser.render_dashboard'))


@browser.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('browser.browser_login'))
    except Exception as e:
        return render_template('register.html', error=str(e))


@browser.route('/login', methods=['GET', 'POST'])
def browser_login(msg=None, error=None, next_template='browser.render_dashboard'):
    try:
        if request.method == 'POST':
            if dt.users.validate_login(request.form['email'], request.form['password']):
                session['user'] = dt.users.get_user_by_email(request.form['email']).to_dict()
                session['logged_in'] = True
                return redirect(url_for(next_template))
            error = 'Invalid email/password'
    except ValueError as e:
        return render_template('login.html', error=str(e))
    return render_template('login.html', msg=msg, error=error)


@browser.route('/logout', methods=['GET'])
def browser_logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['user'] = None
    return redirect(url_for('browser.browser_login'))


@browser.route('/dashboard', methods=['GET'])
def render_dashboard():
    try:
        get_user_id()
        return render_template('dashboard.html')
    except Exception as e:
        return handle_exception_browser(e)


@browser.route('/settings', methods=['GET', 'POST'])
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
                    return redirect(url_for('browser.browser_login', msg=msg, next_template='browser.render_settings'))
                session['user'] = dt.users.get_user(get_user_id())
                return render_template('settings.html', msg=msg)
    except Exception as e:
        return handle_exception_browser(e)


@browser.route('/apidocs')
def render_api_docs():
    return render_template('swagger.html')
