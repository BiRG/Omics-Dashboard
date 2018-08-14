from flask import Blueprint, jsonify, request
import data_tools as dt
from helpers import get_user_id, handle_exception
analyses_api = Blueprint('analyses_api', __name__, url_prefix='/api/analyses')


@analyses_api.route('/', methods=['GET', 'POST'])
def list_analyses():
    try:
        user_id = get_user_id()
        return jsonify(dt.analyses.get_analyses(user_id))
    except Exception as e:
        return handle_exception(e)


@analyses_api.route('/attach/<analysis_id>', methods=['POST'])
def attach_collection(analysis_id=None):
    try:
        user_id = get_user_id()
        data = request.get_json()
        if 'collectionIds' in data:
            for collection_id in data['collectionIds']:
                return jsonify(dt.analyses.attach_collection(user_id, analysis_id, collection_id))
        elif 'collectionId' in data:
            return jsonify(dt.analyses.attach_collection(user_id, analysis_id, data['collectionId']))
        else:
            raise ValueError('No collection id(s) specified')
    except Exception as e:
        return handle_exception(e)


@analyses_api.route('/<analysis_id>', methods=['GET', 'POST', 'DELETE'])
def get_analysis(analysis_id=None):
    try:
        user_id = get_user_id()
        if request.method == 'GET':
            res_data = dt.analyses.get_analysis(user_id, analysis_id)
            res_data['collections'] = dt.analyses.get_attached_collections(user_id, analysis_id)
            return jsonify(res_data)
        if request.method == 'POST':
            return jsonify(dt.analyses.update_analysis(user_id, analysis_id, request.get_json(force=True)))
        if request.method == 'DELETE':
            return jsonify(dt.analyses.delete_analysis(user_id, analysis_id))
    except Exception as e:
        return handle_exception(e)
