import os
import shutil
from typing import List, Dict, Any

from data_tools.db import User, ExternalFile, db
from data_tools.users import is_read_permitted, is_write_permitted, get_all_read_permitted_records
from data_tools.util import AuthException, NotFoundException


def get_all_external_files() -> List[ExternalFile]:
    """
    Get information about all external files in the system (note: no user access control)
    :return: ExternalFile records
    """
    return ExternalFile.query.all()


def get_external_files(user: User) -> List[ExternalFile]:
    """
    Get all the external files a user is permitted to read
    :param user: A user (usually the currently authenticated user)
    :return: All the external files the user is permitted to read
    """
    return get_all_read_permitted_records(user, ExternalFile)


def get_external_file(user: User, external_file_id: int) -> ExternalFile:
    """
    Get a record corresponding to an external file
    :param user:
    :param external_file_id:
    :return:
    """
    external_file = ExternalFile.query.filter_by(id=external_file_id).first()
    if external_file is None:
        raise NotFoundException(f'No external file with id {external_file_id}')
    if is_read_permitted(user, external_file):
        return external_file
    raise AuthException(f'User {user.id} is not authorized to view external file {external_file.id}')


def get_external_file_by_path(user: User, filename: str) -> ExternalFile:
    """
    Get the external file record for the file with path filename
    :param user:
    :param filename:
    :return:
    """
    external_file = ExternalFile.query.filter_by(filename=filename).first()
    if external_file is None:
        raise NotFoundException(f'No external file record exists for {filename}')
    if is_read_permitted(user, external_file):
        return external_file
    raise AuthException(f'User {user.id} is not authorized to view external file record for {filename}')


def create_external_file(user: User, data: Dict[str, Any]) -> ExternalFile:
    """
    Create a new external file record (will not create the file at all, use upload for that)
    :param user:
    :param data:
    :return:
    """
    if 'id' in data:  # cannot create with designated id
        del data['id']
    external_file = ExternalFile(name=data['name'], creator=user, owner=user)
    db.session.add(external_file)
    db.session.commit()
    update_external_file(user, external_file, data)
    return external_file


def update_external_file(user: User, external_file: ExternalFile, new_data: Dict[str, Any],
                         move_file: bool = False) -> ExternalFile:
    """
    Update the data in the external file record
    :param user:
    :param external_file:
    :param new_data:
    :return:
    """
    if is_write_permitted(user, external_file):
        if 'id' in new_data:
            if ExternalFile.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'External file with id {new_data["id"]} already exists!')
        if move_file and 'filename' in new_data:
            original_filename = external_file.filename
            shutil.copy(original_filename, new_data['filename'])
            os.remove(original_filename)
        external_file.update(new_data)
        external_file.last_editor = user
        db.session.commit()
        return external_file
    raise AuthException(f'User {user.id} is not permitted to modify external file record {external_file.id}')


def upload_external_file(user: User, filename: str, new_data: Dict[str, Any]) -> ExternalFile:
    """
    From an uploaded file, create a new external file. File record entries are set from new_data
    :param user:
    :param filename:
    :param new_data:
    :return:
    """
    new_external_file = ExternalFile(owner=user, creator=user, last_editor=user, name=new_data['name'])
    db.session.add(new_external_file)
    db.session.commit()
    # make directories if necessary up to specified filename
    # consider relative paths relative to '/data/external'
    if 'filename' in new_data and new_data['filename']:
        if os.path.isabs(new_data['filename']):
            new_external_file.filename = os.path.normpath(new_data['filename'])
        else:
            new_external_file.filename = os.path.normpath(f'/data/external/{new_data["filename"]}')
    else:
        new_external_file.filename = f'/data/external/{new_external_file.id}/{os.path.basename(filename)}'
    if 'filename' in new_data:
        del new_data['filename']
    if os.path.isfile(new_external_file.filename):
        db.session.delete(new_external_file)
        db.session.commit()
        os.remove(filename)
        raise ValueError('File already exists! Please specify a different filename.')
    os.makedirs(os.path.dirname(new_external_file.filename))
    shutil.copy(filename, new_external_file.filename)
    os.remove(filename)
    update_external_file(user, new_external_file, new_data)
    db.session.commit()
    return new_external_file


def download_external_file(user: User, external_file: ExternalFile) -> Dict[str, str]:
    if is_read_permitted(user, external_file):
        return {'filename': os.path.basename(external_file.filename)}
    raise AuthException(f'User {user.id} is not permitted to access external file {external_file.id}')


def delete_external_file(user: User, external_file: ExternalFile, delete_file: bool = False):
    if is_write_permitted(user, external_file):
        filename = external_file.filename
        record_id = external_file.id
        db.session.delete(external_file)
        db.session.commit()
        if delete_file:
            os.remove(filename)
            return {'message': f'Deleted external file record {record_id} and file {filename}'}
        else:
            return {'message': f'Deleted external file record {record_id}. File {filename} still exists on disk.'}
