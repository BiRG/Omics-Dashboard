import datetime
import os

import jwt
from typing import List, Dict, Any

from data_tools.util import AuthException, DATADIR
import bcrypt
from xkcdpass import xkcd_password as xp
from data_tools.db import User, UserGroup, Invitation, Base, db
from flask_sqlalchemy import Model


def hash_password(password: str) -> str:
    """
    Hash a password using bcrpyt and get the hashed password as a str
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


def get_all_users() -> List[User]:
    """
    Get a list of all users
    :return:
    """
    return [user for user in User.query.all()]
    # return db.query_db('select id, name, email, admin from Users;')


def get_users(user: User) -> List[User]:
    """
    Get a list of all users
    :return:
    """
    return get_read_permitted_records(user, User.query.all())
    # return db.query_db('select id, name, email, admin from Users;')


def get_user(user: User, target_user_id: int) -> User:
    """
    Get the record for one user
    :param user:
    :param target_user_id:
    :return:
    """
    target_user = User.query.filter_by(id=target_user_id).first()
    if is_read_permitted(user, target_user):
        return target_user
    raise AuthException(f'User with id {target_user_id} does not exist or is not visible to {user.email}')


def get_user_by_email(email: str) -> User:
    """
    Get the user record for a user based on their email address
    :param email:
    :return:
    """
    return User.query.filter_by(email=email).first()


def get_user_password_hash(email: str) -> str:
    """
    Get the password hash for a user based on their email address
    :param email:
    :return:
    """
    return User.query.filter_by(email=email).first().password


def create_user(current_user: User, data: Dict[str, Any]) -> User:
    """
    Create a new user
    :param current_user:
    :param data:
    :return:
    """
    if current_user.admin:
        if User.query.filter_by(email=data['email']).count():
            raise ValueError('This email is already in use!')
        new_user = User(email=data['email'], name=data['name'], admin=data['admin'],
                        password=hash_password(data['password']), active=True)
        db.session.add(new_user)
        db.session.commit()
        return new_user
    raise AuthException('must be admin to create user')


def register_user(invitation_string: str, data: Dict) -> User:
    """
    Create a new user from their registration code
    :param invitation_string:
    :param data:
    :return:
    """
    if User.query.filter_by(email=data['email']).count():
        raise ValueError('This email is already in use!')
    invitation = Invitation.query.filter_by(value=invitation_string).first()
    if invitation is not None:
        user = User(email=data['email'], name=data['name'], admin=data['admin'],
                    active=True, password=hash_password(data['password']))
        db.session.add(user)
        db.session.delete(invitation)
        db.commit()
        return user
    raise ValueError('Incorrect invitation')


def update_user(current_user: User, target_user: User, new_data: Dict[str, Any]) -> User:
    """
    Change the values in the user record to match the information provided in new_data
    :param current_user:
    :param target_user:
    :param new_data:
    :return:
    """
    if current_user is target_user or current_user.admin:
        # if new password provided, hash it
        if 'email' in new_data:
            email_count = User.query.filter_by(email=new_data['email']).count
            if email_count:
                raise ValueError('This email is already in use!')
        for key, value in new_data.items():
            if key == 'name':
                target_user.name = value
            if key == 'email':
                target_user.email = value
            if key == 'admin':
                target_user.admin = value
            if key == 'password':
                target_user.password = hash_password(value)
        db.session.commit()
        return target_user
    raise AuthException(f'User {current_user.email} does not have permissions to edit user {target_user.email}')


def delete_user(current_user: User, target_user: User) -> Dict[str, Any]:
    """
    Delete the user records and remove the user from all user groups. All user id fields with this user id as values
    are set to null.
    :param current_user:
    :param target_user:
    :return:
    """
    if current_user is target_user or current_user.admin:
        # deletion will cascasde without worry
        db.session.delete(target_user)
        db.session.commit()
        return {'message': f'user {target_user.email} deleted'}
    raise AuthException(f'User {current_user.email} does not have permissions to delete user {target_user.email}')


def create_invitation(user: User) -> Invitation:
    """
    Create an invitation string for a new user. The user_id most correspond to an admin user
    :param user:
    :return:
    """
    if user.admin:
        invite_string = xp.generate_xkcdpassword(xp.generate_wordlist(valid_chars='[a-z]'), numwords=3, delimiter='_')
        invitation = Invitation(creator_id=user.id, value=invite_string)
        db.session.add(invitation)
        db.session.commit()
        return invitation
    raise AuthException(f'User {user.email} is not an administrator and cannot invite other users.')


def validate_login(email: str, password: str) -> User:
    """
    Authenticate a user
    :param email:
    :param password:
    :return:
    """
    user = User.query.filter_by(email=email).first()
    if User is None or not check_password(password, user.password):
        raise ValueError('Invalid username/password')
    return user


def get_jwt_by_email(email: str, password: str) -> str:
    """
    Authenticate a user and get a JSON Web Token for them
    :param email:
    :param password:
    :return:
    """
    validate_login(email, password)
    user_data = User.query.filter_by(email=email).first().to_dict()
    user_data['exp'] = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    return jwt.encode(user_data, os.environ['SECRET'], algorithm='HS256').decode('utf-8')


def get_jwt(user: User) -> str:
    """
    Get a JSON Web Token for the user with user_id (user should be authenticated elsewhere
    :param user:
    :return:
    """
    user_data = user.to_dict()
    user_data['exp'] = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    return jwt.encode(user, os.environ['SECRET'], algorithm='HS256').decode('utf-8')


def user_in_user_group(user: User, group: UserGroup) -> bool:
    """
    Check if a user is in a user group
    :param user:
    :param group:
    :return:
    """
    return user in group.members


def is_user_group_admin(user: User, group: UserGroup) -> bool:
    """
    Check if a user is an admin of a user group
    :param user:
    :param group:
    :return:
    """
    return user in group.admins


def is_read_permitted(user: User, record: Any) -> bool:
    """
    Check if a user is allowed to read from this record. A user is allowed to read from a record if they are
    1. The user is the owner of the record
    2. The user is a member of the user group associated with the record with the user group
       permitted to read the record
    3. All users are permitted to read the record
    :param user:
    :param record:
    :return:
    """
    return user.admin or (record.group_can_read and user in record.user_group.members) or record.all_can_read


def is_write_permitted(user: User, record: Any) -> bool:
    """
    Check if a record can be read by a user
    :param user:
    :param record:
    :return:
    """
    return user.admin or user.id is record.owner_id \
           or (record.group_can_write and user in record.user_group.members) \
           or record.all_can_write


def get_read_permitted_records(user: User, records: List[Any]) -> List[Any]:
    """
    Get all the records in the list records which the user is allowed to read
    :param user:
    :param records:
    :return:
    """
    return [record for record in records if is_read_permitted(user, record)]


def get_user_name(user: User):
    return user.name
