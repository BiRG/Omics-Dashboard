from flask import render_template, request, redirect, url_for, Blueprint
from flask_login import login_required

import data_tools as dt
from data_tools.wrappers.analyses import get_analyses, get_analysis
from config.socket_config import send_message
from data_tools.db_models import Collection
from data_tools.template_models.entry_page import AnalysisPageData
from data_tools.template_models.form import AnalysisCreateFormData
from data_tools.template_models.list_table import ListTableData
from helpers import get_current_user, handle_exception_browser, process_input_dict

analyses = Blueprint('analyses', __name__, url_prefix='/analyses')


@analyses.route('/', methods=['GET', 'POST'])
@login_required
def render_analysis_list():
    try:
        current_user = get_current_user()
        send_message(current_user, 'You visited the analysis list page.')
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_analyses(current_user), 'Analyses'))
    except Exception as e:
        return handle_exception_browser(e)


@analyses.route('/create', methods=['GET', 'POST'])
@login_required
def render_create_analysis():
    try:
        current_user = get_current_user()
        if request.method == 'POST':
            new_data = process_input_dict(request.form.to_dict(), True)
            if 'collection_ids' in new_data:
                del new_data['collection_ids']
            collection_ids = [int(collection_id) for collection_id in request.form.getlist('collection_ids')]
            collections = Collection.query.filter(Collection.id.in_(collection_ids)).all()
            analysis = dt.analyses.create_analysis(current_user, new_data, collections)
            return redirect(url_for('analyses.render_analysis', analysis_id=analysis.id))
        selected_collection_ids = [int(token) for token in request.args.get('collection_ids').strip('"').split(',')] \
            if request.args.get('sample_ids', '') else []
        selected_collections = Collection.query.filter(Collection.id.in_(selected_collection_ids)).all()
        return render_template('pages/create.html',
                               page_data=AnalysisCreateFormData(current_user, selected_collections))
    except Exception as e:
        return handle_exception_browser(e)


@analyses.route('/<analysis_id>', methods=['GET'])
@login_required
def render_analysis(analysis_id=None):
    try:
        current_user = get_current_user()
        return render_template('pages/analysis_entry.html',
                               page_data=AnalysisPageData(current_user, get_analysis(current_user, analysis_id)))
    except Exception as e:
        return handle_exception_browser(e)
