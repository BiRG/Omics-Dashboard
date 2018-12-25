"""Functions for handling "Samples", which are HDF5 files created from the parsing of instrument-produced text files"""
import os
import shutil
from typing import Dict, List, Any
import data_tools.file_tools.metadata_tools as mdt
from data_tools.db import Sample, User, db
from data_tools.util import DATADIR, AuthException, validate_file
from data_tools.users import is_read_permitted, is_write_permitted, get_read_permitted_records


def get_all_samples() -> List[Sample]:
    """
    Get the attributes and dataset paths of all samples
    :return:
    """
    return Sample.query.all()


def get_samples(user: User) -> List[Sample]:
    """
    Get the attributes and dataset paths of all the samples to which the user with user_id has read access
    :param user:
    :return:
    """
    return get_read_permitted_records(user, Sample.query.all())


def get_sample_metadata(user: User, sample: Sample) -> Dict[str, Any]:
    """
    Get the attributes of the sample with sample_id
    :param user:
    :param sample:
    :return:
    """

    if is_read_permitted(user, sample):
        collection_info = sample.to_dict()
        for key, value in sample.get_file_metadata():
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
            for sample in get_read_permitted_records(user, Sample.query.all())]


def get_sample(user: User, sample_id: int) -> Sample:
    """
    Get the attributes and dataset paths of the sample with sample_id
    :param user:
    :param sample_id:
    :return:
    """
    sample = Sample.query.filter_by(id=sample_id).first()
    if is_read_permitted(user, sample):
        return sample
    raise AuthException(f'User {user.email} is not permitted to access sample {sample_id}')


def update_sample(user: User, sample: Sample, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Change the attributes of the sample file with sample_id
    :param user:
    :param sample:
    :param new_data:
    :return:
    """

    if is_write_permitted(user, sample):
        for key, value in new_data.items():
            if key in sample.to_dict() and key is not 'filename':
                sample.__setattr__(key, value)
        mdt.update_metadata(sample.filename, new_data)
        db.session.commit()
        return get_sample_metadata(user, sample)
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


def upload_sample(user: User, filename: str, new_data: Dict, sample_id: int = None) -> Sample:
    """
    Replace the current file with sample_id with a new file
    :param user:
    :param filename:
    :param new_data:
    :param sample_id:
    :return:
    """
    if validate_file(filename):
        sample = Sample.query.filter_by(id=sample_id).first()
        if sample is None:
            sample = Sample(owner_id=user.id)
            db.session.add(sample)
            db.commit()
        sample.filename = f'{DATADIR}/collections/{sample.id}.h5'
        shutil.copy(filename, sample.filename)
        os.remove(filename)
        new_data['creator_id'] = user.id
        new_data['owner_id'] = user.id
        update_sample(user, sample, new_data)  # apply metadata
        db.commit()
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
        return {'filename': sample.filename}
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
    sample = Sample()
    db.session.add(sample)
    db.session.commit()
    sample.filename = f'{DATADIR}/samples/{sample.id}.h5'
    update_sample(user, sample, data)
    db.session.commit()
    mdt.create_empty_file(sample.filename, data)
    return sample


def create_placeholder_samples(user: User, data: Dict, count: int) -> List[Sample]:
    """
    Create a particular number of blank samples. Used in sample parsing
    :param user:
    :param data:
    :param count:
    :return:
    """
    return [create_placeholder_sample(user, data) for _ in range(0, count)]
