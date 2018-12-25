from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy import event
import ruamel.yaml as yaml
import json
import os
import data_tools.file_tools.metadata_tools as mdt
db = SQLAlchemy()
"""
The to_dict methods only act recursively one way for some relationships to prevent infinite loops
Analysis provides Collection and Workflow metadata but Collection and Workflow provide only Analysis ids
SampleGroup provides Sample metadata but Sample provides only SampleGroup ids
UserGroup provides User metadata but User provides only UserGroup ids
"""
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


class Base(db.Model):
    __abstract_ = True
    id = db.Column(db.Integer, primary_key=True)
    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    group_can_read = False
    group_can_write = False
    all_can_read = False
    all_can_write = False
    owner_id = None
    user_group_id = None

    def to_dict(self):
        return {'id': self.id}


class User(Base):
    __tablename__ = 'user'
    email = db.Column(db.String, nullable=False, unique=True)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    user_groups = db.relationship('UserGroup', secondary=user_group_membership, back_populates='members')
    admin_user_groups = db.relationship('UserGroup', secondary=user_group_admin, back_populates='admins')

    owner_id = Base.id
    group_can_read = True
    all_can_read = db.Column(db.Boolean, default=True)

    def to_dict(self, sanitized=True):
        dict_rep = {
            'id': self.id,
            'email': self.email,
            'admin': self.admin,
            'active': self.active,
            'group_ids': [group.id for group in self.groups],
            'admin_group_ids': [group.id for group in self.admin_groups]
        }
        if not sanitized:
            dict_rep['password'] = self.password
        return dict_rep


class UserGroup(Base):
    __tablename__ = 'user_group'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String)
    description = db.Column(db.String)

    members = db.relationship('User', secondary=user_group_membership, back_populates='groups')
    admins = db.relationship('User', secondary=user_group_admin, back_populates='admin_groups')

    group_can_read = True
    group_can_write = False
    all_can_read = db.Column(db.Boolean, default=True)
    all_can_write = False

    analyses = db.relationship('Analysis', back_populates='user_group')
    samples = db.relationship('Sample', back_populates='user_group')
    collections = db.relationship('Collection', back_populates='user_group')
    sample_groups = db.relationship('SampleGroup', back_populates='user_group')
    workflows = db.relationship('Workflow', back_populates='user_group')

    user_group_id = id  # make it belong to itself...

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'name': self.name,
            'description': self.description,
            'members': [member.to_dict() for member in self.members],
            'admins': [admin.to_dict() for admin in self.admins]
        }


class OmicsRecord(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    group_can_read = db.Column(db.Boolean, default=True)
    group_can_write = db.Column(db.Boolean, default=True)
    all_can_read = db.Column(db.Boolean, default=True)
    all_can_write = db.Column(db.Boolean, default=False)

    user_group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'))


class FileRecord(OmicsRecord):
    filename = db.Column(db.String)
    file_type = db.Column(db.String, default='hdf5')

    def get_file_info(self):
        """
        provides deep dive on structure of file
        :return:
        """
        # to extend to different file types, insert checks here
        if self.file_type == 'hdf5':
            return mdt.get_collection_info(self.filename)
        return {}

    def get_file_metadata(self):
        """
        provides highest-level attributes of file
        :return:
        """
        # to extend to different file types, insert checks here
        if self.file_type == 'hdf5':
            return mdt.get_collection_metadata(self.filename)
        return{}


class Analysis(OmicsRecord):
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
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'collections': [collection.to_dict() for collection in self.collections],
            'workflows': [workflow.to_dict() for workflow in self.workflows]
        }


class Sample(FileRecord):
    __tablename__ = 'sample'
    user_group = db.relationship('UserGroup', back_populates='samples')
    sample_groups = db.relationship('SampleGroup', secondary=sample_group_membership, back_populates='samples')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'sample_group_ids': [group.id for group in self.sample_groups]
        }


class SampleGroup(OmicsRecord):
    __tablename__ = 'sample_group'
    user_group = db.relationship('UserGroup', back_populates='sample_groups')
    samples = db.relationship('Sample', secondary=sample_group_membership, back_populates='sample_groups')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'samples': [sample.to_dict() for sample in self.samples]
        }


class Collection(FileRecord):
    __tablename__ = 'collection'
    user_group = db.relationship('UserGroup', back_populates='collections')
    analyses = db.relationship('Analysis', secondary=collection_analysis_membership, back_populates='collections')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'analysis_ids': [analysis.id for analysis in self.analyses]
        }


class Workflow(FileRecord):
    __tablename__ = 'workflow'
    workflow_language = db.Column(db.String, default='cwl')
    file_type = db.Column(db.String, default='yaml')

    user_group = db.relationship('UserGroup', back_populates='workflows')
    analyses = db.relationship('Analysis', secondary=workflow_analysis_membership, back_populates='workflows')

    def get_file_info(self):
        if self.file_type == 'json':
            return json.load(open(self.filename, 'r'))
        elif self.file_type == 'yaml':
            return yaml.safe_load(open(self.filename, 'r'))
        else:
            return open(self.filename, 'r').read()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'group_can_read': self.group_can_read,
            'group_can_write': self.group_can_write,
            'all_can_read': self.all_can_read,
            'all_can_write': self.all_can_write,
            'user_group_id': self.user_group_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'workflow_language': self.workflow_language,
            'analysis_ids': [analysis.id for analysis in self.analyses],
            'workflow': self.get_file_info()
        }


class Invitation(Base):
    __tablename__ = 'invitation'
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    value = db.Column(db.String)
    owner_id = creator_id

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'value': self.value
        }


class JobserverToken(Base):
    __tablename__ = 'job_server_token'
    value = db.Column(db.String)

    def to_dict(self):
        return {
            'id': self.id,
            'value': self.value
        }


@event.listens_for(FileRecord, 'after_delete')
def receive_after_delete(mapper, connection, target):
    """
    Triggered when a record with a 'filename' field is deleted. Will delete the file on the filesystem.
    Can throw FileNotFoundError which should be handled gracefully.
    :param mapper:
    :param connection:
    :param target:
    :return:
    """
    os.remove(target.filename)

