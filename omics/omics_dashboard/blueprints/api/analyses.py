from flask import Blueprint, jsonify, request

import data_tools as dt
from data_tools.users import is_write_permitted
from helpers import get_current_user, handle_exception

analyses_api = Blueprint('analyses_api', __name__, url_prefix='/api/analyses')


@analyses_api.route('/', methods=['GET', 'POST'])
def list_analyses():
    try:
        print('list_analyses')
        user = get_current_user()
        print(request.method)
        if request.method == 'POST':
            print('POST')
            new_data = request.get_json(force=True)
            print(new_data)
            if 'collection_ids' in new_data:
                collections = [dt.collections.get_collection(user, collection_id) for collection_id in new_data['collection_ids']]
            else:
                collections = None
            analysis = dt.analyses.create_analysis(user, new_data, collections)
            return jsonify(analysis.to_dict())
        return jsonify([analysis.to_dict() for analysis in dt.analyses.get_analyses(user)])
    except Exception as e:
        return handle_exception(e)


@analyses_api.route('/attach/<analysis_id>', methods=['POST', 'DELETE'])
def attach_collection(analysis_id=None):
    try:
        user = get_current_user()
        analysis = dt.analyses.get_analysis(user, analysis_id)
        data = request.get_json()
        if 'collection_ids' in data:
            collections = [dt.collections.get_collection(user, collection_id)
                           for collection_id in data['collection_ids']]
            for collection in collections:
                if request.method == 'POST':
                    dt.analyses.attach_collection(user, analysis, collection)
                if request.method == 'DELETE':
                    dt.analyses.detach_collection(user, analysis, collection)
            return jsonify({**analysis.to_dict(), 'is_write_permitted': is_write_permitted(user, analysis)})
        else:
            raise ValueError('No collection id(s) specified')
    except Exception as e:
        return handle_exception(e)


@analyses_api.route('/<analysis_id>', methods=['GET', 'POST', 'DELETE'])
def get_analysis(analysis_id=None):
    try:
        user = get_current_user()
        if request.method == 'GET':
            analysis = dt.analyses.get_analysis(user, analysis_id)
            return jsonify(analysis.to_dict())
        if request.method == 'POST':
            analysis = dt.analyses.get_analysis(user, analysis_id)
            print(f'req_body: {request.get_json(force=True)}')
            print(f'analysis: {analysis.to_dict()}')
            return jsonify(dt.analyses.update_analysis(user, analysis, request.get_json(force=True)).to_dict())
        if request.method == 'DELETE':
            analysis = dt.analyses.get_analysis(user, analysis_id)
            return jsonify(dt.analyses.delete_analysis(user, analysis))
    except Exception as e:
        return handle_exception(e)
