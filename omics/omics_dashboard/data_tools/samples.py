"""Functions for handling "Samples", which are HDF5 files created from the parsing of instrument-produced text files"""
import os
import shutil
from typing import Dict, List, Any
import data_tools.file_tools.metadata_tools as mdt
from data_tools.util import DATADIR, AuthException, validate_file, get_next_id
from data_tools.users import is_read_permitted, is_write_permitted, get_read_permitted_records


def get_all_samples() -> List[Dict]:
    """
    Get the attributes and dataset paths of all samples
    :return:
    """
    paths = [f'{DATADIR}/samples/{file}' for file in os.listdir(f'{DATADIR}/samples')]
    return [mdt.get_collection_info(path) for path in paths]


def get_samples(user_id: int) -> List[Dict]:
    """
    Get the attributes and dataset paths of all the samples to which the user with user_id has read access
    :param user_id:
    :return:
    """
    paths = [f'{DATADIR}/samples/{file}' for file in os.listdir(f'{DATADIR}/samples')]
    collection_info = [mdt.get_collection_info(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_all_sample_metadata(user_id: int) -> List[Dict]:
    """
    Get the attributes of all the samples to which the user with user_id has read access
    :param user_id:
    :return:
    """
    paths = [f'{DATADIR}/samples/{file}' for file in os.listdir(f'{DATADIR}/samples')]
    collection_info = [mdt.get_collection_metadata(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_sample_metadata(user_id: int, sample_id: int) -> Dict[str, Any]:
    """
    Get the attributes of the sample with sample_id
    :param user_id:
    :param sample_id:
    :return:
    """
    collection_info = mdt.get_collection_metadata(f'{DATADIR}/samples/{sample_id}.h5')
    if is_read_permitted(user_id, collection_info):
        return collection_info
    raise AuthException(f'User {user_id} is not authorized to view sample {sample_id}')


def get_sample(user_id: int, sample_id: int) -> Dict[str, Any]:
    """
    Get the attributes and dataset paths of the sample with sample_id
    :param user_id:
    :param sample_id:
    :return:
    """
    sample_info = mdt.get_collection_info(f'{DATADIR}/samples/{sample_id}.h5')
    if is_read_permitted(user_id, sample_info):
        return sample_info
    raise AuthException(f'User {user_id} is not permitted to access sample {sample_id}')


def download_sample_dataset(user_id: int, sample_id: int, path: str) -> Dict[str, str]:
    """
    Download a CSV file containing a dataset found in this sample
    :param user_id:
    :param sample_id:
    :param path:
    :return:
    """
    filename = f'{DATADIR}/samples/{sample_id}.h5'
    collection = mdt.get_collection_metadata(filename)
    csv_filename = f'{os.path.basename(os.path.normpath(path))}.csv'
    if is_read_permitted(user_id, collection):
        return {'csv': mdt.get_csv(filename, path), 'cd': f'attachment; filename={csv_filename}'}
    raise AuthException(f'User {user_id} is not permitted to access collection {sample_id}')


def upload_sample(user_id: int, filename: str, new_data: Dict, sample_id: int = None) -> Dict[str, Any]:
    """
    Replace the current file with sample_id with a new file
    :param user_id:
    :param filename:
    :param new_data:
    :param sample_id:
    :return:
    """
    if validate_file(filename):
        new_id = sample_id if sample_id is not None else get_next_id(f'{DATADIR}/samples/')
        new_filename = f'{DATADIR}/samples/{new_id}.h5'
        old_data = mdt.get_collection_metadata(new_filename) if sample_id is not None else None
        if (sample_id is not None) and (old_data is None):
            raise Exception('Cannot update nonexistent collection!')
        if (sample_id is None) or is_write_permitted(user_id, old_data):
            shutil.copy(filename, new_filename)
            os.remove(filename)
            # user can add any arbitrary valid JSON to a collection
            # if it gets to this point, it has already been validated!
            metadata = {} if new_data is None else dict(new_data)
            metadata['createdBy'] = user_id
            metadata['owner'] = user_id
            mdt.update_metadata(new_filename, metadata)
            return mdt.get_collection_info(new_filename)
    raise Exception('file not valid')


def download_sample(user_id: int, sample_id: int) -> Dict[str, str]:
    """
    If the user with user_id is permitted to access sample_id, present the filename for the sample with sample_id
    :param user_id:
    :param sample_id:
    :return:
    """
    filename = f'{DATADIR}/samples/{sample_id}.h5'
    sample = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, sample):
        return {'filename': f'{sample_id}.h5'}
    raise AuthException(f'User {user_id} is not permitted to access sample')


def list_sample_paths(user_id: int, sample_id: int) -> List[str]:
    """
    List all the paths to datasets within the sample file
    :param user_id:
    :param sample_id:
    :return:
    """
    filename = f'{DATADIR}/samples/{sample_id}.h5'
    sample = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, sample):
        return mdt.get_dataset_paths(filename)
    raise AuthException(f'User {user_id} is not permitted to access sample {sample_id}')


def update_sample(user_id: int, sample_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Change the attributes of the sample file with sample_id
    :param user_id:
    :param sample_id:
    :param new_data:
    :return:
    """
    sample_info = mdt.get_collection_metadata(f'{DATADIR}/samples/{sample_id}.h5')
    if is_write_permitted(user_id, sample_info):
        return mdt.update_metadata(f'{DATADIR}/samples/{sample_id}.h5', new_data)
    raise AuthException(f'User {user_id} does not have permission to edit sample {sample_id}')


def delete_sample(user_id: int, sample_id: int) -> Dict[str, Any]:
    """
    Delete the sample file with sample_id
    :param user_id:
    :param sample_id:
    :return:
    """
    sample_info = mdt.get_collection_metadata(f'{DATADIR}/samples/{sample_id}.h5')
    if is_write_permitted(user_id, sample_info):
        os.remove(f'{DATADIR}/samples/{sample_id}.h5')
        return {'message': f'sample {sample_id} removed'}
    raise AuthException(f'User {user_id} does not have permission to modify sample {sample_id}')


def create_placeholder_sample(data: Dict[str, Any]) -> int:
    """
    Create a blank sample at the next available id
    :param data:
    :return:
    """
    sample_id = get_next_id(f'{DATADIR}/samples')
    path = f'{DATADIR}/samples/{sample_id}.h5'
    mdt.create_empty_file(path, data)
    return sample_id


def create_placeholder_samples(data: Dict, count: int) -> List[int]:
    """
    Create a particular number of blank samples. Used in sample parsing
    :param data:
    :param count:
    :return:
    """
    return [create_placeholder_sample(data) for _ in range(0, count)]

