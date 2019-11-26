from typing import List, Dict, Any

from data_tools.wrappers.users import is_read_permitted, is_write_permitted, get_read_permitted_records, \
    get_all_read_permitted_records
from data_tools.db_models import User, Sample, SampleGroup, db
from data_tools.util import AuthException, NotFoundException


def get_sample_groups(user: User, filter_by: Dict[str, Any] = None) -> List[SampleGroup]:
    """
    Get all sample groups visible to a user.
    :param user:
    :param filter_by:
    :return:
    """
    return get_all_read_permitted_records(user, SampleGroup, filter_by)


def get_sample_group(user: User, group_id: int) -> SampleGroup:
    """
    Get a sample group.
    :param user:
    :param group_id:
    :return:
    """
    sample_group = SampleGroup.query.filter_by(id=group_id).first()
    if sample_group is None:
        raise NotFoundException(f'Sample group with id {group_id} not found.')
    if is_read_permitted(user, sample_group):
        return sample_group
    raise AuthException(f'User {user.email} is not authorized to view sample group {group_id}')


def create_sample_group(user: User, data: Dict[str, Any]) -> SampleGroup:
    """
    Create a new sample group.
    :param user:
    :param data:
    :return:
    """
    if 'id' in data:  # cannot create with designated id
        del data['id']
    name = data['name'] if 'name' in data else data['sample_group_name'] if 'sample_group_name' in data else ''
    sample_group = SampleGroup(owner=user, creator=user, last_editor=user, name=name)
    db.session.add(sample_group)
    db.session.commit()
    update_sample_group(user, sample_group, data)
    return sample_group


def update_sample_group(user: User, sample_group: SampleGroup, new_data: Dict[str, Any]) -> SampleGroup:
    """
    Update the data for a sample group.
    :param user:
    :param sample_group:
    :param new_data:
    :return:
    """

    if is_write_permitted(user, sample_group):
        if 'id' in new_data:
            if sample_group.id != new_data['id'] and SampleGroup.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'Sample group with id {new_data["id"]} already exists!')
        sample_group.update(new_data)
        sample_group.last_editor = user
        db.session.commit()
        return sample_group
    raise AuthException(f'User {user.email} is not permitted to modify group {sample_group.id}')


def update_sample_group_attachments(user: User, sample_group: SampleGroup, samples: List[Sample]) -> SampleGroup:
    """
    Make the only samples attached to a group those in sample_ids
    :param user:
    :param sample_group:
    :param samples:
    :return:
    """
    if is_write_permitted(user, sample_group) and all([is_read_permitted(user, sample) for sample in samples]):
        sample_group.samples = samples
        sample_group.last_editor = user
        db.session.commit()
        return sample_group
    raise AuthException(f'User {user.email} not authorized to modify group {sample_group.id}')


def attach_sample(user: User, sample: Sample, sample_group: SampleGroup) -> SampleGroup:
    """
    Make a sample a member of a sample group.
    :param user:
    :param sample:
    :param sample_group:
    :return:
    """
    if is_write_permitted(user, sample_group) and is_read_permitted(user, sample):
        if sample not in sample_group.samples:
            sample_group.samples.append(sample)
        sample_group.last_editor = user
        db.session.commit()
        return sample_group
    raise AuthException(f'User {user.email} is not permitted to attach {sample.id} to group {sample_group.id}')


def detach_sample(user: User, sample: Sample, sample_group: SampleGroup) -> SampleGroup:
    """
    Remove a sample from a sample group.
    :param user:
    :param sample:
    :param sample_group:
    :return:
    """
    if is_write_permitted(user, sample_group):
        sample_group.samples.remove(sample)
        sample_group.last_editor = user
        db.session.commit()
        return sample_group
    raise AuthException(f'User {user.email} not permitted to modify group {sample_group.id}')


def delete_sample_group(user: User, sample_group: SampleGroup) -> Dict[str, str]:
    """
    Delete a sample group.
    :param user:
    :param sample_group:
    :return:
    """
    if is_write_permitted(user, sample_group):
        db.session.delete(sample_group)
        db.session.commit()
        return {'message': f'User group {sample_group.id} deleted'}
    raise AuthException(f'User {user.email} not permitted to modify sample group {sample_group.id}')


def get_included_sample_groups(user: User, sample: Sample) -> List[SampleGroup]:
    """
    Get a list of sample groups that a sample is found in
    :param user:
    :param sample:
    :return:
    """
    if is_read_permitted(user, sample):
        return get_read_permitted_records(user, sample.sample_groups)
    raise AuthException(f'User {user.email} not permitted to view sample {sample.id}')


def get_sample_group_members(user: User, sample_group: SampleGroup) -> List[Sample]:
    """
    Get a list of samples which belong to this group.
    :param user:
    :param sample_group:
    :return:
    """
    if is_read_permitted(user, sample_group):
        return get_read_permitted_records(user, sample_group.samples)
    raise AuthException(f'User {user.email} not permitted to view sample group {sample_group.id}')


def sample_in_sample_group(user: User, sample: Sample, sample_group: SampleGroup) -> bool:
    """
    Determine if a sample belongs to a sample group. NotFoundException,
    :param user:
    :param sample:
    :param sample_group:
    :return:
    """
    if is_read_permitted(user, sample_group) and is_read_permitted(user, sample):
        return sample in sample_group.samples
    raise AuthException(f'User {user.email} not permitted to check the attachment of {sample.id} to sample group {sample_group.id}')
