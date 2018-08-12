import json
from omics_dashboard.data_tools.samples import get_sample_metadata
from omics_dashboard.data_tools.util import AuthException, DATADIR
from omics_dashboard.data_tools.users import is_read_permitted, is_write_permitted, get_read_permitted_records
from omics_dashboard.data_tools.database import db
import omics_dashboard.data_tools.file_tools.metadata_tools as mdt
from typing import List, Dict, Any


def get_sample_groups(user_id: int) -> List[Dict[str, Any]]:
    """
    Get all sample groups visible to a user.
    :param user_id:
    :return:
    """
    sample_groups = db.query_db('select * from SampleGroups;')
    sample_groups = get_read_permitted_records(user_id, sample_groups)
    for sample_group in sample_groups:
        sample_group['members'] = get_sample_group_members(user_id, sample_group['id'])
    return sample_groups


def get_sample_group(user_id: int, group_id: int) -> Dict[str, Any]:
    """
    Get a sample group.
    :param user_id:
    :param group_id:
    :return:
    """
    sample_group = db.query_db('select * from SampleGroups where id=?;', [str(group_id)], True)
    if is_read_permitted(user_id, sample_group):
        sample_group['members'] = get_sample_group_members(user_id, group_id)
        return sample_group
    raise AuthException(f'User {user_id} is not authorized to view sample group {group_id}')


def create_sample_group(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new sample group.
    :param user_id:
    :param data:
    :return:
    """
    db.query_db('insert into SampleGroups '
                '(name, description, createdBy, owner, groupPermissions, allPermissions, userGroup, uploadWorkflowId)'
                ' values (?, ?, ?, ?, ?, ?, ?, ?);',
                [str(data['name']), str(data['description']), str(user_id), str(user_id), str(data['groupPermissions']),
                 str(data['allPermissions']), str(data['userGroup']), 'None'],  # workflow id is optional
                True)
    return db.query_db('select id, * from SampleGroups where id=last_insert_rowid()', (), True)


def update_sample_group(user_id: int, group_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the data for a sample group.
    :param user_id:
    :param group_id:
    :param new_data:
    :return:
    """
    sample_group = db.query_db('select * from SampleGroups where id=?;', [str(group_id)], True)
    valid_keys = ['name', 'description', 'owner', 'groupPermissions', 'allPermissions', 'userGroup', 'uploadWorkflowId']
    if is_write_permitted(user_id, sample_group):
        query = 'update SampleGroups set ' \
                + ','.join([' %s = ?' % key for key, value in new_data.items() if key in valid_keys]) \
                + ' where id=?;'
        params = []  # will throw if keys do not match columns in table
        [params.append(str(value)) for value in new_data.values()]
        params.append(str(group_id))
        db.query_db(query, params)
        return db.query_db('select * from SampleGroups where id=?;', [str(group_id)], True)
    raise AuthException(f'User {user_id} is not permitted to modify group {group_id}')


def update_sample_group_attachments(user_id: int, group_id: int, sample_ids: List[int]) -> Dict[str, str]:
    """
    Make the only samples attached to a group those in sample_ids
    :param user_id:
    :param group_id:
    :param sample_ids:
    :return:
    """
    print('update_sample_group_attachments')
    group = db.query_db('select * from SampleGroups where id=?', [str(group_id)], True)
    print(json.dumps({'user_id': user_id, 'group_id': group_id, 'sample_ids': sample_ids}))
    if is_write_permitted(user_id, group):
        current_member_ids = db.query_db('select sampleId from SampleGroupMemberships where sampleGroupId=?',
                                         [str(group_id)], True)
        if current_member_ids is not None:
            samples_to_detach = [sample_id for sample_id in current_member_ids if sample_id not in sample_ids]
            samples_to_attach = [sample_id for sample_id in sample_ids if sample_id not in current_member_ids]
        else:
            samples_to_detach = []
            samples_to_attach = sample_ids
        for sample_id in samples_to_detach:
            detach_sample(user_id, sample_id, group_id)
        for sample_id in samples_to_attach:
            attach_sample(user_id, sample_id, group_id)
        return {'message': f'Samples{str(samples_to_attach)} attached to group {group_id}. '
                           f'Samples {str(samples_to_detach)} detached from group {group_id}'}
    raise AuthException(f'User {user_id} not authorized to modify group {group_id}')


def attach_sample(user_id: int, sample_id: int, group_id: int):
    """
    Make a sample a member of a sample group.
    :param user_id:
    :param sample_id:
    :param group_id:
    :return:
    """
    group = db.query_db('select * from SampleGroups where id=?', [str(group_id)], True)
    sample = mdt.get_collection_info(DATADIR + '/samples/' + str(sample_id) + '.h5')
    if is_write_permitted(user_id, group) and is_write_permitted(user_id, sample):
        if not sample_in_sample_group(sample_id, group_id):
            db.query_db('insert into SampleGroupMemberships (sampleId, sampleGroupId) values (?,?);',
                        [str(sample_id), str(group_id)])
            # see if attached
        return {'message': 'collection ' + str(sample_id) + ' attached to analysis ' + str(group_id)}
    raise AuthException(f'User {user_id} is not permitted to attach {sample_id} to group {group_id}')


def detach_sample(user_id: int, sample_id: int, group_id: int):
    """
    Remove a sample from a sample group.
    :param user_id:
    :param sample_id:
    :param group_id:
    :return:
    """
    group = db.query_db('select * from SampleGroups where id=?', [str(group_id)], True)
    if is_write_permitted(user_id, group):
        db.query_db('delete from SampleGroupMemberships where sampleId=? and sampleGroupId=?;',
                    [str(sample_id), str(group_id)])
        return {'message': f'sample {sample_id} detached from group {group_id}'}
    raise AuthException(f'User {user_id} not permitted to modify group {group_id}')


def delete_sample_group(user_id: int, group_id: int) -> Dict[str, str]:
    """
    Delete a sample group.
    :param user_id:
    :param group_id:
    :return:
    """
    sample_group = db.query_db('select * from SampleGroups where id=?', [str(group_id)], True)
    if is_write_permitted(user_id, sample_group):
        db.query_db('delete from SampleGroups where id=?;', [str(group_id)])
        db.query_db('delete from SampleGroupMemberships where sampleGroupId=?', [str(group_id)])
        return {'message': f'User group {group_id} deleted'}
    raise AuthException('User {user_id} not permitted to modify sample group {group_id}')


def get_included_sample_groups(sample_id: int) -> List[Dict[str, Any]]:
    """
    Get a list of sample groups that a sample is found in
    :param sample_id:
    :return:
    """
    query = ('select SampleGroups.id, SampleGroups.name from SampleGroupMemberships '
             'inner join SampleGroups on SampleGroups.id=SampleGroupMemberships.sampleGroupId '
             'where SampleGroupMemberships.sampleId=?')
    return db.query_db(query, [sample_id])


def get_sample_group_members(user_id: int, group_id: int) -> List[Dict[str, Any]]:
    """
    Get a list of samples which belong to this group.
    :param user_id:
    :param group_id:
    :return:
    """
    query = 'select sampleId from SampleGroupMemberships where sampleGroupId=?'
    sample_ids = [line['sampleId'] for line in db.query_db(query, [str(group_id)])]
    return [get_sample_metadata(user_id, sample_id) for sample_id in sample_ids]


def sample_in_sample_group(sample_id: int, group_id: int) -> bool:
    """
    Determine if a sample belongs to a sample group.
    :param sample_id:
    :param group_id:
    :return:
    """
    return (db.query_db('select * from SampleGroupMemberships where sampleId=? and sampleGroupId=?;',
                        [str(sample_id), str(group_id)], True) is not None)
