"""
The to_dict methods only act recursively one way for some relationships to prevent infinite loops
Analysis provides Collection and Workflow metadata but Collection and Workflow provide only Analysis ids
SampleGroup provides Sample metadata but Sample provides only SampleGroup ids
UserGroup provides User metadata but User provides only UserGroup ids
"""
import json
import os

import ruamel.yaml as yaml
import sqlalchemy as sa
from flask_sqlalchemy import Model, SQLAlchemy, event
from sqlalchemy.ext.declarative import declared_attr

import data_tools.file_tools.metadata_tools as mdt


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

    def to_dict(self):
        return {'id': self.id}


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


class User(db.Model):
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

    def to_dict(self, sanitized=True):
        dict_rep = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'admin': self.admin,
            'active': self.active,
            'primary_user_group_id': self.primary_user_group_id,
            'group_ids': [group.id for group in self.user_groups],
            'admin_group_ids': [group.id for group in self.admin_user_groups]
        }
        if not sanitized:
            dict_rep['password'] = self.password
        return dict_rep


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
            'admins': [admin.to_dict() for admin in self.admins]
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
    def user_group_id(cls): return db.Column(db.Integer, db.ForeignKey('user_group.id'))

    @declared_attr
    def user_group(cls): return db.relationship(UserGroup, foreign_keys=[cls.user_group_id])


class FileRecordMixin(OmicsRecordMixin):
    filename = db.Column(db.String)
    file_type = db.Column(db.String, default='hdf5')
    data_path = '/data'
    file_ext = '.h5'

    @staticmethod
    def delete_file(mapper, connection, target):
        try:
            print('delete_file')
            print(target.name)
            if target.filename is not None:
                os.remove(target.filename)
        except FileNotFoundError:
            print('file not found')
            pass

    @staticmethod
    def synchronize_filename(target, value, oldvalue, initiator):
        target.filename = f'{target.data_path}/{value}.{target.file_ext}'

    @classmethod
    def register(cls):
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

    def get_file_info(self):
        """
        provides deep dive on structure of file
        :return:
        """
        # to extend to different file types, insert checks here
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

    def file_exists(self):
        return os.path.isfile(self.filename) if self.filename is not None else False


class NumericFileRecordMixin(FileRecordMixin):
    file_type = 'hdf5'
    file_ext = 'h5'

    def get_dimensions(self):
        return mdt.approximate_dims(self.filename) if self.file_exists() else (None, None)

    def get_dataset_info(self):
        return mdt.get_all_dataset_info(self.filename) if self.file_exists() else {}


class Analysis(OmicsRecordMixin, db.Model):
    __tablename__ = 'analysis'

    collections = db.relationship('Collection', secondary=collection_analysis_membership, back_populates='analyses')
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
            'workflows': [workflow.to_dict() for workflow in self.workflows]
        }


class Sample(NumericFileRecordMixin, db.Model):
    __tablename__ = 'sample'
    user_group = db.relationship('UserGroup', back_populates='samples')
    sample_groups = db.relationship('SampleGroup', secondary=sample_group_membership, back_populates='samples')
    data_path = '/data/samples'
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
            'file_info': self.get_file_info() if self.file_exists() else {}
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
            'samples': [sample.to_dict() for sample in self.samples]
        }


class Collection(NumericFileRecordMixin, db.Model):
    __tablename__ = 'collection'
    id = db.Column(db.Integer, primary_key=True)  # needed to make backref on children work properly
    user_group = db.relationship('UserGroup', back_populates='collections')
    analyses = db.relationship('Analysis', secondary=collection_analysis_membership, back_populates='collections')
    parent_id = db.Column(db.Integer, db.ForeignKey('collection.id'))
    children = db.relationship('Collection', backref=db.backref('parent', remote_side=[id]))
    data_path = '/data/collections'

    def create_label_column(self, name: str, data_type: str='string'):
        mdt.add_column(self.filename, name, data_type)

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
            'file_info': self.get_file_info() if self.file_exists() else {}
        }


class Workflow(FileRecordMixin, db.Model):
    __tablename__ = 'workflow'
    workflow_language = db.Column(db.String, default='cwl')
    file_type = db.Column(db.String, default='yaml')
    file_ext = db.synonym('workflow_language')

    user_group = db.relationship('UserGroup', back_populates='workflows')
    analyses = db.relationship('Analysis', secondary=workflow_analysis_membership, back_populates='workflows')

    data_path = '/data/workflows'

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
            'workflow_definition': self.get_file_info()
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
            'value': self.value
        }


class JobserverToken(db.Model):
    __tablename__ = 'job_server_token'
    value = db.Column(db.String)

    def to_dict(self):
        return {
            'id': self.id,
            'value': self.value
        }


Workflow.register()
Sample.register()
Collection.register()