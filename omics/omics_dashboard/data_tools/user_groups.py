from data_tools.util import AuthException
from data_tools.users import user_in_user_group, is_user_group_admin
from data_tools.database import db
from typing import List, Dict, Any


def get_user_groups() -> List[Dict[str, Any]]:
    """
    Get a list of all user groups.
    :return:
    """
    user_groups = db.query_db('select * from UserGroups;')
    for user_group in user_groups:
        group_members = get_group_members(user_group['id'])
        user_group['members'] = group_members
        user_group['users'] = [member['id'] for member in group_members]
        user_group['admins'] = [member['id'] for member in group_members if member['groupAdmin']]
    return user_groups


def get_user_group(group_id: int) -> Dict[str, Any]:
    """
    Get a user group.
    :param group_id:
    :return:
    """
    user_group = db.query_db('select * from UserGroups where id=?;', [str(group_id)], True)
    group_members = get_group_members(group_id)
    user_group['members'] = group_members
    user_group['users'] = [member['id'] for member in group_members]
    user_group['admins'] = [member['id'] for member in group_members if member['groupAdmin']]
    return user_group


def create_user_group(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user group.
    :param user_id:
    :param data:
    :return:
    """
    db.query_db('insert into UserGroups (createdBy, name, description) values (?, ?, ?);',
                [str(user_id), str(data['name']), str(data['description'])],
                True)
    new_group = db.query_db('select * from UserGroups order by id desc limit 1;', (), True)
    db.query_db('insert into GroupMemberships (userId, groupId, groupAdmin) values(?, ?, ?);',
                [str(user_id), str(new_group['id']), '1'])
    return new_group


def update_user_group(user_id: int, group_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the user groups information.
    :param user_id:
    :param group_id:
    :param new_data:
    :return:
    """
    if is_user_group_admin(user_id, group_id):
        valid_keys = ['name', 'description']
        valid_data = {key: value for key, value in new_data.items() if key in valid_keys}
        if len(valid_data):
            query = 'update UserGroups set' + ','.join([f' {key} = ?' for key in valid_data.keys()]) + ' where id=?;'
            params = [str(value) for key, value in new_data.items() if key in valid_keys]
            params.append(str(group_id))
            db.query_db(query, params)
        return db.query_db('select * from UserGroups where id=?;', [str(group_id)], True)
    raise AuthException('User %s is not authorized to modify user group %s' % (str(user_id), str(group_id)))


def update_user_attachments(current_user_id: int, group_id: int, user_ids: List[int]) -> Dict[str, str]:
    """
    Change which members belong to a user group.
    :param current_user_id:
    :param group_id:
    :param user_ids: The only users of the user group after this is called.
    :return:
    """
    if is_user_group_admin(current_user_id, group_id):
        user_ids = [int(user_id) for user_id in user_ids if int(user_id) != int(current_user_id)]
        current_member_ids = [member['id'] for member in get_group_members(group_id)]
        users_to_detach = [member_id for member_id in current_member_ids
                           if member_id not in user_ids and member_id != current_user_id]
        users_to_attach = [user_id for user_id in user_ids if user_id not in current_member_ids]
        for user_id in users_to_attach:
            attach_user(current_user_id, user_id, group_id)
        for user_id in users_to_detach:
            detach_user(current_user_id, user_id, group_id)
        return {'message': f'Users {str(users_to_attach)} attached to group {group_id}. '
                           f'Users {str(users_to_detach)} detached from group {group_id}'}
    raise AuthException(f'User {current_user_id} not authorized to modify group {group_id}')


def attach_user(current_user_id: int, target_user_id: int, group_id: int) -> Dict[str, str]:
    """
    Make a user a member of a user group.
    :param current_user_id:
    :param target_user_id:
    :param group_id:
    :return:
    """
    if is_user_group_admin(current_user_id, group_id):
        if not user_in_user_group(target_user_id, group_id):
            db.query_db('insert into GroupMemberships (userId, groupId, groupAdmin) values (?, ?, ?);',
                        [str(target_user_id), str(group_id), '0'])
            return db.query_db('select * from UserGroups order by id desc limit 1;', (), True)
        return {'message': f'user {target_user_id} attached to group {group_id}'}
    raise AuthException(f'User {current_user_id} is not authorized to attach user {target_user_id} to group {group_id}')


def elevate_user(current_user_id: int, target_user_id: int, group_id: int) -> Dict[str, str]:
    """
    Make a user the admin of a group.
    :param current_user_id:
    :param target_user_id:
    :param group_id:
    :return:
    """
    if is_user_group_admin(current_user_id, group_id):
        db.query_db('update GroupMemberships set groupAdmin=1 where id=?;', [str(target_user_id)])
        return {'message': f'User {target_user_id} elevated to admin of group {group_id}'}
    raise AuthException(f'User {current_user_id} not authorized to modify group {group_id}')


def detach_user(current_user_id: int, target_user_id: int, group_id: int) -> Dict[str, str]:
    """
    Remove a user from a user group.
    :param current_user_id:
    :param target_user_id:
    :param group_id:
    :return:
    """
    if target_user_id == current_user_id or is_user_group_admin(current_user_id, group_id):
        db.query_db('delete from GroupMemberships where userId=? and groupId=?;',
                    [str(target_user_id), str(group_id)])
        return {'message': 'user ' + str(target_user_id) + ' detached from group ' + str(group_id)}
    raise AuthException('User %s not permitted to modify group %s' % (str(current_user_id), str(group_id)))


def delete_user_group(user_id: int, group_id: int) -> Dict[str, str]:
    """
    Delete a user group.
    :param user_id:
    :param group_id:
    :return:
    """
    if is_user_group_admin(user_id, group_id):
        db.query_db('delete from UserGroups where id=?;', [str(group_id)])
        db.query_db('delete from GroupMemberships where groupId=?', [str(group_id)])
        return {'message': 'user group ' + str(group_id) + ' deleted'}
    raise AuthException('User %s not permitted to modify group %s' % (str(user_id), str(group_id)))


def get_included_groups(user_id: int) -> List[Dict[str, Any]]:
    """
    Get a list of user groups a user belongs to.
    :param user_id:
    :return:
    """
    query = ('select UserGroups.id, UserGroups.name, GroupMemberships.groupAdmin '
             'from GroupMemberships '
             'inner join UserGroups on UserGroups.id=GroupMemberships.groupId where GroupMemberships.userId=?')
    return db.query_db(query, [user_id])


def get_group_members(group_id: int) -> List[Dict[str, Any]]:
    """
    Get the users who belong to this group.
    :param group_id:
    :return:
    """
    query = ('select Users.id, Users.name, GroupMemberships.groupAdmin'
             ' from Users'
             ' inner join GroupMemberships on GroupMemberships.userId=Users.id'
             ' where GroupMemberships.groupId=?')
    return db.query_db(query, [str(group_id)])
