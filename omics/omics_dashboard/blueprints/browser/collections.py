from flask import render_template, request, redirect, url_for, Blueprint
from flask_login import login_required

import data_tools as dt
from data_tools.access_wrappers.collections import get_collections, get_collection, delete_collection
from data_tools.db_models import Sample
from data_tools.template_data.entry_page import CollectionPageData
from data_tools.template_data.form import CollectionCreateFormData
from data_tools.template_data.list_table import ListTableData
from helpers import get_current_user, handle_exception_browser, process_input_dict

collections = Blueprint('collections', __name__, url_prefix='/collections')


@collections.route('/', methods=['GET', 'POST'])
@login_required
def render_collection_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_collections(current_user), 'Collections'))
    except Exception as e:
        return handle_exception_browser(e)


@collections.route('/<collection_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def render_collection(collection_id=None):
    try:
        current_user = get_current_user()
        collection = get_collection(current_user, collection_id)
        if request.method == 'DELETE':
            delete_collection(current_user, collection_id)
            return redirect(url_for('collections.render_collection_list'))
        if request.method == 'POST':
            dataset_name = request.form.get('dataset_name')
            dataset_type = request.form.get('dtype')
            dt.collections.create_new_label_dataset(current_user, collection, dataset_name, dataset_type)
        return render_template('pages/collection_entry.html',
                               page_data=CollectionPageData(current_user, collection))
    except Exception as e:
        return handle_exception_browser(e)


@collections.route('/create', methods=['GET', 'POST'])
@login_required
def render_create_collection():
    try:
        current_user = get_current_user()
        if request.method == 'POST':
            form_data = process_input_dict(request.form.to_dict(), True)
            samples = [dt.samples.get_sample(current_user, sample_id) for sample_id in request.form.getlist('sample_ids')]
            if 'sample_ids' in form_data:
                del form_data['sample_ids']
            sort_by = form_data['sort_by']
            del form_data['sort_by']
            collection = dt.access_wrappers.collections.create_collection(current_user, samples, form_data,
                                                                          sort_by=sort_by)
            return redirect(url_for('collections.render_collection', collection_id=collection.id))
        if request.method == 'GET':
            if request.args.get('sample_ids', ''):
                sample_ids = [int(token) for token in request.args.get('sample_ids').strip('"').split(',')]
                selected_samples = Sample.query.filter(Sample.id.in_(sample_ids)).all()
            else:
                selected_samples = None
            return render_template('pages/create.html',
                                   page_data=CollectionCreateFormData(current_user, selected_samples))
    except Exception as e:
        return handle_exception_browser(e)
