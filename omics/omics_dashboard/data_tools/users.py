import datetime
import os

import jwt
from typing import List, Dict, Any

from data_tools.util import AuthException, DATADIR
import data_tools.file_tools.metadata_tools as mdt
import data_tools.database.db as db
import bcrypt
from xkcdpass import xkcd_password as xp


def hash_password(password: str) -> str:
    """
    Hash a password using bcrpyt and get the hasehd password as a str
    :param password:
    :return:
    """
    return bcrypt.hashpw(bytes(password, 'utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password: str, hashed_password: str) -> bool:
    """
    Check the presented password against a hashed password
    :param password:
    :param hashed_password:
    :return:
    """
    return bcrypt.checkpw(bytes(password, 'utf-8'), bytes(hashed_password, 'utf-8'))


def get_users() -> List[Dict]:
    """
    Get a list of all users
    :return:
    """
    return db.query_db('select id, name, email, admin from Users;')


def get_user(user_id: int) -> Dict:
    """
    Get the record for one user
    :param user_id:
    :return:
    """
    return db.query_db('select id, name, email, admin from Users where rowid=?;', [str(user_id)], True)


def get_user_by_email(email: str) -> Dict:
    """
    Get the user record for a user based on their email address
    :param email:
    :return:
    """
    return db.query_db('select id, name, email, admin from Users where email=?;', [str(email)], True)


def get_user_password_hash(email: str) -> str:
    """
    Get the password hash for a user based on their email address
    :param email:
    :return:
    """
    return db.query_db('select password from Users where email=?;', [str(email)], True)['password']


def create_user(current_user_id: int, data: Dict) -> Dict:
    """
    Create a new user
    :param current_user_id:
    :param data:
    :return:
    """
    if is_admin(current_user_id):
        # check email
        if len(db.query_db('select * from Users where email=?', [data['email']])):
            raise ValueError('This email is already in use!')
        db.query_db('insert into Users (name, email, admin, password) values (?, ?, ?, ?);',
                    [str(data['name']), str(data['email']), str(data['admin']), hash_password(data['password'])])
        return db.query_db('select id, name, email, admin from Users where id=last_insert_rowid()', (), True)
    raise AuthException('must be admin to create user')


def register_user(invitation_string: str, data: Dict) -> Dict[str, Any]:
    """
    Create a new user from their registration code
    :param invitation_string:
    :param data:
    :return:
    """
    if len(db.query_db('select * from Users where email=?;', [data['email']])):
        raise ValueError('This email is already in use!')
    if len(db.query_db('select * from Invitations where value=?;', [invitation_string], True)):
        db.query_db('insert into Users (name, email, admin, password) values (?, ?, ?, ?)',
                    [str(data['name']), str(data['email']), '0', hash_password(data['password'])])
        db.query_db('delete from Invitations where value=?;', [invitation_string])
        return db.query_db('select id, name, email, admin from Users where id=last_insert_rowid()', (), True)
    raise ValueError('Incorrect invitation')


def update_user(current_user_id: int, target_user_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Change the values in the user record to match the information provided in new_data
    :param current_user_id:
    :param target_user_id:
    :param new_data:
    :return:
    """
    if (current_user_id == target_user_id) or is_admin(current_user_id):
        # if new password provided, hash it
        if 'password' in new_data:
            new_data['password'] = hash_password(new_data['password'])
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
    raise AuthException(f'User {current_user_id} does not have permissions to edit user {target_user_id}')


def delete_user(current_user_id: int, target_user_id: int) -> Dict[str, str]:
    """
    Delete the user records and remove the user from all user groups. All user id fields with this user id as values
    are set to null.
    :param current_user_id:
    :param target_user_id:
    :return:
    """

    from data_tools.samples import get_all_samples
    from data_tools.collections import get_all_collections
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
        filenames = [
            f'{DATADIR}/samples/{sample["id"]}.h5' for sample in samples if str(sample['owner']) == str(target_user_id)
        ]
        filenames.extend([
            f'{DATADIR}/collections/{collection["id"]}.h5' for collection in collections
            if str(collection['owner']) == str(target_user_id)
        ])
        [mdt.update_metadata(filename, {'owner': -1}) for filename in filenames]
        filenames = [
            f'{DATADIR}/samples/{sample["id"]}.h5' for sample in samples
            if str(sample['createdBy']) == str(target_user_id)
        ]
        filenames.extend([
            f'{DATADIR}/collections/{collection["id"].h5}' for collection in collections
            if str(collection['createdBy']) == str(target_user_id)
        ])
        [mdt.update_metadata(filename, {'createdBy': -1}) for filename in filenames]

        return {'message': f'user {target_user_id} deleted'}
    raise AuthException(f'User {current_user_id} does not have permissions to delete user {target_user_id}')


def create_invitation(user_id: int) -> Dict[str, Any]:
    """
    Create an invitation string for a new user. The user_id most correspond to an admin user
    :param user_id:
    :return:
    """
    if is_admin(user_id):
        invite_string = xp.generate_xkcdpassword(xp.generate_wordlist(valid_chars='[a-z]'), numwords=3, delimiter='_')
        db.query_db('insert into Invitations (createdBy, value) values (?,?);', [str(user_id), invite_string])
        return db.query_db('select * from Invitations where id=last_insert_rowid();', (), True)


def validate_login(email: str, password: str) -> bool:
    """
    Authenticate a user
    :param email:
    :param password:
    :return:
    """
    pwhash = get_user_password_hash(email)
    if pwhash is None or not check_password(password, pwhash):
        raise ValueError('Invalid username/password')
    return True


def get_jwt(email: str, password: str) -> str:
    """
    Authenticate a user and get a JSON Web Token for them
    :param email:
    :param password:
    :return:
    """
    validate_login(email, password)
    user = get_user_by_email(email)
    user['exp'] = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    return jwt.encode(user, os.environ['SECRET'], algorithm='HS256').decode('utf-8')


def get_jwt_by_id(user_id: int) -> str:
    """
    Get a JSON Web Token for the user with user_id (user should be authenticated elsewhere
    :param user_id:
    :return:
    """
    user = get_user(user_id)
    user['exp'] = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    return jwt.encode(user, os.environ['SECRET'], algorithm='HS256').decode('utf-8')


def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin (to the overall system
    :param user_id:
    :return:
    """
    return db.query_db('select * from Users where id=? and admin=1;', [str(user_id)], True) is not None


def user_in_user_group(user_id: int, group_id: int) -> bool:
    """
    Check if a user is in a user group
    :param user_id:
    :param group_id:
    :return:
    """
    return (db.query_db('select * from GroupMemberships where userId=? and groupId=?;',
                        [str(user_id), str(group_id)], True)
            is not None)


def is_user_group_admin(user_id: int, group_id: int) -> bool:
    """
    Check if a user is an admin of a user group
    :param user_id:
    :param group_id:
    :return:
    """
    return (db.query_db('select * from GroupMemberships where userId=? and groupId=? and groupAdmin=1;',
                        [str(user_id), str(group_id)], True)
            is not None)


def is_read_permitted(user_id: int, record: Dict[str, Any]) -> bool:
    """
    Check if a user is allowed to read from this record. A user is allowed to read from a record if they are
    1. The user is the owner of the record
    2. The user is a member of the user group associated with the record with the user group
       permitted to read the record
    3. All users are permitted to read the record
    :param user_id:
    :param record:
    :return:
    """
    return 'owner' in record and record['owner'] == user_id \
        or is_admin(user_id) \
        or record['allPermissions'] == 'readonly'  \
        or record['allPermissions'] == 'full' \
        or ((record['groupPermissions'] == 'readonly'
            or record['groupPermissions'] == 'full') and user_in_user_group(user_id, record['userGroup']))


def is_write_permitted(user_id: int, record: Dict) -> bool:
    """
    Check if a record can be read by a user
    :param user_id:
    :param record:
    :return:
    """
    return 'owner' in record and record['owner'] == user_id \
        or 'email' in record and record['id'] == user_id \
        or is_admin(user_id) \
        or record['allPermissions'] == 'full' \
        or (record['groupPermissions'] == 'full' and user_in_user_group(user_id, record['userGroup']))


def get_read_permitted_records(user_id: int, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get all the records in the list records which the user is allowed to read
    :param user_id:
    :param records:
    :return:
    """
    return [record for record in records if is_read_permitted(user_id, record)]


def get_user_name(user_id):
    return get_user(user_id)['name']
