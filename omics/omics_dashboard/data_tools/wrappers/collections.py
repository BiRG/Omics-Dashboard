import os
import re
import shutil
import tempfile
from typing import List, Dict, Any

import data_tools.file_tools.collection_tools as ct
import data_tools.file_tools.metadata_tools as mdt
from data_tools.wrappers.analyses import get_analysis
from data_tools.wrappers.users import is_read_permitted, is_write_permitted, get_all_read_permitted_records
from data_tools.db_models import Collection, User, Sample, db
from data_tools.file_tools.h5_merge import h5_merge
from data_tools.util import AuthException, NotFoundException, validate_file
from config.config import DATADIR


def get_all_collections(filter_by: Dict[str, Any] = None) -> List[Collection]:
    """
    Get the attributes and dataset information of all collections in the system.
    :return:
    """
    if filter_by:
        return Collection.query.filter_by(**filter_by).all()
    return Collection.query.all()


def get_collections(user: User, filter_by: Dict[str, Any] = None) -> List[Collection]:
    """
    Get the attributes and dataset information of all collections a user is allowed to read.
    :param user:
    :param filter_by:
    :return:
    """
    return get_all_read_permitted_records(user, Collection, filter_by)


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
        for key, value in collection.get_file_metadata().items():
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
            for collection in get_all_read_permitted_records(user, Collection)]


def get_collection(user: User, collection_id: int) -> Collection:
    """
    Get the attributes and dataset information of a collection
    :param user:
    :param collection_id:
    :return:
    """
    collection = Collection.query.filter_by(id=collection_id).first()
    if collection is None:
        raise NotFoundException(f'No collection with id {collection_id}')
    if is_read_permitted(user, collection):
        return collection
    raise AuthException(f'User {user.email} is not authorized to view collection {collection.id}')


def get_collection_copy(user: User, collection_id: int) -> Collection:
    """
    Get a temporary copy of a collection. It's filename will be a temporary file that you should delete
    :param user:
    :param collection_id:
    :return:
    """
    collection = get_collection(user, collection_id)
    tempdir = tempfile.mkdtemp()
    new_filename = os.path.join(tempdir, os.path.basename(collection.filename))
    shutil.copy(collection.filename, new_filename)
    with db.session.no_autoflush:
        collection.id = None  # if we add to db, will get new id, but we shouldn't do this if we still have tmp filename
        collection.filename = new_filename
        collection.is_temp = True
        return collection


def update_collection(user: User, collection: Collection, new_data: Dict[str, Any], filename: str = None) -> Collection:
    """
    Update collection attributes
    :param user:
    :param collection:
    :param new_data:
    :return:
    """
    if is_write_permitted(user, collection):
        # file attributes and database attributes should be separated
        if 'id' in new_data:
            if collection.id != int(new_data['id']) and Collection.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'Collection with id {new_data["id"]} already exists!')
        # verify write permissions on analyses to attach to or detach from
        if 'analysis_ids' in new_data:
            new_analyses = [get_analysis(user, analysis_id) for analysis_id in new_data['analysis_ids']]
            remove_analyses = [analysis for analysis in collection.analyses
                               if analysis.id not in new_data['analysis_ids']]
            for analysis in new_analyses:
                if not is_write_permitted(user, analysis):
                    raise AuthException(f'User {user.email} is not permitted to attach collection {collection.id} '
                                        f'to analysis {analysis.id}')
            for analysis in remove_analyses:
                if not is_write_permitted(user, analysis):
                    raise AuthException(f'User {user.email} is not permitted to detach collection {collection.id} '
                                        f'from analysis {analysis.id}')
            collection.analyses = new_analyses
        collection.update(new_data)
        if filename is not None:
            os.remove(collection.filename)
            shutil.copy(filename, collection.filename)
            os.remove(filename)
        if 'file_info' in new_data:
            mdt.update_metadata(collection.filename,
                                {key: value for key, value in new_data['file_info'].items()})
        collection.last_editor = user
        db.session.commit()
        return collection
    raise AuthException(f'User {user.email} is not permitted to modify collection {collection.id}')


def update_collection_array(user: User, collection: Collection, path: str, i: int, j: int, val) -> Collection:
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
        return collection
    raise AuthException(f'User {user.email} is not permitted to modify collection {collection.id}.')


def upload_collection(user: User, filename: str, new_data: Dict[str, Any], remove_file=True) -> Collection:
    """
    From an uploaded HDF5 file, create a new collection. Metadata will be set from new_data
    :param user:
    :param filename:
    :param new_data:
    :return:
    """
    if validate_file(filename):
        parent_id = new_data['parent_id'] if 'parent_id' in new_data else None
        analysis_id = new_data['analysis_id'] if 'analysis_id' in new_data else None
        analyses = [get_analysis(user, analysis_id)] if analysis_id is not None else []
        new_collection = Collection(owner=user, creator=user, last_editor=user, name=new_data['name'], parent_id=parent_id, analyses=analyses)
        db.session.add(new_collection)
        db.session.commit()
        new_collection.filename = f'{DATADIR}/collections/{new_collection.id}.h5'
        shutil.copy(filename, new_collection.filename)
        if remove_file:
            os.remove(filename)
        new_data['creator_id'] = user.id if 'creator_id' not in new_data else new_data['creator_id']
        new_data['owner_id'] = user.id if 'owner_id' not in new_data else new_data['owner_id']
        update_collection(user, new_collection, new_data)  # apply metadata
        db.session.commit()
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
        return {'filename': os.path.basename(collection.filename)}
    raise AuthException(f'User {user.email} is not permitted to access collection {collection.id}')


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
    raise AuthException(f'User {user.email} is not permitted to access collection {collection.id}')


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
        return {data_format: ct.get_serialized_dataframe(collection.filename, single_column, data_format, json_orient),
                'cd': f'attachment; filename={collection.id}.{data_format}'}
    raise AuthException(f'User {user.email} is not permitted to access collection {collection.id}')


def list_collection_paths(user: User, collection: Collection) -> List[str]:
    """
    List the paths corresponding to datasets in the collection
    :param user:
    :param collection:
    :return:
    """
    if is_read_permitted(user, collection):
        return mdt.get_dataset_paths(collection.filename)
    raise AuthException(f'User {user.email} is not permitted to access collection {collection.id}')


def create_collection(user: User,
                      samples: List[Sample],
                      data: Dict[str, Any],
                      sort_by: str = 'base_sample_id') -> Collection:
    """
    Create a new collection by concatenating samples. Collection metadata is set with new_data
    :param user:
    :param samples:
    :param data: Collection attributes
    :param sort_by:
    :return:
    """
    data['owner_id'] = user.id
    data['creator_id'] = user.id
    if 'id' in data:  # cannot create with specified id
        del data['id']
    for sample in samples:
        if not is_read_permitted(user, sample):
            raise AuthException(f'User {user.id} is not permitted to access sample {sample.id}')
    filenames = [sample.filename for sample in samples]
    new_collection = Collection(owner=user, creator=user, last_editor=user, name=data['name'])
    db.session.add(new_collection)
    db.session.commit()
    new_collection.filename = f'{DATADIR}/collections/{new_collection.id}.h5'
    db.session.commit()
    if len(filenames):
        new_collection.merge_samples(samples, sort_by)
    else:
        new_collection.create_empty_file()
    update_collection(user, new_collection, data)
    return new_collection


def delete_collection(user: User, collection: Collection) -> Dict[str, str]:
    if is_write_permitted(user, collection):
        collection_id = collection.id
        db.session.delete(collection)
        db.session.commit()  # event will handle file deletion
        return {'message': f'collection {collection_id} removed'}
    raise AuthException(f'User {user.email} is not permitted to modify collection {collection.id}')


def copy_collection(user: User, collection: Collection) -> Collection:
    new_collection = Collection(user_group=collection.user_group,
                                analyses=collection.analyses,
                                name='Copy of ' + collection.name,
                                description=collection.description,
                                group_can_read=collection.group_can_read,
                                group_can_write=collection.group_can_write,
                                all_can_read=collection.all_can_read,
                                all_can_write=collection.all_can_write,
                                owner=user,
                                creator=user,
                                last_editor=user,
                                parent_id=collection.id)
    db.session.add(new_collection)
    db.session.commit()
    new_collection.filename = f'{DATADIR}/collections/{new_collection.id}.h5'
    db.session.commit()
    shutil.copy(collection.filename, new_collection.filename)
    return new_collection


def merge_collections(user: User, collections: List[Collection], new_data: Dict[str, Any]) -> Collection:
    infilenames = [collection.filename for collection in collections]
    collection_id_str = ' + '.join([str(collection.id) for collection in collections])
    new_collection = Collection(user_group=collections[0].user_group,
                                analyses=collections[0].analyses,
                                name=f'{collections[0].name} (Collections {collection_id_str})',
                                description=collections[0].description,
                                group_can_read=collections[0].group_can_read,
                                group_can_write=collections[0].group_can_write,
                                all_can_read=collections[0].all_can_read,
                                all_can_write=collections[0].all_can_write,
                                owner=user,
                                creator=user,
                                last_editor=user)
    db.session.add(new_collection)
    db.session.commit()
    new_collection.filename = f'{DATADIR}/collections/{new_collection.id}.h5'
    db.session.commit()
    h5_merge(infilenames, new_collection.filename, orientation='vert', reserved_paths=['/x'], align_at='/x')
    return update_collection(user, new_collection, new_data)


def create_new_label_dataset(user: User, collection: Collection, name: str, data_type: str = 'string') -> Dict[str, str]:
    if is_write_permitted(user, collection):
        if re.match('^[^\d\W]\w*$', name):
            collection.create_label_column(name, data_type)
            return {'message': f'Created dataset {name} in collection {collection.id}.'}
        raise ValueError(f'Suggested name {name} is not valid.')
    raise AuthException(f'User {user.email} not permitted to modify collection {collection.id}.')

