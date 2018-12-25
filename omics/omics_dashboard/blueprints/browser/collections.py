from flask import render_template, request, redirect, url_for, Blueprint

import data_tools as dt
from helpers import get_user_id, get_current_user, handle_exception_browser
collections = Blueprint('collections', __name__, url_prefix='/collections')


@collections.route('/', methods=['GET', 'POST'])
def render_collection_list():
    try:
        data = dt.collections.get_all_collection_metadata(get_current_user())
        headings = {
            'id': 'ID',
            'name': 'Name',
            'description': 'Description',
            'owner': 'Owner', 'maxRowCount':
            'Rows', 'maxColCount': 'Columns'
        }
        return render_template('list.html', type='Collections', headings=headings, data=data)
    except Exception as e:
        return handle_exception_browser(e)


@collections.route('/<collection_id>', methods=['GET', 'POST', 'DELETE'])
def render_collection(collection_id=None):
    try:
        user = get_current_user()
        collection = dt.collections.get_collection(user, collection_id)
        if request.method == 'GET':
            data = dt.collections.get_collection_metadata(user, collection)
            datasets = dt.collections.list_collection_paths(user, collection)
            metadata_fields = dt.collections.download_collection_dataframe(user, collection, True, 'json', 'split')['json']
            column_headings = ['ID'] + metadata_fields['columns']
            values = [[ind] + row for ind, row in zip(metadata_fields['index'], metadata_fields['data'])]
            return render_template('collectionentry.html', type='Collection', data=data, datasets=datasets,
                                   column_headings=column_headings, values=values)
        if request.method == 'DELETE':
            dt.collections.delete_collection(get_user_id(), collection_id)
            return redirect(url_for('samples.render_sample_list'))
        if request.method == 'POST':
            dt.collections.update_collection(user, collection, request.form)
            data = dt.collections.get_collection_metadata(user, collection)
            datasets = dt.collections.list_collection_paths(user, collection)
            return render_template('collectionentry.html', type='Collection', data=data, datasets=datasets)
    except Exception as e:
        return handle_exception_browser(e)


@collections.route('/create', methods=['GET', 'POST'])
def render_create_collection():
    try:
        user = get_current_user()
        if request.method == 'POST':
            form_data = request.form.to_dict()
            with open('/data/logs/omics.log', 'a+') as log_file:
                log_file.write(f'form_data:\n{form_data}\n')
            samples = [dt.samples.get_sample(user, sample_id) for sample_id in request.form.getlist('sample')]
            if 'sample' in form_data:
                del form_data['sample']
            sort_by = form_data['sortBy']
            del form_data['sortBy']
            data = dt.collections.create_collection(user, samples, form_data, sort_by=sort_by)
            collection_id = data['id']
            return redirect(url_for('collections.render_collection', collection_id=collection_id))
        if request.method == 'GET':
            if request.args.get('sampleIds', ''):
                sample_ids = [int(token) for token in request.args.get('sampleIds').strip('"').split(',')]
                return render_template('createbase.html', type='Collection',
                                       endpoint='collections.render_create_collection',
                                       sample_ids=sample_ids)

            return render_template('createbase.html', type='Collection',
                                   endpoint='collections.render_create_collection')
    except Exception as e:
        return handle_exception_browser(e)
