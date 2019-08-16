"""
The to_dict methods only act recursively one way for some relationships to prevent infinite loops
Analysis provides Collection and Workflow metadata but Collection and Workflow provide only Analysis ids
SampleGroup provides Sample metadata but Sample provides only SampleGroup ids
UserGroup provides User metadata but User provides only UserGroup ids
"""
import json
import os
import pathlib
from typing import Dict, Any, List

import bcrypt
import h5py
import magic
import numpy as np
import pandas as pd
import ruamel.yaml as yaml
import sqlalchemy as sa
from flask_login import UserMixin
from flask_sqlalchemy import Model, SQLAlchemy, event
from sqlalchemy.ext.declarative import declared_attr

import data_tools.file_tools.collection_tools as ct
import data_tools.file_tools.metadata_tools as mdt
from data_tools.file_tools.h5_merge import h5_merge
from data_tools.redis import clear_user_hash
from data_tools.util import DATADIR


class Base(Model):
    __abstract_ = True
    id = sa.Column(sa.Integer, primary_key=True)
    created_on = sa.Column(sa.DateTime, default=sa.func.now())
    updated_on = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    group_can_read = False
    group_can_write = False
    all_can_read = False
    all_can_write = False
    owner_id = None
    user_group_id = None

    protected_keys = {
        'created_on',
        'updated_on',
    }

    admin_keys = set()

    def to_dict(self):
        return {'id': self.id}

    def update(self, new_data: Dict[str, Any], admin: bool = False):
        def invalid(val):
            return val in self.protected_keys if admin else (val in self.protected_keys | self.admin_keys)

        for key, value in new_data.items():
            if hasattr(self, key) and not invalid(key):
                self.__setattr__(key, value)


db = SQLAlchemy(model_class=Base)

# Tables that represent relations only
user_group_membership = db.Table('user_group_membership', db.Model.metadata,
                                 db.Column('user_id', db.Integer,
                                           db.ForeignKey('user.id',
                                                         onupdate='CASCADE',
                                                         ondelete='CASCADE'),
                                           primary_key=True),
                                 db.Column('user_group_id', db.Integer,
                                           db.ForeignKey('user_group.id',
                                                         onupdate='CASCADE',
                                                         ondelete='CASCADE'),
                                           primary_key=True))

user_group_admin = db.Table('user_group_admin', db.Model.metadata,
                            db.Column('user_id', db.Integer,
                                      db.ForeignKey('user.id',
                                                    onupdate='CASCADE',
                                                    ondelete='CASCADE'),
                                      primary_key=True),
                            db.Column('user_group_id', db.Integer,
                                      db.ForeignKey('user_group.id',
                                                    onupdate='CASCADE',
                                                    ondelete='CASCADE'),
                                      primary_key=True))

sample_group_membership = db.Table('sample_group_membership', db.Model.metadata,
                                   db.Column('sample_id', db.Integer,
                                             db.ForeignKey('sample.id',
                                                           onupdate='CASCADE',
                                                           ondelete='CASCADE'),
                                             primary_key=True),
                                   db.Column('sample_group_id', db.Integer,
                                             db.ForeignKey('sample_group.id',
                                                           onupdate='CASCADE',
                                                           ondelete='CASCADE'),
                                             primary_key=True))

collection_analysis_membership = db.Table('collection_analysis_membership', db.Model.metadata,
                                          db.Column('collection_id', db.Integer,
                                                    db.ForeignKey('collection.id',
                                                                  onupdate='CASCADE',
                                                                  ondelete='CASCADE'),
                                                    primary_key=True),
                                          db.Column('analysis_id', db.Integer,
                                                    db.ForeignKey('analysis.id',
                                                                  onupdate='CASCADE',
                                                                  ondelete='CASCADE'),
                                                    primary_key=True))

workflow_analysis_membership = db.Table('workflow_analysis_membership', db.Model.metadata,
                                        db.Column('workflow_id', db.Integer,
                                                  db.ForeignKey('workflow.id',
                                                                onupdate='CASCADE',
                                                                ondelete='CASCADE'),
                                                  primary_key=True),
                                        db.Column('analysis_id', db.Integer,
                                                  db.ForeignKey('analysis.id',
                                                                onupdate='CASCADE',
                                                                ondelete='CASCADE'),
                                                  primary_key=True))

external_file_analysis_membership = db.Table('external_file_analysis_membership', db.Model.metadata,
                                             db.Column('external_file_id', db.Integer,
                                                       db.ForeignKey('external_file.id',
                                                                     onupdate='CASCADE',
                                                                     ondelete='CASCADE'),
                                                       primary_key=True),
                                             db.Column('analysis_id', db.Integer,
                                                       db.ForeignKey('analysis.id',
                                                                     onupdate='CASCADE',
                                                                     ondelete='CASCADE'),
                                                       primary_key=True))


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    email = db.Column(db.String, nullable=False, unique=True)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    primary_user_group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'))
    primary_user_group = db.relationship('UserGroup', foreign_keys=primary_user_group_id)
    user_groups = db.relationship('UserGroup', secondary=user_group_membership, back_populates='members')
    admin_user_groups = db.relationship('UserGroup', secondary=user_group_admin, back_populates='admins')
    user_group = db.synonym('primary_user_group')
    user_group_id = db.synonym('primary_user_group_id')
    owner_id = db.synonym('id')
    group_can_read = True
    all_can_read = db.Column(db.Boolean, default=True)
    theme = db.Column(db.String, default='light')  # can be dark or light

    admin_keys = {
        'active',
        'admin',
        'id',
        'owner_id'
    }

    def set_password(self, plain_password: str):
        self.password = bcrypt.hashpw(bytes(plain_password, 'utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(bytes(plain_password, 'utf-8'), bytes(self.password, 'utf-8'))

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(bytes(plain_password, 'utf-8'), bcrypt.gensalt()).decode('utf-8')

    def to_dict(self, sanitized=True):
        dict_rep = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'admin': self.admin,
            'active': self.active,
            'primary_user_group_id': self.primary_user_group_id,
            'group_ids': [group.id for group in self.user_groups],
            'admin_group_ids': [group.id for group in self.admin_user_groups],
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat(),
            'theme': self.theme
        }
        if not sanitized:
            dict_rep['password'] = self.password
        return dict_rep

    # Flask-Login things

    @property
    def is_active(self):
        return self.active

    @staticmethod
    def reset_redis_hashes(target, value, oldvalue, initiator):
        clear_user_hash(oldvalue)
        clear_user_hash(value)

    @staticmethod
    def reset_redis_hash(mapper, connection, target):
        clear_user_hash(target.id)


class UserGroup(db.Model):
    __tablename__ = 'user_group'
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    members = db.relationship('User', secondary=user_group_membership, back_populates='user_groups')
    admins = db.relationship('User', secondary=user_group_admin, back_populates='admin_user_groups')

    group_can_read = True
    group_can_write = False
    all_can_read = db.Column(db.Boolean, nullable=False, default=True)
    all_can_write = False

    analyses = db.relationship('Analysis', back_populates='user_group')
    samples = db.relationship('Sample', back_populates='user_group')
    collections = db.relationship('Collection', back_populates='user_group')
    sample_groups = db.relationship('SampleGroup', back_populates='user_group')
    workflows = db.relationship('Workflow', back_populates='user_group')

    user_group_id = db.synonym('id')  # make it belong to itself...
    creator = db.relationship('User', foreign_keys=[creator_id])
    owner = db.synonym('creator')
    owner_id = db.synonym('creator_id')

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'name': self.name,
            'description': self.description,
            'members': [member.to_dict() for member in self.members],
            'admins': [admin.to_dict() for admin in self.admins],
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class OmicsRecordMixin(object):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    @declared_attr
    def creator_id(cls): return db.Column(db.Integer, db.ForeignKey('user.id'))

    @declared_attr
    def owner_id(cls): return db.Column(db.Integer, db.ForeignKey('user.id'))

    @declared_attr
    def last_editor_id(cls): return db.Column(db.Integer, db.ForeignKey('user.id'))

    @declared_attr
    def creator(cls): return db.relationship(User, foreign_keys=[cls.creator_id])

    @declared_attr
    def owner(cls): return db.relationship(User, foreign_keys=[cls.owner_id])

    @declared_attr
    def last_editor(cls): return db.relationship(User, foreign_keys=[cls.last_editor_id])

    group_can_read = db.Column(db.Boolean, default=True)
    group_can_write = db.Column(db.Boolean, default=True)
    all_can_read = db.Column(db.Boolean, default=True)
    all_can_write = db.Column(db.Boolean, default=False)

    @declared_attr
    def user_group_id(cls): return db.Column(db.Integer, db.ForeignKey('user_group.id'), default=None)

    @declared_attr
    def user_group(cls): return db.relationship(UserGroup, foreign_keys=[cls.user_group_id])

    admin_keys = {
        'creator',
        'creator_id',
        'last_editor',
        'last_editor_id'
    }


class FileRecordMixin(OmicsRecordMixin):
    filename = db.Column(db.String)
    file_type = db.Column(db.String, default='hdf5')
    data_path = DATADIR
    file_ext = 'h5'
    is_temp = False

    admin_keys = {
        'creator',
        'creator_id',
        'last_editor',
        'last_editor_id',
        'filename'
    }

    def __del__(self):
        try:
            if self.is_temp and self.filename is not None:
                os.remove(self.filename)
        except FileNotFoundError:
            pass

    @staticmethod
    def delete_file(mapper, connection, target):
        try:
            if target.filename is not None:
                os.remove(target.filename)
        except FileNotFoundError:
            pass

    @staticmethod
    def synchronize_filename(target, value, oldvalue, initiator):
        target.filename = f'{target.data_path}/{value}.{target.file_ext}'

    @classmethod
    def register_listeners(cls):
        """
        If the inherited class manages files (controls their names and deletions), listen for record deletion and id
        change and rename or delete the file when necessary.
        :return:
        """
        event.listen(cls, 'after_delete', cls.delete_file)
        event.listen(cls.id, 'set', cls.synchronize_filename)

    def get_file_metadata(self):
        """
        provides highest-level attributes of file
        :return:
        """
        # to extend to different file types, insert checks here
        if self.filename is not None:
            if self.file_type == 'hdf5':
                return mdt.get_collection_metadata(self.filename)
            elif self.file_type == 'yaml':
                return yaml.safe_load(open(self.filename, 'r'))
            elif self.file_type == 'json':
                return json.load(open(self.filename, 'r'))
        return {}

    def get_attr(self, key):
        if self.file_exists:
            try:
                if self.file_type == 'hdf5':
                    return h5py.File(self.filename).attrs[key]
                elif self.file_type == 'yaml':
                    return yaml.safe_load(open(self.filename, 'r'))[key]
                elif self.file_type == 'json':
                    return json.load(open(self.filename, 'r'))[key]
                else:
                    return None
            except:
                return None
        else:
            return None

    def get_file_info(self):
        """
        provides deep dive on structure of file
        :return:
        """
        # to extend to different file types, insert checks here (or overload in child class)
        if self.filename is not None:
            if self.file_type == 'hdf5':
                return mdt.get_collection_info(self.filename)
            else:
                return self.get_file_metadata()
        return {}

    def get_file_attributes(self):
        if self.filename is not None:
            if self.file_type == 'hdf5':
                return mdt.get_file_attributes(self.filename)
            elif self.file_type == 'yaml':
                return yaml.safe_load(open(self.filename, 'r'))
            elif self.file_type == 'json':
                return json.load(open(self.filename, 'r'))
        return {}

    def get_attribute_types(self):
        if self.file_type == 'hdf5':
            return mdt.get_file_attribute_dtypes(self.filename)
        else:
            if self.file_type == 'yaml':
                data = yaml.safe_load(open(self.filename, 'r'))
            elif self.file_type == 'json':
                data = json.load(open(self.filename, 'r'))
            else:
                data = {}  # technically correct
        return {key: type(value).__name__ for key, value in data.items()}

    @property
    def file_exists(self):
        return os.path.isfile(self.filename) if self.filename is not None else False


class NumericFileRecordMixin(FileRecordMixin):
    file_type = 'hdf5'
    file_ext = 'h5'

    def get_dimensions(self):
        return mdt.approximate_dims(self.filename) if self.file_exists else (None, None)

    def get_dataset_info(self):
        return mdt.get_all_dataset_info(self.filename) if self.file_exists else {}

    def get_attrs(self, path: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get a list of all the attributes of the file or the dataset at path.
        :param path:
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            with h5py.File(self.filename, 'r') as fp:
                if path is not None:
                    return {key: value for key, value in fp[path].attrs.items()}
                else:
                    return {key: value for key, value in fp.attrs.items()}

    def get_attr(self, key: str, path: str = None, safe=False) -> Any:
        """
        Get an attribute of the file or a path (Group or Dataset) inside the file.
        :param key: The key of the attribute to access.
        :param path: Optional. Get the attribute on a Group or Dataset of the file.
        :return:
        """
        path = path or '/'
        if self.file_exists:
            try:
                with h5py.File(self.filename, 'r') as fp:
                    return fp[path].attrs[key]
            except Exception as e:
                if safe:
                    return None
                raise e
        else:
            if safe:
                return None
            raise RuntimeError('File has not been downloaded! Use Session.download_file to download the file for this '
                               'record')

    def delete_attr(self, key: str, path: str = None):
        """
        Delete an attribute of the file or a path (Group or Dataset) inside the file.
        :param key: The key of the attribute to set.
        :param path: Optional. Set the attribute on a Group or Dataset of the file.
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            with h5py.File(self.filename, 'r+') as fp:
                if path is not None:
                    del fp[path].attrs[key]
                else:
                    del fp.attrs[key]
        else:
            raise RuntimeError('File has not been downloaded! Use Session.download_file to download the file for this '
                               'record')

    def set_attr(self, key: str, value: Any, path: str = None):
        """
        Get an attribute of the file or a path (Group or Dataset) inside the file.
        :param key: The key of the attribute to set.
        :param value: The new value for the attribute.
        :param path: Optional. Set the attribute on a Group or Dataset of the file.
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            with h5py.File(self.filename, 'r+') as fp:
                if path is not None:
                    fp[path].attrs[key] = value
                else:
                    fp.attrs[key] = value
        else:
            raise RuntimeError('File does not exist!')

    def get_dataset(self, path: str) -> np.array:
        """
        Get a numpy array from the file.
        :param path:
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            with h5py.File(self.filename, 'r') as fp:
                return np.asarray(fp[path])
        else:
            raise RuntimeError('File does not exist!')

    def delete_dataset(self, path):
        # type: (str) -> None
        """
        Delete a dataset from the file.
        :param path: Path to the dataset
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            with h5py.File(self.filename, 'r+') as fp:
                del fp[path]
        else:
            raise RuntimeError('File has not been downloaded! Use Session.download_file to download the file for this '
                               'record')

    def set_dataset(self, path, arr):
        # type: (str, np.array) -> None
        """
        Set the value of the dataset at path to arr
        :param arr: The numpy array.
        :param path: The path to the dataset.
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            with h5py.File(self.filename, 'r+') as fp:
                if path in fp:
                    del fp[path]
                fp.create_dataset(path, data=arr)
        else:
            raise RuntimeError('File has not been downloaded! Use Session.download_file to download the file for this '
                               'record')

    def get_dataframe(self, row_index_key: str = 'base_sample_id', keys: List[str] = None, include_labels: bool = True,
                      numeric_columns: bool = False, include_only_labels: bool = False) -> pd.DataFrame:
        """
        Get a Pandas DataFrame containing the records in keys or the columns of 'Y'. The column names will be 'Y_{x_i}'
        for 'x_i' in 'x' for Y if 'x' exists with the same dimensions as Y. Otherwise, the column names for all datasets
        with multiple columns will be 'Key_{i}' for i in n columns. The column names for datasets with one column will
        be the key of the dataset.
        :param row_index_key: A key for a column with unique values to use as a row index.
        :param keys: An iterable of keys to use as data for the dataframe.
        :param include_labels: Whether to include those datasets which are row labels for Y
        :param numeric_columns: Whether the column labels of Y should be the values of x, or the values of x prepended by Y (e.g. Y_15.2)
        :param include_only_labels: Whether to exclude 'Y' from the dataframe and only include label columns.
        :return:
        """
        """
        Get a Pandas DataFrame containing the records in keys. If keys is not specified or set to None, the index will
        be the values in "/x" and the names of the "label columns" (those columns with same number of rows as /Y).
        :param include_labels: Whether to include label columns alongside "/x" and "/Y". This will change the name of
        the indices associated with "/x" from "1" to "x_1"
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            return ct.get_dataframe(self.filename, row_index_key, keys, include_labels, numeric_columns,
                                    include_only_labels)
        else:
            raise RuntimeError('No local file')

    def get_dataset_csv(self, path: str) -> str:
        """
        Get a string containing CSV of a dataset
        :param path:
        :return:
        """
        if self.filename is not None and os.path.isfile(self.filename):
            return mdt.get_csv(self.filename, path)
        else:
            raise RuntimeError('File has not been downloaded! Use Session.download_file to download the file for this '
                               'record')

    def update_dataset(self, path: str, i: int, j: int, val: Any):
        """
        Change the value of an array at (i, j)
        :param path:
        :param i:
        :param j:
        :param val:
        :return:
        """

        if self.filename is not None and os.path.isfile(self.filename):
            ct.update_array(self.filename, path, i, j, val)
        else:
            raise RuntimeError('File has not been downloaded! Use Session.download_file to download the file for this '
                               'record')

    def merge(self, others):
        # type: (List[NumericFileRecordMixin]) -> None
        """
        Merge the rows from the other file into this one
        :param others:
        :return:
        """
        filenames = [self.filename] + [other.filename for other in others]
        h5_merge(filenames, self.filename, orientation='vert', reserved_paths=['/x'], align_at='/x')

    def create_empty_file(self):
        if not self.file_exists:
            h5py.File(self.filename, 'w')


class Analysis(OmicsRecordMixin, db.Model):
    __tablename__ = 'analysis'

    collections = db.relationship('Collection', secondary=collection_analysis_membership, back_populates='analyses')
    external_files = db.relationship('ExternalFile', secondary=external_file_analysis_membership,
                                     back_populates='analyses')
    workflows = db.relationship('Workflow', secondary=workflow_analysis_membership, back_populates='analyses')
    user_group = db.relationship('UserGroup', back_populates='analyses')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'last_editor_id': self.last_editor_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'collections': [collection.to_dict() for collection in self.collections],
            'workflows': [workflow.to_dict() for workflow in self.workflows],
            'external_files': [external_file.to_dict() for external_file in self.external_files],
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class Sample(NumericFileRecordMixin, db.Model):
    __tablename__ = 'sample'
    user_group = db.relationship('UserGroup', back_populates='samples')
    sample_groups = db.relationship('SampleGroup', secondary=sample_group_membership, back_populates='samples')
    data_path = f'{DATADIR}/samples'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'last_editor_id': self.last_editor_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'sample_group_ids': [group.id for group in self.sample_groups],
            'file_info': self.get_file_info() if self.file_exists else {},
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class SampleGroup(OmicsRecordMixin, db.Model):
    __tablename__ = 'sample_group'
    user_group = db.relationship('UserGroup', back_populates='sample_groups')
    samples = db.relationship('Sample', secondary=sample_group_membership, back_populates='sample_groups')
    upload_job_id = db.Column(db.String)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'last_editor_id': self.last_editor_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'upload_job_id': self.upload_job_id,
            'samples': [sample.to_dict() for sample in self.samples],
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class Collection(NumericFileRecordMixin, db.Model):
    __tablename__ = 'collection'
    id = db.Column(db.Integer, primary_key=True)  # needed to make backref on children work properly
    user_group = db.relationship('UserGroup', back_populates='collections')
    analyses = db.relationship('Analysis', secondary=collection_analysis_membership, back_populates='collections')
    parent_id = db.Column(db.Integer, db.ForeignKey('collection.id'))
    children = db.relationship('Collection', backref=db.backref('parent', remote_side=[id]))
    data_path = f'{DATADIR}/collections'
    kind = db.Column(db.String, default='data')  # should be 'data' or 'results'

    def merge_samples(self, samples: List[Sample], sort_by: str = 'base_sample_id'):
        h5_merge([sample.filename for sample in samples], self.filename, orientation='vert',
                 reserved_paths=['/x'], align_at='/x', sort_by=sort_by, merge_attributes=True)

    def create_label_column(self, name: str, data_type: str = 'string'):
        mdt.add_column(self.filename, name, data_type)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'last_editor_id': self.owner_id,
            'parent_id': self.parent_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'analysis_ids': [analysis.id for analysis in self.analyses],
            'file_info': self.get_file_info() if self.file_exists else {},
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class ExternalFile(FileRecordMixin, db.Model):
    __tablename__ = 'external_file'
    data_path = f'{DATADIR}/external'
    file_ext = ''  # Only used by FileRecordMixin models that are "registered" but should be blank here.
    analyses = db.relationship('Analysis', secondary=external_file_analysis_membership, back_populates='external_files')

    admin_keys = {
        'creator',
        'creator_id',
        'last_editor',
        'last_editor_id',
    }  # filename is editable

    @property
    def file_type(self):
        if self.file_exists:
            if not self.is_directory:
                return magic.from_file(self.filename, mime=True)
            else:
                return 'directory'
        else:
            return 'file does not exist'

    @property
    def is_directory(self):
        return os.path.isdir(self.filename)

    @property
    def children(self):
        if self.is_directory:
            file_info = []
            path = pathlib.Path(self.filename)
            for p in path.glob('**/*'):
                if p.is_file():
                    info = {
                        'absolute_path': str(p.absolute()),
                        'relative_path': str(p.relative_to(path)),
                        'file_type': magic.from_file(str(p))
                    }
                    stat = p.stat()
                    info.update({key: getattr(stat, key) for key in dir(stat) if key.startswith('st_')})
                    file_info.append(info)
            return file_info
        else:
            return None

    @staticmethod
    def delete_file(mapper, connection, target):
        raise RuntimeError('delete_file not supported on ExternalFile')

    @staticmethod
    def synchronize_filename(target, value, oldvalue, initiator):
        raise RuntimeError('synchronize_filename not supported on ExternalFile')

    @classmethod
    def register_listeners(cls):
        raise RuntimeError('register_listeners not supported on ExternalFile')

    def get_file_info(self):
        if self.file_exists:
            stat = os.stat(self.filename)
            return {key: getattr(stat, key) for key in dir(stat) if key.startswith('st_')}
        else:
            return None

    @property
    def file_exists(self):
        return super().file_exists or self.is_directory

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'last_editor_id': self.owner_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'analysis_ids': [analysis.id for analysis in self.analyses],
            'file_info': self.get_file_info() if self.file_exists else {},
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat(),
            'children': self.children if self.children is not None else []
        }


class Workflow(FileRecordMixin, db.Model):
    __tablename__ = 'workflow'
    workflow_language = db.Column(db.String, default='cwl')
    file_type = db.Column(db.String, default='yaml')
    file_ext = db.synonym('workflow_language')

    user_group = db.relationship('UserGroup', back_populates='workflows')
    analyses = db.relationship('Analysis', secondary=workflow_analysis_membership, back_populates='workflows')

    data_path = f'{DATADIR}/workflows'

    def get_file_info(self):
        if self.file_type == 'json':
            return json.load(open(self.filename, 'r'))
        elif self.file_type == 'yaml':
            return yaml.safe_load(open(self.filename, 'r'))
        else:
            return open(self.filename, 'r').read()

    def get_workflow_contents(self):
        with yaml.StringIO() as stream:
            yaml.dump(self.get_file_info(), stream)
            return stream.getvalue()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'last_editor_id': self.last_editor_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'workflow_language': self.workflow_language,
            'analysis_ids': [analysis.id for analysis in self.analyses],
            'workflow_definition': self.get_file_info(),
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class UserInvitation(db.Model):
    __tablename__ = 'user_invitation'
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship(User, foreign_keys=[creator_id])
    owner = db.synonym('creator')
    primary_user_group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'))
    primary_user_group = db.relationship(UserGroup, foreign_keys=[primary_user_group_id])
    value = db.Column(db.String)
    owner_id = db.synonym('creator_id')

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'primary_user_group_id': self.primary_user_group_id,
            'value': self.value,
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


class JobserverToken(db.Model):
    __tablename__ = 'job_server_token'
    value = db.Column(db.String)

    def to_dict(self):
        return {
            'id': self.id,
            'value': self.value,
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


# Do not register ExternalFile because we don't manage their filenames!
Workflow.register_listeners()
Sample.register_listeners()
Collection.register_listeners()
event.listen(User.id, 'set', User.reset_redis_hashes)
event.listen(User, 'after_delete', User.reset_redis_hash)


def validate_update_dict(record: db.Model, user: User, new_data: Dict[str, Any]):
    protected_keys = {
        'created_on',
        'updated_on',
    }
    admin_keys = {
        'owner_id',
        'creator_id'
    }

    def invalid(key):
        return key in protected_keys if user.admin else (key in protected_keys | admin_keys)

    return {key: value for key, value in new_data if hasattr(record, key) and not invalid(key)}
