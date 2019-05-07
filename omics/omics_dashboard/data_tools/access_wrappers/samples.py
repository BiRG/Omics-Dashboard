"""Functions for handling "Samples", which are HDF5 files created from the parsing of instrument-produced text files"""
import os
import shutil
from typing import Dict, List, Any

import data_tools.file_tools.metadata_tools as mdt
from data_tools.access_wrappers.sample_groups import get_sample_group
from data_tools.access_wrappers.users import is_read_permitted, is_write_permitted, get_all_read_permitted_records
from data_tools.db_models import Sample, User, db
from data_tools.util import DATADIR, AuthException, NotFoundException, validate_file


def get_all_samples(filter_by: Dict[str, Any] = None) -> List[Sample]:
    """
    Get the attributes and dataset paths of all samples
    :return:
    """
    if filter_by:
        return Sample.query.filter_by(**filter_by).all()
    return Sample.query.all()


def get_samples(user: User, filter_by: Dict[str, Any] = None) -> List[Sample]:
    """
    Get the attributes and dataset paths of all the samples to which the user with user_id has read access
    :param user:
    :return:
    """
    return get_all_read_permitted_records(user, Sample, filter_by)


def get_sample_metadata(user: User, sample: Sample) -> Dict[str, Any]:
    """
    Get the attributes of the sample with sample_id
    :param user:
    :param sample:
    :return:
    """

    if is_read_permitted(user, sample):
        collection_info = sample.to_dict()
        for key, value in sample.get_file_metadata().items():
            if key not in collection_info:  # ensures that database entries take precedence over file attributes
                collection_info[key] = value
        return collection_info
    raise AuthException(f'User {user.email} is not authorized to view collection {sample.id}')


def get_all_sample_metadata(user: User) -> List[Dict]:
    """
    Get the attributes of all the samples to which the user with user_id has read access
    :param user:
    :return:
    """
    return [get_sample_metadata(user, sample)
            for sample in get_all_read_permitted_records(user, Sample)]


def get_sample(user: User, sample_id: int) -> Sample:
    """
    Get the attributes and dataset paths of the sample with sample_id
    :param user:
    :param sample_id:
    :return:
    """
    sample = Sample.query.filter_by(id=sample_id).first()
    if sample is None:
        raise NotFoundException(f'No sample with id {sample_id}')
    if is_read_permitted(user, sample):
        return sample
    raise AuthException(f'User {user.email} is not permitted to access sample {sample_id}')


def update_sample(user: User, sample: Sample, new_data: Dict[str, Any], filename: str = None) -> Sample:
    """
    Change the attributes of the sample file with sample_id
    If a key exists in both the file and the db, it will be updated in both.
    :param user:
    :param sample:
    :param new_data:
    :param filename:
    :return:
    """
    if is_write_permitted(user, sample):
        # file attributes and database attributes should be separated
        if 'id' in new_data:
            if sample.id != int(new_data['id']) and Sample.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'Sample with id {new_data["id"]} already exists!')
        if 'sample_group_ids' in new_data:
            new_data['sample_group_ids'] = [int(sample_group_id) for sample_group_id in new_data['sample_group_ids']]
            new_sample_groups = [get_sample_group(user, sample_group_id) for sample_group_id in new_data['sample_group_ids']]
            remove_sample_groups = [sample_group for sample_group in sample.sample_groups if sample_group.id not in new_data['sample_group_ids']]
            for sample_group in new_sample_groups:
                if not is_write_permitted(user, sample_group):
                    raise AuthException(f'User {user.email} is not permitted to attach sample {sample.id} to sample group {sample_group.id}')
            for sample_group in remove_sample_groups:
                if not is_write_permitted(user, sample_group):
                    raise AuthException(f'User {user.email} is not permitted to detach sample {sample.id} from sample group {sample_group.id}')
            sample.sample_groups = new_sample_groups
        sample.update(new_data)
        if 'file_info' in new_data:
            mdt.update_metadata(sample.filename, new_data['file_info'])
        if filename is not None:
            os.remove(sample.filename)
            shutil.copy(filename, sample.filename)
            os.remove(filename)
        sample.last_editor = user
        sample.filename = f'/data/samples/{sample.id}.h5'
        db.session.commit()
        return sample
    raise AuthException(f'User {user.email} is not permitted to modify sample {sample.id}')


def delete_sample(user: User, sample: Sample) -> Dict[str, Any]:
    """
    Delete the sample file with sample_id
    :param user:
    :param sample:
    :return:
    """

    if is_write_permitted(user, sample):
        sample_id = sample.id
        db.session.delete(sample)
        db.session.commit()  # event will handle file deletion
        return {'message': f'Sample {sample_id} removed'}
    raise AuthException(f'User {user.email} is not permitted to modify collection {sample.id}')


def download_sample_dataset(user: User, sample: Sample, path: str) -> Dict[str, str]:
    """
    Download a CSV file containing a dataset found in this sample
    :param user:
    :param sample:
    :param path:
    :return:
    """
    csv_filename = f'{os.path.basename(os.path.normpath(path))}.csv'
    if is_read_permitted(user, sample):
        return {'csv': mdt.get_csv(sample.filename, path), 'cd': f'attachment; filename={csv_filename}'}
    raise AuthException(f'User {user.email} is not permitted to access collection {sample.id}')


def upload_sample(user: User, filename: str, data: Dict, sample_id: int = None) -> Sample:
    """
    Replace the current file with sample_id with a new file
    :param user:
    :param filename:
    :param data:
    :param sample_id:
    :return:
    """
    if 'id' in data:  # cannot create with specified id
        del data['id']
    if validate_file(filename):
        sample = Sample.query.filter_by(id=sample_id).first()
        name = data['name'] if 'name' in data else ''
        if sample is None:
            sample = Sample(owner=user, creator=user, last_editor=user, name=name)
            db.session.add(sample)
            db.session.commit()
        sample.filename = f'{DATADIR}/samples/{sample.id}.h5'
        shutil.copy(filename, sample.filename)
        os.remove(filename)
        # reconcile file metadata with sample when possible:
        file_attrs = sample.get_file_attributes()
        new_data = {key: value for key, value in data.items()}
        for key, value in file_attrs.items():
            if key in {'name', 'description'}:
                new_data[key] = file_attrs[key]
        update_sample(user, sample, new_data)  # apply metadata
        db.session.commit()
        return sample
    raise Exception('File not valid.')


def download_sample(user: User, sample: Sample) -> Dict[str, str]:
    """
    If the user with user_id is permitted to access sample_id, present the filename for the sample with sample_id
    :param user:
    :param sample:
    :return:
    """

    if is_read_permitted(user, sample):
        return {'filename': f'{sample.id}.h5'}
    raise AuthException(f'User {user.email} is not permitted to access sample {sample.id}')


def list_sample_paths(user: User, sample: Sample) -> List[str]:
    """
    List all the paths to datasets within the sample file
    :param user:
    :param sample:
    :return:
    """
    if is_read_permitted(user, sample):
        return mdt.get_dataset_paths(sample.filename)
    raise AuthException(f'User {user.email} is not permitted to access sample {sample.id}')


def create_placeholder_sample(user: User, data: Dict[str, Any]) -> Sample:
    """
    Create a blank sample at the next available id
    :param user
    :param data:
    :return:
    """
    if 'id' in data:  # cannot create with specified id
        del data['id']
    sample = Sample(creator=user, owner=user, last_editor=user, name=data['name'])
    db.session.add(sample)
    db.session.commit()
    filename = f'{DATADIR}/samples/{sample.id}.h5'
    mdt.create_empty_file(filename, {'name': data['name']})
    sample.filename = filename
    update_sample(user, sample, data)
    db.session.commit()
    return sample


def create_placeholder_samples(user: User, data: Dict, count: int) -> List[Sample]:
    """
    Create a particular number of blank samples. Used in sample parsing
    :param user:
    :param data:
    :param count:
    :return:
    """
    print(f'create_placeholder_samples: {data}, count: {count}')
    return [create_placeholder_sample(user, data) for _ in range(0, count)]
