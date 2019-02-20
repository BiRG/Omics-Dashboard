import datetime
import os

import jwt
from typing import List, Dict, Any, Type

from data_tools.util import AuthException, NotFoundException, DATADIR
import bcrypt
from xkcdpass import xkcd_password as xp
from data_tools.db import User, UserGroup, UserInvitation, Base, db
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
    return get_all_read_permitted_records(user, User)
    # return db.query_db('select id, name, email, admin from Users;')


def get_user(user: User, target_user_id: int) -> User:
    """
    Get the record for one user
    :param user:
    :param target_user_id:
    :return:
    """
    target_user = User.query.filter_by(id=target_user_id).first()
    if target_user is None:
        raise NotFoundException(f'No user with id {target_user_id}.')
    if is_read_permitted(user, target_user):
        return target_user
    raise AuthException(f'User with id {target_user_id} does not exist or is not visible to {user.email}')


def get_user_by_email(email: str) -> User:
    """
    Get the user record for a user based on their email address
    :param email:
    :return:
    """
    user = User.query.filter_by(email=email).first()
    if user is None:
        raise NotFoundException(f'No user with email {email}')
    return user


def get_user_password_hash(email: str) -> str:
    """
    Get the password hash for a user based on their email address
    :param email:
    :return:
    """
    user = User.query.filter_by(email=email).first()
    if user is None:
        raise NotFoundException(f'No user with email {email}.')
    return user.password


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
    invitation = UserInvitation.query.filter_by(value=invitation_string).first()
    if invitation is not None:
        user = User(email=data['email'], name=data['name'], admin=data['admin'],
                    active=True, password=hash_password(data['password']))
        if invitation.primary_user_group is not None:
            user.primary_user_group = invitation.primary_user_group
            user.user_groups = [invitation.primary_user_group]
            user.admin_user_groups = []
        db.session.add(user)
        db.session.delete(invitation)
        db.session.commit()
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
            if key == 'password':
                target_user.password = hash_password(value)
            elif key in target_user.to_dict():
                target_user.__setattr__(key, value)
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


def create_invitation(user: User, primary_user_group: UserGroup=None) -> UserInvitation:
    """
    Create an invitation string for a new user. The user_id most correspond to an admin user
    :param user:
    :param primary_user_group:
    :return:
    """
    if user.admin:
        invite_string = xp.generate_xkcdpassword(xp.generate_wordlist(valid_chars='[a-z]'), numwords=3, delimiter='_')
        invitation = UserInvitation(creator=user, primary_user_group=primary_user_group, value=invite_string)
        db.session.add(invitation)
        db.session.commit()
        return invitation
    raise AuthException(f'User {user.email} is not an administrator and cannot view or edit invitations.')


def get_invitations(user: User):
    if user.admin:
        return UserInvitation.query.all()
    raise AuthException(f'User {user.email} is not an administrator and cannot view or edit invitations.')


def get_invitation(user: User, invitation_id: int) -> UserInvitation:
    if user.admin:
        return UserInvitation.query.filter_by(id=invitation_id)
    raise AuthException(f'User {user.email} is not an administrator and cannot view or edit invitations.')


def delete_invitation(user: User, invitation: UserInvitation) -> Dict[str, str]:
    if user.admin:
        db.session.remove(invitation)
        db.session.commit()
        return {'message': f'Invitation {invitation.id} removed.'}
    raise AuthException(f'User {user.email} is not an administrator and cannot view or edit invitations.')


def validate_login(email: str, password: str) -> User:
    """
    Authenticate a user
    :param email:
    :param password: password in plaintext
    :return:
    """
    user = User.query.filter_by(email=email).first()
    if user is None or not check_password(password, user.password):
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
    return jwt.encode(user_data, os.environ['SECRET'], algorithm='HS256').decode('utf-8')


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
    return user.admin or (user in group.admins)


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
    #  TODO: All of this stuff should be done with DB queries rather than loading all elements in memory first
    if record is None:
        return False
    elif user.admin or record.all_can_read or record.owner_id == user.id:
        return True
    elif not hasattr(record, 'user_group') or hasattr(record, 'user_group') and record.user_group is None:
        return False
    return record.group_can_read and user in record.user_group.members


def is_write_permitted(user: User, record: Any) -> bool:
    """
    Check if a record can be read by a user
    :param user:
    :param record:
    :return:
    """
    if record is None:
        return False
    elif user.admin or record.all_can_write or record.owner_id == user.id:
        return True
    elif not hasattr(record, 'user_group') or hasattr(record, 'user_group') and record.user_group is None:
        return False
    return record.group_can_write and (user in record.user_group.members)


def get_read_permitted_records(user: User, records: List[Any]) -> List[Any]:
    """
    Get all the records in the list records which the user is allowed to read
    Use get_all_read_permitted_records instead if you want to filter all records in existance,
    This is best for smaller collections of records
    TODO: Do this at the query level instead of on all()
    :param user:
    :param records:
    :return:
    """
    return [record for record in records if is_read_permitted(user, record)]


def get_all_read_permitted_records(user: User, model: db.Model):
    """
    Get all of the records of the model model which the user is allowed to read.
    This should be used in place of get_read_permitted_records when you need to filter
    all records of a particular kind because it uses a db query that only loads the returned records
    :param user:
    :param model:
    :return:
    """
    if user.admin:
        return model.query.all()
    else:
        return model.query.filter(model.all_can_read or (model.group_can_read and user.in_(model.user_group.members))).all()


def get_user_name(user: User):
    return user.name
