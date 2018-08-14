from flask import render_template, request, redirect, url_for, Blueprint

import data_tools as dt
from helpers import get_user_id, handle_exception_browser
analyses = Blueprint('analyses', __name__, url_prefix='/analyses')


@analyses.route('/', methods=['GET', 'POST'])
def render_analysis_list():
    try:
        user_id = get_user_id()
        analysis_list = dt.analyses.get_analyses(user_id)
        headings = {'id': 'ID', 'name': 'Name', 'description': 'Description', 'owner': 'Owner'}
        return render_template('list.html', data=analysis_list, headings=headings, type='Analyses')
    except Exception as e:
        return handle_exception_browser(e)


@analyses.route('/create', methods=['GET', 'POST'])
def render_create_analysis():
    try:
        user_id = get_user_id()
        if request.method == 'POST':
            collection_ids = [int(collection_id) for collection_id in request.form.getlist('collection')]
            analysis = dt.analyses.create_analysis(user_id, request.form.to_dict())
            for collection_id in collection_ids:
                dt.analyses.attach_collection(user_id, analysis['id'], collection_id)
            return redirect(url_for('analyses.render_analysis', analysis_id=analysis['id']))
        return render_template('createbase.html', type='Analysis', groups=dt.user_groups.get_user_groups(),
                               endpoint='analyses.render_create_analysis')
    except Exception as e:
        return handle_exception_browser(e)


@analyses.route('/<analysis_id>', methods=['GET'])
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
