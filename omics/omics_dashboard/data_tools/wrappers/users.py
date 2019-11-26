import datetime
import os
from typing import List, Dict, Any

import jwt
from xkcdpass import xkcd_password as xp

from data_tools.db_models import User, UserGroup, UserInvitation, db, OmicsRecordMixin
from data_tools.util import AuthException, NotFoundException


def get_all_users() -> List[User]:
    """
    Get a list of all users
    :return:
    """
    return [user for user in User.query.all()]


def get_users(user: User) -> List[User]:
    """
    Get a list of all users
    :return:
    """
    return get_all_read_permitted_records(user, User)


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
    if 'id' in data:  # cannot create with specified id
        del data['id']
    if current_user.admin:
        if User.query.filter_by(email=data['email']).count():
            raise ValueError('This email is already in use!')
        new_user = User(email=data['email'], name=data['name'], admin=data['admin'],
                        password=User.hash_password(data['password']), active=True)
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
                    active=True, password=User.hash_password(data['password']))
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
        if 'id' in new_data:
            if target_user.id != int(new_data['id']) and User.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'User with id {new_data["id"]} already exists!')
        # if new password provided, hash it
        if 'email' in new_data:
            email_count = User.query.filter_by(email=new_data['email']).count
            if email_count:
                raise ValueError('This email is already in use!')
        if 'user_group_ids' in new_data:
            from data_tools.wrappers.user_groups import get_user_group
            new_data['user_group_ids'] = [int(user_group_id) for user_group_id in new_data['user_group_ids']]
            new_user_groups = [get_user_group(current_user, user_group_id) for user_group_id in
                               new_data['user_group_ids']]
            remove_user_groups = [user_group for user_group in current_user.user_groups if
                                  user_group.id not in new_data['user_group_ids']]
            for user_group in new_user_groups:
                if not is_write_permitted(current_user, user_group):
                    raise AuthException(f'User {current_user.email} is not permitted to attach user {target_user.id} to user group {user_group.id}')
            for user_group in remove_user_groups:
                if not is_write_permitted(current_user, user_group):
                    raise AuthException(f'User {current_user.email} is not permitted to detach user {target_user.id} from user group {user_group.id}')
            target_user.user_groups = new_user_groups
        for key, value in new_data.items():
            if key == 'password':
                target_user.password = User.hash_password(value)
            elif key == 'active' and current_user.admin:
                target_user.active = value
            elif key == 'admin' and current_user.admin:
                target_user.admin = value
            # note that if you want to make a user an admin of a user group, do it by editing the user group
            elif key in target_user.to_dict() and key not in {'password', 'active', 'admin', 'admin_group_ids',
                                                              'group_ids'}:
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
    if user is None or not user.check_password(password):
        raise AuthException('Invalid username/password.')
    return user


def get_jwt_by_email(email: str, password: str) -> str:
    """
    Authenticate a user and get a JSON Web Token for them
    :param email:
    :param password:
    :return:
    """
    user_data = validate_login(email, password).to_dict()
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
    Use get_all_read_permitted_records instead if you want to filter all records in existence,
    This is best for smaller collections of records
    TODO: Do this at the query level instead of on all()
    :param user:
    :param records:
    :return:
    """
    return [record for record in records if record.read_permitted(user)]


def get_all_read_permitted_records(user: User, model: db.Model, filter_by: Dict[str, Any] = None):
    """
    Get all of the records of the model model which the user is allowed to read.
    This should be used in place of get_read_permitted_records when you need to filter
    all records of a particular kind because it uses a db query that only loads the returned records
    :param user:
    :param model:
    :param filter_by: A dictionary to filter on.
    :return:
    """
    query = model.query.filter_by(**filter_by) if filter_by is not None else model.query
    if issubclass(model, OmicsRecordMixin):
        return query.filter((model.owner_id == user.id) | model.all_can_read |
                            (model.group_can_read & model.user_group_id.in_(
                                [user_group.id for user_group in user.user_groups])))
    else:
        # argh ORMs
        # query database (all_can_read is a property of User and UserGroup classes, not a table)
        entries = query.filter((model.owner_id == user.id) | model.all_can_read |
                               (model.user_group_id.in_([user_group.id for user_group in user.user_groups])))
        # filter results
        return [
            entry for entry in entries
            if (entry.owner_id == user.id
                or entry.all_can_read
                or (entry.group_can_read and entry.user_group_id in [user_group.id for user_group in user.user_groups]))
        ]


def get_user_name(user: User):
    return user.name


def get_mailto(users: List[User]):
    return f'mailto:{",".join([user.email for user in users])}'


def get_mailto_all():
    return get_mailto([user for user in User.query.all()])


def get_mailto_group(user_group: UserGroup):
    return get_mailto([user for user in user_group.members])
