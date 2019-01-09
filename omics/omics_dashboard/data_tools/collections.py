import os
import shutil
import data_tools.file_tools.metadata_tools as mdt
import data_tools.file_tools.collection_tools as ct
from data_tools.db import Collection, User, Sample, db
from typing import List, Dict, Any
from data_tools.util import DATADIR, AuthException, validate_file
from data_tools.users import is_read_permitted, is_write_permitted, get_read_permitted_records
from data_tools.file_tools.h5_merge import h5_merge


def get_all_collections() -> List[Dict[str, Any]]:
    """
    Get the attributes and dataset information of all collections in the system.
    :return:
    """
    return Collection.query.all()


def get_collections(user: User) -> List[Dict[str, Any]]:
    """
    Get the attributes and dataset information of all collections a user is allowed to read.
    :param user:
    :return:
    """
    return get_read_permitted_records(user, Collection.query.all())


def get_collection_file_info(collection: Collection):
    collection_info = collection.to_dict()
    collection_info['file_info'] = collection.get_file_info()
    return collection_info


def get_collection_metadata(user: User, collection: Collection) -> Dict[str, Any]:
    """
    Get the attributes of a collection.
    :param user:
    :param collection:
    :return:
    """
    if is_read_permitted(user, collection):
        collection_info = collection.to_dict()
        for key, value in collection.get_file_metadata():
            if key not in collection_info:  # ensures that database entries take precedence over file attributes
                collection_info[key] = value
        return collection_info
    raise AuthException(f'User {user.email} is not authorized to view collection {collection.id}')


def get_all_collection_metadata(user: User) -> List[Dict[str, Any]]:
    """
    Get the attributes of all collections a user is allowed to read.
    :param user:
    :return:
    """
    return [get_collection_metadata(user, collection)
            for collection in get_read_permitted_records(user, Collection.query.all())]


def get_collection(user: User, collection_id: int) -> Collection:
    """
    Get the attributes and dataset information of a collection
    :param user:
    :param collection_id:
    :return:
    """
    collection = Collection.query.filter_by(id=collection_id).first()
    if is_read_permitted(user, collection):
        return collection
    raise AuthException(f'User {user.id} is not authorized to view collection {collection.id}')


def update_collection(user: User, collection: Collection, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update collection attributes
    :param user:
    :param collection:
    :param new_data:
    :return:
    """
    if is_write_permitted(user, collection):
        for key, value in new_data.items():
            if key in collection.to_dict() and key is not 'filename':
                collection.__setattr__(key, value)
        mdt.update_metadata(collection.filename, new_data)
        db.session.commit()
        return get_collection_metadata(user, collection)
    raise AuthException(f'User {user.id} is not permitted to modify collection {collection.id}')


def update_collection_array(user: User, collection: Collection, path: str, i: int, j: int, val) -> Dict[str, Any]:
    """
    Update one point of one array in a collection
    :param user:
    :param collection:
    :param path:
    :param i:
    :param j:
    :param val:
    :return:
    """
    if is_write_permitted(user, collection):
        ct.update_array(collection.filename, path, i, j, val)
        return get_collection_metadata(user, collection)
    raise AuthException(f'User {user.id} is not permitted to modify collection {collection.id}.')


def upload_collection(user: User, filename: str, new_data: Dict[str, Any]) -> Collection:
    """
    From an uploaded HDF5 file, create a new collection. Metadata will be set from new_data
    :param user:
    :param filename:
    :param new_data:
    :return:
    """
    if validate_file(filename):
        new_collection = Collection(owner_id=user.id)  # leave empty on init
        db.session.add(new_collection)
        db.commit()
        new_collection.filename = f'{DATADIR}/collections/{new_collection.id}.h5'
        shutil.copy(filename, new_collection.filename)
        os.remove(filename)
        new_data['creator_id'] = user.id
        new_data['owner_id'] = user.id
        update_collection(user, new_collection, new_data)  # apply metadata
        db.commit()
        return new_collection
    raise Exception('File not valid.')


def download_collection(user: User, collection: Collection) -> Dict[str, str]:
    """
    If the user is permitted to read this collection, get the path to the collection, else throw.
    The file is sent via the send_from_directory flask method
    :param user:
    :param collection:
    :return:
    """
    if is_read_permitted(user, collection):
        return {'filename': collection.filename}
    raise AuthException(f'User {user.id} is not permitted to access collection {collection.id}')


def download_collection_dataset(user: User, collection: Collection, path: str) -> Dict[str,  str]:
    """
    If the user is allowed to read a collection, get the contents required to send a file containing a dataset
    as CSV
    :param user:
    :param collection:
    :param path:
    :return:
    """
    csv_filename = f'{os.path.basename(os.path.normpath(path))}.csv'
    if is_read_permitted(user, collection):
        return {'csv': mdt.get_csv(collection.filename, path), 'cd': f'attachment; filename={csv_filename}'}
    raise AuthException(f'User {user.id} is not permitted to access collection {collection.id}')


def download_collection_dataframe(user: User, collection: Collection, single_column: bool = False,
                                  data_format: str = 'csv', json_orient: str = 'records') -> Dict[str, any]:
    """
    If the user is allowed to read a collection, get the contents required to send a file containing the collection
    as a pandas dataframe as CSV
    :param user:
    :param collection:
    :param single_column: whether to only include single-column attributes in dataframe
    :param data_format: file format of dataframe
    :param json_orient: pandas json orientation if json is data_format, otherwise ignored
    :return:
    """
    if is_read_permitted(user, collection):
        return {data_format: ct.get_dataframe(collection.filename, single_column, data_format, json_orient),
                'cd': f'attachment; filename={collection.id}.{data_format}'}
    raise AuthException(f'User {user.id} is not permitted to access collection {collection.id}')


def list_collection_paths(user: User, collection: Collection) -> List[str]:
    """
    List the paths corresponding to datasets in the collection
    :param user:
    :param collection:
    :return:
    """
    if is_read_permitted(user, collection):
        return mdt.get_dataset_paths(collection.filename)
    raise AuthException(f'User {user.id} is not permitted to access collection {collection.id}')


def create_collection(user: User,
                      samples: List[Sample],
                      new_data: Dict[str, Any],
                      sort_by: str = 'base_sample_id') -> Collection:
    """
    Create a new collection by concatenating samples. Collection metadata is set with new_data
    :param user:
    :param samples:
    :param new_data: Collection attributes
    :param sort_by:
    :return:
    """
    new_data['owner_id'] = user.id
    new_data['creator_id'] = user.id
    print('check permissions on samples:\n')
    for sample in samples:
        if not is_read_permitted(user, sample):
            raise AuthException(f'User {user.id} is not permitted to access sample {sample.id}')
    filenames = [sample.filename for sample in samples]
    new_collection = Collection(owner_id=user.id)
    db.session.add(new_collection)
    db.session.commit()
    new_collection.filename = f'{DATADIR}/collections/{new_collection.id}.h5'
    db.session.commit()
    h5_merge(filenames, new_collection.filename, orientation='vert', reserved_paths=['/x'], sort_by=sort_by)
    update_collection(user, new_collection, new_data)
    return new_collection


def delete_collection(user, collection) -> Dict[str, str]:
    if is_write_permitted(user, collection):
        collection_id = collection.id
        db.session.delete(collection)
        db.session.commit()  # event will handle file deletion
        return {'message': f'collection {collection_id} removed'}
    raise AuthException(f'User {user.id} is not permitted to modify collection {collection.id}')
