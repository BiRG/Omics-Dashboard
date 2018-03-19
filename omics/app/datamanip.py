from passlib.hash import pbkdf2_sha256
import importlib
import yaml
import os
from file_tools import metadatatools as mdt
from file_tools import h5merge
from db import db
import h5py
from xkcdpass import xkcd_password as xp
import sys
import requests
import json
import uuid
import shutil

DATADIR = os.environ['DATADIR']
TMPDIR = os.environ['TMPDIR'] if 'TMPDIR' in os.environ else DATADIR + '/tmp'
COMPUTESERVER = os.environ['COMPUTESERVER']
MODULEDIR = os.environ['MODULEDIR'] if 'MODULEDIR' in os.environ else DATADIR + '/modules'

# TODO: raise exceptions for unauthorized
# route functions should capture exceptions from SQLite3




class AuthException(Exception):
    pass


def validate_file(path):
    return h5py.is_hdf5(path)


def is_admin(user_id):
    return db.query_db('select * from Users where id=? and admin=1;', [str(user_id)], True) is not None


def user_in_group(user_id, group_id):
    return (db.query_db('select * from GroupMemberships where userId=? and groupId=?;', [str(user_id), str(group_id)], True)
            is not None)






def is_group_admin(user_id, group_id):
    return (db.query_db('select * from GroupMemberships where userId=? and groupId=? and groupAdmin=1;',
                     [str(user_id), str(group_id)], True)
            is not None)


def is_read_permitted(user_id, record):
    return is_admin(user_id) \
        or record['allPermissions'] == 'readonly' \
        or record['allPermissions'] == 'full' \
        or ((record['groupPermissions'] == 'readonly' or record['allPermissions'] == 'full') and user_in_group(record['userGroup']))


def is_write_permitted(user_id, record):
    return is_admin(user_id) or record['allPermissions'] == 'full' \
           or (record['allPermissions'] == 'full' and user_in_group(user_id, record['userGroup']))


def get_read_permitted_records(user_id, records):
    return [record for record in records if is_read_permitted(user_id, record)]


def get_next_id(path):
    files = os.listdir(path)
    if not files:
        return 0
    ids = [int(os.path.splitext(file)[0]) for file in files]
    return 0 if ids is None else max(ids) + 1


# Create, Read, Update, Delete from db or files
# Users
def get_users():
    return db.query_db('select id, name, email, admin from Users;')


def get_user(user_id):
    return db.query_db('select id, name, email, admin from Users where rowid=?;', [str(user_id)], True)


def get_user_by_email(email):
    return db.query_db('select id, name, email, admin from Users where email=?;', [str(email)], True)


def get_user_password_hash(email):
    return db.query_db('select password from Users where email=?;', [str(email)], True)


def create_user(current_user_id, data):
    if is_admin(current_user_id):
        # check email
        if len(db.query_db('select * from Users where email=?', [data['email']])):
            raise ValueError('This email is already in use!')
        db.query_db('insert into Users (name, email, admin, password) values (?, ?, ?, ?);',
                    [str(data['name']), str(data['email']), str(data['admin']), pbkdf2_sha256.hash(data['password'])])
        return db.query_db('select id, name, email, admin from Users where id=last_insert_rowid()', (), True)
    raise AuthException('must be admin to create user')


def register_user(invitation_string, data):
    # check email
    if len(db.query_db('select * from Users where email=?;', [data['email']])):
        raise ValueError('This email is already in use!')
    if len(db.query_db('select * from Invitations where value=?;', [invitation_string], True)):
        db.query_db('insert into Users (name, email, admin, password) values (?, ?, ?, ?)',
                    [str(data['name']), str(data['email']), '0', pbkdf2_sha256.hash(data['password'])])
        db.query_db('delete from Invitations where value=?;', [invitation_string])
        return db.query_db('select id, name, email, admin from Users where id=last_insert_rowid()', (), True)
    raise ValueError('Incorrect invitation')


def update_user(current_user_id, target_user_id, new_data):
    if (current_user_id == target_user_id) or is_admin(current_user_id):
        # if new password provided, hash it
        if 'password' in new_data:
            new_data['password'] = pbkdf2_sha256.hash(new_data['password'])
        if 'email' in new_data:
            emails = db.query_db('select * from Users where email=?', [new_data['email']])
            if len(emails):
                raise ValueError('This email is already in use!')
        valid_keys = ['name', 'email', 'admin', 'password']
        query = 'update Users set' + ','.join([' %s = ?' % key for key in new_data.keys() if key in valid_keys]) \
                + ' where id=?;'
        params = []
        [params.append(str(value)) for key, value in new_data.items() if key in valid_keys]
        params.append(target_user_id)
        db.query_db(query, params)
        return db.query_db('select id, name, email, admin from Users where id=?;', [str(target_user_id)], True)

    raise AuthException('User %s does not have permissions to edit user %s' % (str(current_user_id), str(target_user_id)))


def delete_user(current_user_id, target_user_id):
    if (current_user_id == target_user_id) or is_admin(current_user_id):
        # delete user from users table and nullify all the ids set based on this user
        db.query_db('delete from Users where id=?;', str(target_user_id))
        db.query_db('update GroupMemberships set userId=null where userId=?;', [str(target_user_id)])
        db.query_db('update UserGroups set createdBy=null where createdBy=?;', [str(target_user_id)])
        db.query_db('update UserGroups set groupAdmin=null where groupAdmin=?;', [str(target_user_id)])
        db.query_db('update Analyses set owner=null where owner=?;', [str(target_user_id)])

        # set all createdBy and owner to null in samples and collections
        # notice how much easier it was in SQL? Maybe storing metadata in hdf5 files is a bad idea
        samples = get_all_samples()
        collections = get_all_collections()
        filenames = ['%s/samples/%s.h5' % (DATADIR, str(sample['id'])) for sample in samples if str(sample['owner']) == str(target_user_id)]
        filenames.extend(['%s/collections/%s.h5' % (DATADIR, str(collection['id'])) for collection in collections if str(collection['owner']) == str(target_user_id)])
        [mdt.update_metadata(filename, {'owner': -1}) for filename in filenames]
        filenames = ['%s/samples/%s.h5' % (DATADIR, str(sample['id'])) for sample in samples if str(sample['createdBy']) == str(target_user_id)]
        filenames.extend(['%s/collections/%s.h5' % (DATADIR, str(collection['id'])) for collection in collections if str(collection['createdBy']) == str(target_user_id)])
        [mdt.update_metadata(filename, {'createdBy': -1}) for filename in filenames]

        return {'message': 'user %s deleted' % str(target_user_id)}
    raise AuthException('User %s does not have permissions to delete user %s' % (str(current_user_id), str(target_user_id)))


# samples
def get_all_samples():
    paths = [DATADIR + '/samples/' + file for file in os.listdir(DATADIR + '/samples')]
    return [mdt.get_collection_info(path) for path in paths]


def get_samples(user_id):
    paths = [DATADIR + '/samples/' + file for file in os.listdir(DATADIR + '/samples')]
    collection_info = [mdt.get_collection_info(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_all_sample_metadata(user_id):
    paths = [DATADIR + '/samples/' + file for file in os.listdir(DATADIR + '/samples')]
    collection_info = [mdt.get_collection_metadata(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_sample_metadata(user_id, sample_id):
    collection_info = mdt.get_collection_metadata(DATADIR + '/samples/' + str(sample_id) + '.h5')
    if is_read_permitted(user_id, collection_info):
        return collection_info
    raise AuthException('User %s is not authorized to view sample %s' % (str(user_id), str(sample_id)))


def get_sample(user_id, sample_id):
    sample_info = mdt.get_collection_info(DATADIR + '/samples/' + str(sample_id) + '.h5')
    if is_read_permitted(user_id, sample_info):
        return sample_info
    raise AuthException('User %s is not permitted to access sample %s' % (str(user_id), str(sample_id)))


def download_sample_dataset(user_id, sample_id, path):
    filename = '%s/samples/%s.h5' % (DATADIR, str(sample_id))
    collection = mdt.get_collection_metadata(filename)
    csv_filename = os.path.basename(os.path.normpath(path))
    if is_read_permitted(user_id, collection):
        return {'csv': mdt.get_csv(filename, path), 'cd': 'attachment; filename=%s.csv' % csv_filename}
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(sample_id)))


def download_sample(user_id, sample_id):
    filename = '%s/samples/%s.h5' % (DATADIR, str(sample_id))
    sample = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, sample):
        return {'filename': '%s.h5' % str(sample_id)}
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(sample_id)))


def list_sample_paths(user_id, sample_id):
    filename = '%s/samples/%s.h5' % (DATADIR, str(sample_id))
    sample = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, sample):
        return mdt.get_dataset_paths(filename)
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(sample_id)))


def update_sample(user_id, sample_id, new_data):
    sample_info = mdt.get_collection_metadata(DATADIR + '/samples/' + str(sample_id) + '.h5')
    if is_write_permitted(user_id, sample_info):
        return mdt.update_metadata('%s/samples/%s.h5' % (str(DATADIR), str(sample_id)), new_data)
    raise AuthException('User %s does not have permission to edit sample %s' % (str(user_id), str(sample_id)))


def delete_sample(user_id, sample_id):
    sample_info = mdt.get_collection_metadata(DATADIR + '/samples/' + str(sample_id) + '.h5')
    if is_write_permitted(user_id, sample_info):
        os.remove(DATADIR + '/samples/' + str(sample_id) + '.h5')
        return {'message': 'sample ' + str(sample_id) + ' removed'}
    raise AuthException('User %s does not have permission to modify sample %s' % (str(user_id), str(sample_id)))


# collections
def get_all_collections():
    paths = [DATADIR + '/collections/' + file for file in os.listdir(DATADIR + '/collections/')]
    return [mdt.get_collection_info(path) for path in paths]


def get_collections(user_id):
    paths = [DATADIR + '/collections/' + file for file in os.listdir(DATADIR + '/collections/')]
    collection_info = [mdt.get_collection_info(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_all_collection_metadata(user_id):
    paths = [DATADIR + '/collections/' + file for file in os.listdir(DATADIR + '/collections/')]
    collection_info = [mdt.get_collection_metadata(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_collection_metadata(user_id, collection_id):
    collection_info = mdt.get_collection_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_read_permitted(user_id, collection_info):
        return collection_info
    raise AuthException('User %s is not authorized to view collection %s' % (str(user_id), str(collection_id)))


def get_collection(user_id, collection_id):
    collection_info = mdt.get_collection_info(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_read_permitted(user_id, collection_info):
        return collection_info
    raise AuthException('User %s is not authorized to view collection %s' % (str(user_id), str(collection_id)))


def update_collection(user_id, collection_id, new_data):
    collection_info = mdt.get_collection_info(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_write_permitted(user_id, collection_info):
        return mdt.update_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5', new_data)
    raise AuthException('User %s is not permitted to modifiy collection %s' % (str(user_id), str(collection_id)))


def upload_collection(user_id, filename, new_data):
    # verify that the collection file is valid
    # filename is in a temporary location for uploads
    if validate_file(filename):
        new_id = get_next_id(f'{DATADIR}/collections/')
        new_filename = f'{DATADIR}/collections/{new_id}.h5'
        os.rename(filename, new_filename)
        # user can add any arbitrary valid JSON to a collection
        # if it gets to this point, it has already been validated!
        mdt.update_metadata(new_filename, new_data)
        new_data = {} if new_data is None else new_data
        new_data['createdBy'] = user_id
        new_data['owner'] = user_id
        mdt.update_metadata(new_filename, new_data)
        return mdt.get_collection_info(new_filename)
    raise Exception('file not valid')


# verifies permissions of user to download a collection, returns a filename or a message
def download_collection(user_id, collection_id):
    filename = f'{DATADIR}/collections/{collection_id}.h5'
    collection = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, collection):
        return {'filename': f'{collection_id}.h5'}
    raise AuthException(f'User {user_id} is not permitted to access collection {collection_id}')


def download_collection_dataset(user_id, collection_id, path):
    filename = '%s/collections/%s.h5' % (DATADIR, str(collection_id))
    collection = mdt.get_collection_metadata(filename)
    csv_filename = os.path.basename(os.path.normpath(path))
    if is_read_permitted(user_id, collection):
        return {'csv': mdt.get_csv(filename, path), 'cd': 'attachment; filename=%s.csv' % csv_filename}
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(collection_id)))


def list_collection_paths(user_id, collection_id):
    filename = '%s/collections/%s.h5' % (DATADIR, str(collection_id))
    collection = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, collection):
        return mdt.get_dataset_paths(filename)
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(collection_id)))


def create_collection(user_id, sample_ids, new_data, sortBy='baseSampleId'):
    print('set new_data:\n')
    new_data['owner'] = user_id
    outfilename = f'{DATADIR}/collections/{get_next_id("/data/collections")}.h5'
    filenames = [f'{DATADIR}/samples/{sample_id}.h5' for sample_id in sample_ids]
    print('check permissions on samples:\n')
    for filename in filenames:
        if not is_read_permitted(user_id, mdt.get_collection_metadata(filename)):
            raise AuthException(f'User {user_id} is not permitted to access file {filename}')
    print('h5merge:\n')
    h5merge.h5_merge(filenames, outfilename, reserved_paths=['/x'], sortBy=sortBy) 
    #TODO: allow samples aligned at 'x' with NaN padding
    print('update_metadata:\n')
    return mdt.update_metadata(outfilename, new_data)


def delete_collection(user_id, collection_id):
    collection_info = mdt.get_collection_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_write_permitted(user_id, collection_info):
        os.remove(DATADIR + '/collections/' + str(collection_id) + '.h5')
        db.query_db('delete from CollectionMemberships where collectionId=?;', [str(collection_id)])
        return {'message': 'collection ' + str(collection_id) + ' removed'}
    raise AuthException('User %s not authorized to modify collection %s' % (str(user_id), str(collection_id)))


# TODO: workflows
# workflows are defined in YAML files in DATADIR/workflows
# basic metadata is stored in the DB
# these yaml files define inputs and outputs and module coordination

def get_workflows(user_id):
    results = db.query_db('select * from Workflows;')
    return [result for result in results if is_read_permitted(user_id, result)]


def get_workflow(user_id, workflow_id):
    result = db.query_db('select * from Workflows where id=?;', [str(workflow_id)], True)
    if is_read_permitted(user_id, result):
        return result
    raise AuthException('User %s is not permitted to access analysis %s' % (str(user_id), str(workflow_id)))


def update_workflow(user_id, workflow_id, new_data):
    analysis = db.query_db('select * from Workflows where id=?;', str(workflow_id), True)
    valid_keys = ['name', 'description', 'groupPermissions', 'allPermissions', 'userGroup']
    if is_write_permitted(user_id, analysis):
        query = 'update Analyses set ' \
                + ','.join([' %s = ?' % key for key, value in new_data.items() if key in valid_keys]) \
                + ' where id=?;'
        params = []
        [params.append(str(value)) for key, value in new_data.values() if key in valid_keys]
        params.append(str(workflow_id))
        db.query_db(query, params)
        return db.query_db('select * from Workflows where id=?;', [str(workflow_id)], True)
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(workflow_id)))


def create_workflow(user_id, data):
    db.query_db('insert into Workflows (name, description, createdBy, owner, groupPermissions, allPermissions, userGroup) '
                + 'values (?, ?, ?, ?, ?, ?, ?);',
                [str(data['name']), str(data['description']), str(user_id), str(user_id), str(data['groupPermissions']),
                 str(data['allPermissions']), str(data['userGroup'])],
                True)
    workflow = db.query_db('select * from Workflows where id=last_insert_rowid()', (), True)
    # TODO: Create a workflow file
    # TODO: write the basic workflow definition to the file
    return workflow


def delete_workflow(user_id, workflow_id):
    analysis = db.query_db('select * from Workflows where id=?;', str(workflow_id), True)
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from Workflows where id=?;', [str(workflow_id)])
        db.query_db('delete from WorkflowMemberships where workflowId=?;', [str(workflow_id)])
        return {'message': 'analysis ' + str(workflow_id) + ' deleted'}
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(workflow_id)))


# analyses
def get_analyses(user_id):
    results = db.query_db('select * from Analyses;')
    return [result for result in results if is_read_permitted(user_id, result)]


def get_analysis(user_id, analysis_id):
    result = db.query_db('select id, * from Analyses where rowid=?;', [str(analysis_id)], True)
    if is_read_permitted(user_id, result):
        return result
    raise AuthException('User %s is not permitted to access analysis %s' % (str(user_id), str(analysis_id)))


def update_analysis(user_id, analysis_id, new_data):
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    valid_keys = ['name', 'description', 'owner', 'groupPermissions', 'allPermissions', 'userGroup']
    if is_write_permitted(user_id, analysis):
        query = 'update Analyses set ' \
                + ','.join([' %s = ?' % key for key, value in new_data.items() if key in valid_keys]) \
                + ' where id=?;'
        params = []  # TODO: validate params against schema
        [params.append(str(value)) for value in new_data.values()]
        params.append(str(analysis_id))
        db.query_db(query, params)
        return db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(analysis_id)))


def create_analysis(user_id, data):
    db.query_db('insert into Analyses (name, description, createdBy, owner, groupPermissions, allPermissions, userGroup) '
                + 'values (?, ?, ?, ?, ?, ?, ?);',
                [str(data['name']), str(data['description']), str(user_id), str(user_id), str(data['groupPermissions']),
                 str(data['allPermissions']), str(data['userGroup'])],
                True)
    return db.query_db('select id, * from Analyses where id=last_insert_rowid()', (), True)


def delete_analysis(user_id, analysis_id):
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    if analysis is None:
        return {'message': f'Analysis {analysis_id} does not exist'}
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from Analyses where id=?;', [str(analysis_id)])
        return {'message': 'analysis ' + str(analysis_id) + ' deleted'}
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(analysis_id)))


def attach_collection(user_id, analysis_id, collection_id):
    # check read permissions on analysis and collection
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    collection = mdt.get_collection_metadata(f'{DATADIR}/collections/{collection_id}.h5')
    if is_write_permitted(user_id, collection) and is_write_permitted(user_id, analysis):
        db.query_db('insert into CollectionMemberships (collectionId, analysisId) values (?,?);', [str(collection_id), str(analysis_id)])
        # see if attached
        return {'message': 'collection ' + str(collection_id) + ' attached to analysis ' + str(analysis_id)}
    raise AuthException('User %s is not permitted to attach collection %s to analysis %s' % (str(user_id), str(collection_id), str(analysis_id)))


def detach_collection(user_id, analysis_id, collection_id):
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from CollectionMemberships where collectionId=? and analysisId=?;',
                    [str(collection_id), str(analysis_id)])
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(analysis_id)))


def get_attached_collections(user_id, analysis_id):
    analysis = get_analysis(user_id, analysis_id)
    attachment_data = db.query_db('select * from CollectionMemberships where analysisId=?;', [str(analysis_id)])
    print(attachment_data)
    if is_read_permitted(user_id, analysis):
        collections = [mdt.get_collection_info(f'{DATADIR}/collections/{attachment["collectionId"]}.h5') for attachment in attachment_data]
        print([collection for collection in collections if is_read_permitted(user_id, collection)])
        return [collection for collection in collections if is_read_permitted(user_id, collection)]
    raise AuthException(f'User {user_id} is not permitted to access analysis {analysis_id}')


def get_attached_analyses(user_id, collection_id):
    collection = get_collection(user_id, collection_id)
    attachment_data = db.query_db('select * from CollectionMemberships where collectionId=?;', [str(collection_id)])
    if is_read_permitted(user_id, collection):
        analyses = []
        for attachment in attachment_data:
            analysis = db.query_db('select * from Analyses where id=?', [str(attachment['analysisId'])])
            if is_read_permitted(user_id, analysis):
                analyses.append(analysis)
        return analyses
    raise AuthException(f'User {user_id} not permitted to access collection {collection_id}')


# user groups
# user groups do not have permissions for viewing
def get_user_groups():
    user_groups = db.query_db('select * from UserGroups;')
    for user_group in user_groups:
        group_members = get_group_members(user_group['id'])
        user_group['members'] = group_members
        user_group['users'] = [member['id'] for member in group_members]
        user_group['admins'] = [member['id'] for member in group_members if member['groupAdmin']]
    return user_groups


def get_user_group(group_id):
    user_group = db.query_db('select * from UserGroups where id=?;', [str(group_id)], True)
    group_members = get_group_members(group_id)
    user_group['members'] = group_members
    user_group['users'] = [member['id'] for member in group_members]
    user_group['admins'] = [member['id'] for member in group_members if member['groupAdmin']]
    return user_group


def create_user_group(user_id, data):
    db.query_db('insert into UserGroups (createdBy, name, description) values (?, ?, ?);',
             [str(user_id), str(data['name']), str(data['description'])],
             True)
    new_group = db.query_db('select * from UserGroups order by id desc limit 1;', (), True)
    db.query_db('insert into GroupMemberships (userId, groupId, groupAdmin) values(?, ?, ?);',
             [str(user_id), str(new_group['id']), '1'])
    return new_group


def update_user_group(user_id, group_id, new_data):
    if is_group_admin(user_id, group_id):
        valid_keys = ['name', 'description']
        valid_data = {key: value for key, value in new_data.items() if key in valid_keys}
        if len(valid_data):
            query = 'update UserGroups set' + ','.join([f' {key} = ?' for key in valid_data.keys()]) + ' where id=?;'
            params = [str(value) for key, value in new_data.items() if key in valid_keys]
            params.append(str(group_id))
            db.query_db(query, params)
        return db.query_db('select * from UserGroups where id=?;', [str(group_id)], True)
    raise AuthException('User %s is not authorized to modify user group %s' % (str(user_id), str(group_id)))


def update_user_attachments(current_user_id, group_id, user_ids):
    if is_group_admin(current_user_id, group_id):
        user_ids = [int(user_id) for user_id in user_ids if int(user_id) != int(current_user_id)]
        current_member_ids = [member['id'] for member in get_group_members(group_id)]
        users_to_detach = [member_id for member_id in current_member_ids if member_id not in user_ids and member_id != current_user_id]
        users_to_attach = [user_id for user_id in user_ids if user_id not in current_member_ids]
        for user_id in users_to_attach:
            attach_user(current_user_id, user_id, group_id)
        for user_id in users_to_detach:
            detach_user(current_user_id, user_id, group_id)
        return {'message': f'Users {str(users_to_attach)} attached to group {group_id}. Users {str(users_to_detach)} detached from group {group_id}'}
    raise AuthException(f'User {current_user_id} not authorized to modify group {group_id}')

def attach_user(current_user_id, target_user_id, group_id):
    if is_group_admin(current_user_id, group_id):
        if not user_in_group(target_user_id, group_id):
            db.query_db('insert into GroupMemberships (userId, groupId, groupAdmin) values (?, ?, ?);',
                     [str(target_user_id), str(group_id), '0'])
            return db.query_db('select * from UserGroups order by id desc limit 1;', (), True)
        return {'message': f'user {target_user_id} attached to group {group_id}'}
    raise AuthException('User %s is not authorized to attach user %s to group %s' % (str(current_user_id), str(target_user_id), str(group_id)))


def elevate_user(current_user_id, target_user_id, group_id):
    if is_group_admin(current_user_id, group_id):
        db.query_db('update GroupMemberships set groupAdmin=1 where id=?;', [str(target_user_id)])
        return {'message': 'User %s elevated to admin of group %s' % (str(target_user_id), str(group_id))}
    raise AuthException('User %s not authorized to modify group %s' % (str(current_user_id), str(group_id)))


def detach_user(current_user_id, target_user_id, group_id):
    if target_user_id == current_user_id or is_group_admin(current_user_id, group_id):
        db.query_db('delete from GroupMemberships where userId=? and groupId=?;',
                 [str(target_user_id), str(group_id)])
        return {'message': 'user ' + str(target_user_id) + ' detached from group ' + str(group_id)}
    raise AuthException('User %s not permitted to modify group %s' % (str(current_user_id), str(group_id)))


def delete_user_group(user_id, group_id):
    if is_group_admin(user_id, group_id):
        db.query_db('delete from UserGroups where id=?;', [str(group_id)])
        db.query_db('delete from GroupMemberships where groupId=?', [str(group_id)])
        return {'message': 'user group ' + str(group_id) + ' deleted'}
    raise AuthException('User %s not permitted to modify group %s' % (str(user_id), str(group_id)))


# returns list of dicts with keys ['id', 'name', 'groupAdmin']
def get_included_groups(user_id):
    query = 'select UserGroups.id, UserGroups.name, GroupMemberships.groupAdmin from GroupMemberships inner join UserGroups on UserGroups.id=GroupMemberships.groupId where GroupMemberships.userId=?'
    return db.query_db(query, [user_id])


# returns dict with keys ['id', 'name', 'groupAdmin']
def get_group_members(group_id):
    query = 'select Users.id, Users.name, GroupMemberships.groupAdmin' \
            ' from Users' \
            ' inner join GroupMemberships on GroupMemberships.userId=Users.id' \
            ' where GroupMemberships.groupId=?'
    return db.query_db(query, [str(group_id)])


def create_invitation(user_id):
    if is_admin(user_id):
        invite_string = xp.generate_xkcdpassword(xp.generate_wordlist(valid_chars='[a-z]'), numwords=3, delimiter='_')
        db.query_db('insert into Invitations (createdBy, value) values (?,?);', [str(user_id), invite_string])
        return db.query_db('select * from Invitations where id=last_insert_rowid();', (), True)


def get_modules(path):
    # parse the module descriptions
    yaml_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and os.path.splitext(f)[-1] == '.cwl']
    # output will include label.
    out = []
    for f in yaml_files:
        try:
            out.append(get_module(os.path.join(path, f)))
        except yaml.YAMLError as e:
            sys.stderr.write(f'Error parsing CWL module {f}: {e}')
    return out


def get_module(path):
    with open(path, 'r') as stream:
        data = yaml.load(stream)
        if 'cwlVersion' not in data:
            raise yaml.YAMLError('Not a CWL file')
        data['modulePath'] = path
        return data


def get_module_by_id(basepath, id):
    yaml_files = [f for f in os.listdir(basepath) if os.path.isfile(os.path.join(basepath, f)) and os.path.splitext(f)[-1] == 'cwl']
    for f in yaml_files:
        module = get_module(f)
        if module['id'] == id:
            return module
    raise ValueError(f'Module with id {id} does not exist in {basepath}')


def get_preprocessing_modules():
    return get_modules(f'{MODULEDIR}/processing-modules')


def get_parsing_modules():
    modules = get_modules(f'{MODULEDIR}/file-parsers')
    return modules


# request_data is a dictionary
def start_job(workflow_path, request_data, token, data_type='collection', owner=-1):
    params = {'wf': f'{workflow_path}', 'data_type': data_type, 'owner': owner}
    headers = {'Authorization': token}
    response = requests.post(f'{COMPUTESERVER}/run',
                             json=request_data,
                             headers=headers,
                             params=params)
    try:
        return response.json()
    except Exception as e:
        with open(f'{DATADIR}/logs/omics.log', 'a+') as log_file:
            log_file.write(f'{str(e)}\n')
            log_file.write(f'{str(request_data)}\n')
            log_file.write(f'{response.content}')
        raise RuntimeError('Invalid response from job server. Is the server running?')


def get_jobs():
    url = f'{COMPUTESERVER}/jobs'
    response = requests.get(url)
    print(response)
    return response.json()


def get_job(job_id):
    url = f'{COMPUTESERVER}/jobs/{job_id}'
    response = requests.get(url)
    return response.json()


def cancel_job(user_id, job_id):
    data = json.loads(requests.get('%s/jobs/%i' % (COMPUTESERVER, job_id)))
    if data['owner'] == user_id or is_admin(user_id):
        url = 'http://%s/jobs/%i?action=cancel' % (COMPUTESERVER, job_id)
        response = requests.get(url)
        return response.json()
    raise AuthException('User %s is not authorized to resume job %s' % (str(user_id), str(job_id)))


def pause_job(user_id, job_id):
    data = json.loads(requests.get('%s/jobs/%i' % (COMPUTESERVER, job_id)))
    if data['owner'] == user_id or is_admin(user_id):
        url = 'http://%s/jobs/%i?action=pause' % (COMPUTESERVER, job_id)
        response = requests.get(url)
        return response.json()
    raise AuthException('User %s is not authorized to resume job %s' % (str(user_id), str(job_id)))


def resume_job(user_id, job_id):
    data = json.loads(requests.get('%s/jobs/%i' % (COMPUTESERVER, job_id)))
    if data['owner'] == user_id or data['owner'] < 0 or is_admin(user_id):
        url = '%s/jobs/%i?action=resume' % (COMPUTESERVER, job_id)
        response = requests.get(url)
        return response.json()
    raise AuthException('User %s is not authorized to resume job %s' % (str(user_id), str(job_id)))


def create_sample_creation_workflow(input_filenames, metadata):
    # generate tmpdir for this temporary workflow
    token = create_jobserver_token()
    directory = f'{TMPDIR}/{token}'
    os.mkdir(directory)
    metadata_filename = f'{directory}/metadata'
    prefix = metadata['name']
    del metadata['name']
    with open(metadata_filename, 'w') as file:
        json.dump(metadata, file)
    new_filenames = [f'{directory}/{os.path.basename(input_filename)}' for input_filename in input_filenames]
    [os.rename(input_filename, new_filename) for input_filename, new_filename in zip(input_filenames, new_filenames)]

    workflow = {
        'cwlVersion': 'v1.0',
        'class': 'Workflow',
        'inputs':
            [
                {
                    'id': 'inputFiles',
                    'type': 'File[]'
                },
                {
                    'id': 'metadataFile',
                    'type': 'File'
                },
                {
                    'id': 'dataDirectory',
                    'type': 'Directory'
                },
                {
                    'id': 'prefix',
                    'type': 'string'
                }
            ],
        'outputs':
            [
                {
                    'id': 'outputFiles',
                    'outputSource': 'update/output',
                    'type': 'File[]'
                }
            ],
        'steps':
            [
                {
                    'id': 'parse',
                    'run': metadata["parser"],
                    'in': [
                        {
                            'id': 'inputFiles',
                            'source': 'inputFiles'
                        },
                        {
                            'id': 'prefix',
                            'source': 'prefix'
                        }
                    ],
                    'out': [{'id': 'output'}]
                },
                {
                    'id': 'process',
                    'run': metadata["preproc"],
                    'in': [
                        {
                            'id': 'inputFiles',
                            'source': 'parse/output'
                        }
                    ],
                    'out': [{'id': 'output'}]
                },
                {
                    'id': 'update',
                    'run': f'{MODULEDIR}/core-modules/createcollections.cwl',
                    'in':
                        [
                            {'id': 'inputFiles',
                             'source': 'process/output'},
                            {'id': 'metadataFile',
                             'source': 'metadataFile'},
                            {'id': 'dataDirectory',
                             'source': 'dataDirectory'}
                        ],
                    'out': [{'id': 'output'}]
                }
            ]
    }
    workflow_filename = f'{directory}/workflow.cwl'
    with open(workflow_filename, 'w') as workflow_file:
        yaml.dump(workflow, workflow_file, default_flow_style=False)
    job = {
        'inputFiles': [{'path': filename, 'class': 'File'} for filename in new_filenames],
        'metadataFile': {'path': metadata_filename,
                         'class': 'File'},
        'dataDirectory': {'path': f'{DATADIR}/samples',
                          'class': 'Directory'},
        'prefix': prefix
    }
    # perhaps move execution here?
    return {'workflow_filename': workflow_filename, 'job': job, 'token': token}


def create_jobserver_token():
    token = str(uuid.uuid4())
    while token in os.listdir(f'{TMPDIR}'):
        token = uuid.uuid4()
    db.query_db('insert into JobServerTokens (value) values (?)', [str(token)])
    return token


def check_jobserver_token(token):
    return db.query_db('select * from JobServerTokens where value = ?', [str(token)]) is not None
