from data_tools.util import AuthException
from data_tools.users import is_user_group_admin, get_read_permitted_records
from data_tools.db import User, UserGroup, db
from typing import List, Dict, Any


def get_all_user_groups() -> List[UserGroup]:
    """
    Get a list of all user groups.
    :return:
    """
    return UserGroup.query.all()


def get_user_groups(user: User) -> List[UserGroup]:
    """
    Get a list of all user groups readable by user.
    :return:
    """
    return get_read_permitted_records(user, UserGroup.query.all())


def get_user_group(user: User, user_group_id: int) -> UserGroup:
    """
    Get a user group.
    :param user
    :param user_group_id:
    :return:
    """
    user_group = UserGroup.query.filter_by(id=user_group_id)
    if user_group.all_can_read or user in user_group.members:
        return user_group


def get_user_group_name(user_group_id: int) -> str:
    """
    Get just the name, used by templates.
    Should deprecate soon.
    :param user_group_id:
    :return:
    """
    return UserGroup.query.filter_by(id=user_group_id).first().name


def create_user_group(user: User, data: Dict[str, Any]) -> UserGroup:
    """
    Create a new user group.
    :param user:
    :param data:
    :return:
    """
    user_group = UserGroup(owner_id=user.id, creator_id=user.id)
    db.session.add(user_group)
    db.commit()
    update_user_group(user, user_group, data)
    return user_group


def update_user_group(user: User, user_group: UserGroup, new_data: Dict[str, Any]) -> UserGroup:
    """
    Update the user groups information.
    :param user:
    :param user_group:
    :param new_data:
    :return:
    """
    if is_user_group_admin(user, user_group):
        for key, value in new_data.items():
            if key in user_group.to_dict():
                user_group.__setattr__(key, value)
        db.session.commit()
        return user_group
    raise AuthException(f'User {user.email} is not authorized to modify user group {user_group.id}')


def update_user_attachments(current_user: User, user_group: UserGroup, users: List[User]) -> UserGroup:
    """
    Change which members belong to a user group.
    :param current_user:
    :param user_group:
    :param users: The only users of the user group after this is called.
    :return:
    """
    if is_user_group_admin(current_user, user_group):
        user_group.members = users
        db.session.commit()
        return user_group
    raise AuthException(f'User {current_user.id} not authorized to modify group {user_group.id}')


def attach_user(current_user: User, target_user: User, user_group: UserGroup) -> UserGroup:
    """
    Make a user a member of a user group.
    :param current_user:
    :param target_user:
    :param user_group:
    :return:
    """
    if is_user_group_admin(current_user, user_group):
        if target_user not in user_group.members:
            user_group.members.append(target_user)
            db.session.commit()
        return user_group
    raise AuthException(f'User {current_user.email} is not authorized to attach user '
                        f'{target_user.email} to group {user_group.id}')


def elevate_user(current_user: User, target_user: User, user_group: UserGroup) -> UserGroup:
    """
    Make a user the admin of a group.
    :param current_user:
    :param target_user:
    :param user_group:
    :return:
    """
    if is_user_group_admin(current_user, user_group):
        if not is_user_group_admin(target_user, user_group):
            user_group.admins.append(target_user)
            db.session.commit()
        return user_group
    raise AuthException(f'User{current_user.email} not authorized to modify group {user_group.id}')


def detach_user(current_user: User, target_user: User, user_group: UserGroup) -> UserGroup:
    """
    Remove a user from a user group.
    :param current_user:
    :param target_user:
    :param user_group:
    :return:
    """
    if target_user is current_user or is_user_group_admin(current_user, user_group):
        if target_user in user_group.members:
            user_group.members.remove(target_user)
            db.session.commit()
        return user_group
    raise AuthException(f'User {current_user.email} not permitted to modify group {user_group.id}')


def delete_user_group(user: User, user_group: UserGroup) -> Dict[str, str]:
    """
    Delete a user group.
    :param user:
    :param user_group:
    :return:
    """
    if is_user_group_admin(user, user_group) or user.admin:
        user_group_id = user_group.id
        db.session.delete(user_group)
        return {'message': f'User group {user_group_id} deleted.'}
    raise AuthException(f'User {user.email} not permitted to modify user group {user_group.id}')


def get_included_groups(current_user: User, target_user: User) -> List[UserGroup]:
    """
    Get a list of user groups a user belongs to.
    :param current_user:
    :param target_user:
    :return:
    """
    return get_read_permitted_records(current_user, target_user.user_groups)


def get_group_members(user: User, user_group: UserGroup) -> List[User]:
    """
    Get the users who belong to this group.
    :param user:
    :param user_group:
    :return:
    """
    return get_read_permitted_records(user, user_group.members)
