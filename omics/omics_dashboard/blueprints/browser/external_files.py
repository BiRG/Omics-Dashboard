import os
from pathlib import Path

from flask import render_template, request, redirect, url_for, Blueprint
from flask_login import login_required
from werkzeug.utils import secure_filename

import data_tools as dt
from data_tools.template_models.entry_page import ExternalFilePageData
from data_tools.template_models.form import ExternalFileCreateFormData
from data_tools.template_models.list_table import ListTableData
from config.config import UPLOADDIR, DATADIR
from helpers import get_current_user, handle_exception_browser, process_input_dict

external_files = Blueprint('external_files', __name__, url_prefix='/external_files')


@external_files.route('/', methods=['GET'])
@login_required
def render_external_file_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, dt.external_files.get_external_files(current_user),
                                                       'External File Records'))
    except Exception as e:
        return handle_exception_browser(e)


@external_files.route('/<external_file_id>', methods=['GET'])
@login_required
def render_external_file(external_file_id=None):
    try:
        current_user = get_current_user()
        return render_template('pages/external_file_entry.html',
                               page_data=ExternalFilePageData(current_user,
                                                              dt.external_files.get_external_file(current_user,
                                                                                                  external_file_id)))
    except Exception as e:
        return handle_exception_browser(e)


@external_files.route('/create', methods=['GET', 'POST'])
@login_required
def render_create_external_file():
    try:
        current_user = get_current_user()
        if request.method == 'POST':
            # following must be true:
            # 1. if "file" is empty, then "filename" is not blank and the file exists
            # 2. if "file" is not empty, then "filename" is blank or "filename" is not blank and the file does not exist
            # 1. "filename" is not blank and file exists and "file" is empty
            # 2. "filename" is not blank and file does not exist and "file" is not empty
            data = process_input_dict(request.form.to_dict(), True)

            if 'filename' in data and data['filename']:
                data['filename'] = os.path.join(DATADIR, 'external', secure_filename(data['filename']))
                if (not os.path.isfile(data['filename'])) and (not request.files.get('file')):
                    Path(data['filename']).parent.mkdir(exist_ok=True, parents=True)
                    Path(data['filename']).touch()
                if request.files.get('file') and os.path.isfile(data['filename']):
                    raise ValueError(f'File {data["filename"]} already exists!')
            else:
                if not request.files.get('file'):
                    raise ValueError(f'No file submitted and filename field left blank!')

            if request.files.get('file'):
                file = request.files.get('file')
                if 'filename' in data and not data['filename']:
                    del data['filename']
                if 'filename' in data and os.path.isfile(data['filename']):
                    raise ValueError(
                        f'File {data["filename"]} already exists! Please set a filename in the filename field.')
                filename = os.path.join(UPLOADDIR, secure_filename(file.filename))
                file.save(filename)
                external_file = dt.external_files.upload_external_file(current_user, filename, data)
            else:
                external_file = dt.external_files.create_external_file(current_user, data)
            return redirect(url_for('external_files.render_external_file', external_file_id=external_file.id))
        return render_template('pages/create.html',
                               page_data=ExternalFileCreateFormData(current_user))
    except Exception as e:
        return handle_exception_browser(e)
