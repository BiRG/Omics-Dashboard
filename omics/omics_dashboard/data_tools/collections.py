import os
import shutil
import omics_dashboard.data_tools.file_tools.metadata_tools as mdt
import omics_dashboard.data_tools.file_tools.collection_tools as ct
from omics_dashboard.data_tools.database import db
from typing import List, Dict, Any
from omics_dashboard.data_tools.util import DATADIR, AuthException, \
    validate_file, get_next_id
from omics_dashboard.data_tools.users import is_read_permitted, is_write_permitted, get_read_permitted_records
from omics_dashboard.data_tools.file_tools.h5_merge import h5_merge


def get_all_collections() -> List[Dict[str, Any]]:
    """
    Get the attributes and dataset information of all collections in the system.
    :return:
    """
    paths = [f'{DATADIR}/collections/{collection_file}' for collection_file in os.listdir(f'{DATADIR}/collections/')]
    return [mdt.get_collection_info(path) for path in paths]


def get_collections(user_id: int) -> List[Dict[str, Any]]:
    """
    Get the attributes and dataset information of all collections a user is allowed to read.
    :param user_id:
    :return:
    """
    paths = [DATADIR + '/collections/' + file for file in os.listdir(DATADIR + '/collections/')]
    collection_info = [mdt.get_collection_info(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_all_collection_metadata(user_id: int) -> List[Dict[str, Any]]:
    """
    Get the attributes of all collections a user is allowed to read.
    :param user_id:
    :return:
    """
    paths = [DATADIR + '/collections/' + file for file in os.listdir(DATADIR + '/collections/')]
    collection_info = [mdt.get_collection_metadata(path) for path in paths]
    return get_read_permitted_records(user_id, collection_info)


def get_collection_metadata(user_id: int, collection_id: int) -> Dict[str, Any]:
    """
    Get the attributes of a collection.
    :param user_id:
    :param collection_id:
    :return:
    """
    collection_info = mdt.get_collection_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_read_permitted(user_id, collection_info):
        return collection_info
    raise AuthException('User %s is not authorized to view collection %s' % (str(user_id), str(collection_id)))


def get_collection(user_id: int, collection_id: int) -> Dict[str, Any]:
    """
    Get the attributes and dataset information of a collection
    :param user_id:
    :param collection_id:
    :return:
    """
    collection_info = mdt.get_collection_info(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_read_permitted(user_id, collection_info):
        return collection_info
    raise AuthException('User %s is not authorized to view collection %s' % (str(user_id), str(collection_id)))


def update_collection(user_id: int, collection_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update collection attributes
    :param user_id:
    :param collection_id:
    :param new_data:
    :return:
    """
    collection_info = mdt.get_collection_info(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_write_permitted(user_id, collection_info):
        return mdt.update_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5', new_data)
    raise AuthException('User %s is not permitted to modifiy collection %s' % (str(user_id), str(collection_id)))


def upload_collection(user_id: int, filename: str, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    From an uploaded HDF5 file, create a new collection. Metadata will be set from new_data
    :param user_id:
    :param filename:
    :param new_data:
    :return:
    """
    if validate_file(filename):
        new_id = get_next_id(f'{DATADIR}/collections/')
        new_filename = f'{DATADIR}/collections/{new_id}.h5'
        shutil.copy(filename, new_filename)
        os.remove(filename)

        # user can add any arbitrary valid JSON to a collection
        # if it gets to this point, it has already been validated!
        mdt.update_metadata(new_filename, new_data)
        new_data = {} if new_data is None else new_data
        new_data['createdBy'] = user_id
        new_data['owner'] = user_id
        mdt.update_metadata(new_filename, new_data)
        return mdt.get_collection_info(new_filename)
    raise Exception('File not valid.')


def download_collection(user_id: int, collection_id: int) -> Dict[str, str]:
    """
    If the user is permitted to read this collection, get the path to the collection, else throw.
    The file is sent via the send_from_directory flask method
    :param user_id:
    :param collection_id:
    :return:
    """
    filename = f'{DATADIR}/collections/{collection_id}.h5'
    collection = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, collection):
        return {'filename': f'{collection_id}.h5'}
    raise AuthException(f'User {user_id} is not permitted to access collection {collection_id}')


def download_collection_dataset(user_id: int, collection_id: int, path: str) -> Dict[str,  str]:
    """
    If the user is allowed to read a collection, get the contents required to send a file containing a dataset
    as CSV
    :param user_id:
    :param collection_id:
    :param path:
    :return:
    """
    filename = f'{DATADIR}/collections/{collection_id}.h5'
    collection = mdt.get_collection_metadata(filename)
    csv_filename = f'{os.path.basename(os.path.normpath(path))}.csv'
    if is_read_permitted(user_id, collection):
        return {'csv': mdt.get_csv(filename, path), 'cd': f'attachment; filename={csv_filename}'}
    raise AuthException(f'User {user_id} is not permitted to access collection {collection_id}')


def download_collection_dataframe(user_id: int, collection_id: int) -> Dict[str, str]:
    """
    If the user is allowed to read a collection, get the contents required to send a file containing the collection
    as a pandas dataframe as CSV
    :param user_id:
    :param collection_id:
    :return:
    """
    filename = f'{DATADIR}/collections/{collection_id}.h5'
    collection = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, collection):
        return {'csv': ct.get_dataframe(filename), 'cd': f'attachment; filename={collection_id}.csv'}
    raise AuthException(f'User {user_id} is not permitted to access collection {collection_id}')


def list_collection_paths(user_id: int, collection_id: int) -> List[str]:
    """
    List the paths corresponding to datasets in the collection
    :param user_id:
    :param collection_id:
    :return:
    """
    filename = f'{DATADIR}/collections/{collection_id}.h5'
    collection = mdt.get_collection_metadata(filename)
    if is_read_permitted(user_id, collection):
        return mdt.get_dataset_paths(filename)
    raise AuthException('User %s is not permitted to access collection %s' % (str(user_id), str(collection_id)))


def create_collection(user_id: int,
                      sample_ids: List[int],
                      new_data: Dict[str, Any],
                      sort_by: str= 'baseSampleId') -> Dict[str, Any]:
    """
    Create a new collection by concatenating samples. Collection metadata is set with new_data
    :param user_id:
    :param sample_ids:
    :param new_data: Collection attributes
    :param sort_by:
    :return:
    """
    print('set new_data:\n')
    new_data['owner'] = user_id
    outfilename = f'{DATADIR}/collections/{get_next_id("/data/collections")}.h5'
    filenames = [f'{DATADIR}/samples/{sample_id}.h5' for sample_id in sample_ids]
    print('check permissions on samples:\n')
    for filename in filenames:
        if not is_read_permitted(user_id, mdt.get_collection_metadata(filename)):
            raise AuthException(f'User {user_id} is not permitted to access file {filename}')
    h5_merge(filenames, outfilename, reserved_paths=['/x'], sort_by=sort_by)
    # TODO: allow samples aligned at 'x' with NaN padding
    print('update_metadata:\n')
    return mdt.update_metadata(outfilename, new_data)


def delete_collection(user_id, collection_id):
    collection_info = mdt.get_collection_metadata(DATADIR + '/collections/' + str(collection_id) + '.h5')
    if is_write_permitted(user_id, collection_info):
        os.remove(f'{DATADIR}/collections/{collection_id}.h5')
        db.query_db('delete from CollectionMemberships where collectionId=?;', [str(collection_id)])
        return {'message': 'collection ' + str(collection_id) + ' removed'}
    raise AuthException(f'User {user_id} is not permitted to modify collection {collection_id}')
