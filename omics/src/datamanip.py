from passlib.hash import pbkdf2_sha256
import importlib
import yaml
import os
from file_tools import metadatatools as mdt
from file_tools import h5merge
from db import db
import h5py
from xkcdpass import xkcd_password as xp

DATADIR = os.environ['DATADIR']


# TODO: raise exceptions for unauthorized
# route functions should capture exceptions from SQLite3


class AuthException(Exception):
    pass


def validate_file(path):
    return h5py.is_hdf5(path)


def is_admin(user_id):
    return db.query_db('select * from Users where rowid=? and admin=1;', [str(user_id)], True) is not None


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
    ids = [int(os.path.splitext(file)[0]) for file in os.listdir(path)]
    return 0 if ids is None else max(ids) + 1


# Create, Read, Update, Delete from db or files
# Users
def get_users():
    return db.query_db('select rowid, name, email, admin from Users;')


def get_user(user_id):
    return db.query_db('select rowid, name, email, admin from Users where rowid=?;', [str(user_id)], True)


def get_user_by_email(email):
    return db.query_db('select rowid, name, email, admin from Users where email=?;', [str(email)], True)


def get_user_password_hash(email):
    return db.query_db('select password from Users where email=?;', [str(email)], True)


def create_user(current_user_id, data):
    if is_admin(current_user_id):
        # check email
        if len(db.query_db('select * from Users where email=?', [data['email']])):
            raise ValueError('This email is already in use!')
        db.query_db('insert into Users (name, email, admin, password) values (?, ?, ?, ?);',
                    [str(data['name']), str(data['email']), str(data['admin']), pbkdf2_sha256.hash(data['password'])])
        return db.query_db('select rowid, name, email, admin from Users where rowid=last_insert_rowid()', (), True)
    raise AuthException('must be admin to create user')


def register_user(invitation_string, data):
    # check email
    if len(db.query_db('select * from Users where email=?;', [data['email']])):
        raise ValueError('This email is already in use!')
    if len(db.query_db('select * from Invitations where value=?;', [invitation_string], True)):
        db.query_db('insert into Users (name, email, admin, password) values (?, ?, ?, ?)',
                    [str(data['name']), str(data['email']), '0', pbkdf2_sha256.hash(data['password'])])
        db.query_db('delete from Invitations where value=?;', [invitation_string])
        return db.query_db('select rowid, name, email, admin from Users where rowid=last_insert_rowid()', (), True)
    raise ValueError('Incorrect invitation')


def update_user(current_user_id, target_user_id, new_data):
    if (current_user_id == target_user_id) or is_admin(current_user_id):
        # if new password provided, hash it
        if 'password' in new_data:
            new_data['password'] = pbkdf2_sha256.hash(new_data['password'])
            print(new_data)
        if 'email' in new_data:
            emails = db.query_db('select * from Users where email=?', [new_data['email']])
            if len(emails):
                raise ValueError('This email is already in use!')
        valid_keys = ['name', 'email', 'admin', 'password']
        query = 'update Users set' + ','.join([' %s = ?' % key for key in new_data.keys() if key in valid_keys]) \
                + ' where rowid=?;'
        print('query: %s' % query)
        params = []
        [params.append(str(value)) for key, value in new_data.items() if key in valid_keys]
        params.append(target_user_id)
        print('params: %s' % str(params))
        db.query_db(query, params)
        return db.query_db('select rowid, name, email, admin from Users where rowid=?;', [str(target_user_id)], True)

    raise AuthException('User %s does not have permissions to edit user %s' % (str(current_user_id), str(target_user_id)))


def delete_user(current_user_id, target_user_id):
    if (current_user_id == target_user_id) or is_admin(current_user_id):
        # delete user from users table and nullify all the ids set based on this user
        db.query_db('delete from Users where rowid=?;', str(target_user_id))
        db.query_db('update GroupMemberships set userId=null where userId=?;', [str(target_user_id)])
        db.query_db('update UserGroups set createdBy=null where createdBy=?;', [str(target_user_id)])
        db.query_db('update UserGroups set createdBy=null where createdBy=?;', [str(target_user_id)])
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


def parse_sample(user_id, infilename, parser_name):
    # find acceptable out file name
    sample_id = get_next_id(DATADIR + '/samples')
    outfilename = DATADIR + '/samples/' + str(sample_id) + '.h5'
    with open(DATADIR + '/modules/file_parsers/file_parsers.yml', 'r') as stream:
        parsers = yaml.load(stream) # can raise exception
    parser_data = [parser for parser in parsers if parsers['name'] == parser_name]
    if len(parser_data) == 0:
        raise Exception('parser %s does not exist' % parser_name)
    if len(parser_data) > 1:
        raise Exception('file_parsers.yml is invalid (multiple parsers with same name)')
    # execute file parser script
    # this can raise exceptions, which the master exception handler should translate to status code
    parser = importlib.import_module(DATADIR + '/modules/file_parsers/' + parser_data[0]['script'])
    return get_sample(user_id, sample_id)


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
        new_filename = DATADIR + '/collections/' + str(get_next_id(DATADIR + '/collections/')) + '.h5'
        # user can add any arbitrary valid JSON to a collection
        # if it gets to this point, it has already been validated!
        mdt.update_metadata(filename, new_data)
        new_data = {} if new_data is None else new_data
        new_data['createdBy'] = user_id
        new_data['owner'] = user_id
        mdt.update_metadata(filename, new_data)
        os.rename(filename, new_filename)
        return mdt.get_collection_metadata(new_filename)
    raise Exception('file not valid')


# verifies permissions of user to download a collection, returns a filename or a message
def download_collection(user_id, collection_id):
    filename = '%s/collections/%s.h5' % (DATADIR, str(collection_id))
    collection = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, collection):
        return {'filename': '%s.h5' % str(collection_id)}
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(collection_id)))


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


def create_collection(user_id, sample_ids, new_data):
    outfilename = DATADIR + '/collections/' + str(get_next_id('/data/collections')) + '.h5'
    filenames = [DATADIR + '/samples/' + str(sample_id) for sample_id in sample_ids]
    for filename in filenames:
        if not is_read_permitted(user_id, mdt.get_collection_metadata(filename)):
            raise AuthException('User %s is not permitted to access file %s' % (str(user_id), str(filename)))
    h5merge.h5_merge(filenames, outfilename)
    return mdt.update_metadata(outfilename, new_data)


def delete_collection(user_id, collection_id):
    collection_info = mdt.get_collection_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_write_permitted(user_id, collection_info):
        os.remove(DATADIR + '/collections/' + str(collection_id) + '.h5')
        return {'message': 'collection ' + str(collection_id) + ' removed'}
    raise AuthException('User %s not authorized to modify collection %s' % (str(user_id), str(collection_id)))


# TODO: workflows
# workflows are defined in YAML files in DATADIR +workflows
# these yaml files define inputs and outputs
def get_workflows(user_id):
    return []


def get_workflow(user_id, workflow_id):
    return {}


def update_workflow(user_id, workflow_id, new_data):
    return {}


def delete_workflow(user_id, workflow_id):
    return {}


def create_workflow(user_id, data):
    return {}


# analyses
def get_analyses(user_id):
    results = db.query_db('select * from Analyses;')
    return [result for result in results if is_read_permitted(user_id, result)]


def get_analysis(user_id, analysis_id):
    result = db.query_db('select * from Analyses where rowid=?;', [str(analysis_id)], True)
    if is_read_permitted(user_id, result):
        return result
    raise AuthException('User %s is not permitted to access analysis %s' % (str(user_id), str(analysis_id)))


def update_analysis(user_id, analysis_id, new_data):
    analysis = db.query_db('select * from Analyses where rowid=?;', str(analysis_id), True)
    valid_keys = ['name', 'description', 'createdBy', 'groupPermissions', 'allPermissions', 'userGroup']
    if is_write_permitted(user_id, analysis):
        query = 'update Analyses set ' \
                + ','.join([' %s = ?' % key for key, value in new_data.items() if key in valid_keys]) \
                + ' where rowid=?;'
        params = []  # TODO: validate params against schema
        [params.append(str(value)) for value in new_data.values()]
        params.append(str(analysis_id))
        db.query_db(query, params)
        return db.query_db('select * from Analyses where rowid=?;', [str(analysis_id)], True)
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(analysis_id)))


def create_analysis(user_id, data):
    db.query_db('insert into Analyses (name, description, createdBy, groupPermissions, allPermissions, userGroup) '
                + 'values (?, ?, ?, ?, ?, ?);',
                [str(data['name']), str(data['description']), str(user_id), str(data['groupPermissions']),
                 str(data['allPermissions']), str(data['userGroup'])],
                True)
    return db.query_db('select rowid, * from Analyses where rowid=last_insert_rowid()', (), True)


def delete_analysis(user_id, analysis_id):
    analysis = db.query_db('select * from Analysis where rowid=?;', str(analysis_id), True)
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from Analysis where rowid=?;', [str(analysis_id)])
        return {'message': 'analysis ' + str(analysis_id) + ' deleted'}
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(analysis_id)))


def attach_collection(user_id, analysis_id, collection_id):
    # check read permissions on analysis and collection
    analysis = db.query_db('select * from Analyses where rowid=?;', str(analysis_id), True)
    collection = mdt.get_collection_metadata(DATADIR + 'collections/' + str(collection_id) + '.h5')
    if is_write_permitted(user_id, collection) and is_write_permitted(user_id, analysis):
        # see if attached
        if db.query_db('select * from CollectionMemberships where analysisId=? and collectionId=?;',
                       [str(analysis_id), str(collection_id)]) is None:
            db.query_db('insert into CollectionMemberships (collectionId, analysisId) values (?,?);',
                        [str(analysis_id), str(collection_id)])
        return {'message': 'collection ' + str(collection_id) + ' attached to analysis ' + str(analysis_id)}
    raise AuthException('User %s is not permitted to attach collection %s to analysis %s' % (str(user_id), str(collection_id), str(analysis_id)))


def detach_collection(user_id, analysis_id, collection_id):
    analysis = db.query_db('select * from Analyses where rowid=?;', str(analysis_id), True)
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from CollectionMemberships where collectionId=? and analysisId=?;',
                 [str(collection_id), str(analysis_id)])
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(analysis_id)))


# user groups
# user groups do not have permissions for viewing
def get_user_groups():
    return db.query_db('select * from UserGroups;')


def get_user_group(group_id):
    return db.query_db('select * from UserGroups where rowid=?;', [str(group_id)], True)


def create_user_group(user_id, data):
    db.query_db('insert into UserGroups (createBy, name, description) values (?, ?, ?);',
             [str(user_id), str(data.name), str(data.description)],
             True)
    new_group = db.query_db('select * from UserGroups order by rowid desc limit 1;', (), True)
    db.query_db('insert into GroupMemberships (userId, groupMembership, admin) values(?, ?, ?);',
             [str(user_id), str(new_group.rowid), '1'])
    return new_group


def update_user_group(user_id, group_id, new_data):
    if is_group_admin(user_id, group_id):
        valid_keys = ['name', 'description']
        query = 'update UserGroups set' + ','.join([' ? = ?' for key in new_data.keys if key in valid_keys]) + ' where rowid=?;'
        params = []
        [ params.extend([str(key), str(value)]) for key, value in new_data.items() if key in valid_keys ]
        params.append(str(group_id))
        db.query_db(query, params)
        return db.query_db('select * from UserGroups where rowid=?;', [str(group_id)], True)
    raise AuthException('User %s is not authorized to modify user group %s' % (str(user_id), str(group_id)))


def attach_user(current_user_id, target_user_id, group_id):
    if is_group_admin(current_user_id, group_id):
        if not user_in_group(target_user_id, group_id):
            db.query_db('insert into GroupMemberships (userId, groupMembership, admin) values (?, ?, ?);',
                     [str(target_user_id), str(group_id), '0'])
            return db.query_db('select * from UserGroups order by rowid desc limit 1;', (), True)
        return {'message': 'user ' + target_user_id + ' attached to group ' + str(group_id)}
    raise AuthException('User %s is not authorized to attach user %s to group %s' % (str(current_user_id), str(target_user_id), str(group_id)))


def elevate_user(current_user_id, target_user_id, group_id):
    if is_group_admin(current_user_id, group_id):
        db.query_db('update GroupMemberships set groupAdmin=1 where rowid=?;', [str(target_user_id)])
        return {'message': 'User %s elevated to admin of group %s' % (str(target_user_id), str(group_id))}
    raise AuthException('User %s not authorized to modify group %s' % (str(current_user_id), str(group_id)))


def detach_user(current_user_id, target_user_id, group_id):
    if target_user_id == current_user_id or is_group_admin(current_user_id, group_id):
        db.query_db('delete from GroupMemberships where userId=? and groupMembership=?;',
                 [str(target_user_id), str(group_id)])
        return {'message': 'user ' + str(target_user_id) + ' detached from group ' + str(group_id)}
    raise AuthException('User %s not permitted to modify group %s' % (str(current_user_id), str(group_id)))


def delete_user_group(user_id, group_id):
    if is_group_admin(user_id, group_id):
        db.query_db('delete from UserGroups where rowid=?;', [str(group_id)])
        return {'message': 'user group ' + str(group_id) + ' deleted'}
    raise AuthException('User %s not permitted to modify group %s' % (str(user_id), str(group_id)))


def create_invitation(user_id):
    if is_admin(user_id):
        invite_string = xp.generate_xkcdpassword(xp.generate_wordlist(valid_chars='[a-z]'), numwords=3, delimiter='_')
        db.query_db('insert into Invitations (createdBy, value) values (?,?);', [str(user_id), invite_string])
        return db.query_db('select rowid, * from Invitations where rowid=last_insert_rowid();', (), True)
