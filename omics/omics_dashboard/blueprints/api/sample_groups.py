from flask import request, jsonify, Blueprint

import data_tools as dt
from helpers import get_current_user, handle_exception
from data_tools.util import AuthException
sample_groups_api = Blueprint('sample_groups_api', __name__, url_prefix='/api/sample_groups')


@sample_groups_api.route('/', methods=['GET', 'POST'])
def list_sample_groups():
    try:
        return jsonify([sample_group.to_dict()
                        for sample_group in dt.sample_groups.get_sample_groups(get_current_user())])
    except Exception as e:
        return handle_exception(e)


@sample_groups_api.route('/<sample_group_id>', methods=['GET', 'POST', 'DELETE'])
def get_sample_group(sample_group_id=None):
    try:
        user = get_current_user()
        sample_group = dt.sample_groups.get_sample_group(user, sample_group_id)
        if request.method == 'GET':
            return jsonify(sample_group.to_dict())
        if request.method == 'DELETE':
            samples_to_delete = [sample for sample in sample_group.samples if len(sample.sample_groups) < 2]
            data = dt.sample_groups.delete_sample_group(user, sample_group)
            sample_messages = []
            for sample in samples_to_delete:
                try:
                    sample_messages.append(dt.samples.delete_sample(user, sample)['message'])
                except AuthException:
                    pass
            messages = [data['message']] + sample_messages
            return jsonify({'messages': messages})
        if request.method == 'POST':
            return jsonify(dt.sample_groups
                           .update_sample_group(user, sample_group, request.get_json(force=True))
                           .to_dict())
    except Exception as e:
        return handle_exception(e)


@sample_groups_api.route('/attach/<sample_group_id>', methods=['POST', 'DELETE'])
def attach_sample(sample_group_id=None):
    try:
        user = get_current_user()
        sample_group = dt.sample_groups.get_sample_group(user, sample_group_id)
        data = request.get_json(force=True)
        print(data)
        samples = [dt.samples.get_sample(user, sample_id) for sample_id in data['sample_ids']]
        if request.method == 'POST':
            for sample in samples:
                dt.sample_groups.attach_sample(user, sample, sample_group)
            return jsonify(sample_group.to_dict())
        elif request.method == 'DELETE':
            for sample in samples:
                dt.sample_groups.detach_sample(user, sample, sample_group)
            return jsonify(sample_group.to_dict())
    except Exception as e:
        return handle_exception(e)
