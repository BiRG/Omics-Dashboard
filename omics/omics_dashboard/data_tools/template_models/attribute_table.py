from datetime import datetime
from typing import Any, List, Union

from flask import url_for

from data_tools.wrappers.jobserver_control import Job, get_job
from data_tools.wrappers.users import is_write_permitted, is_read_permitted
from data_tools.wrappers.workflows import WorkflowModule
from data_tools.db_models import User, OmicsRecordMixin, UserGroup, FileRecordMixin, SampleGroup, Sample, Collection, \
    ExternalFile, Base
from data_tools.template_models.form import SelectOption
from data_tools.template_models.page import PageData
from helpers import get_item_link


class AttributeTableRow:
    """
    Stores an attribute that can possibly be edited.
    A list of these is passed to the attribute editor as 'attributes'
    """
    def __init__(self, label: str, value: Any,
                 editable: bool = False,
                 href: str = None,
                 select_options: List[SelectOption] = None,
                 select_multiple: bool = False,
                 select_composite: bool = False):
        self.label = label
        self.value = value
        self.editable = editable
        self.href = href
        self.select_options = select_options
        self.select_multiple = select_multiple
        self.select_composite = select_composite


class FileAttributeTableRow:
    """
    Stores an attribute of a file
    """
    def __init__(self, label: str, value: Any, dtype: str, editable: bool=False):
        self.label = label
        self.value = value
        self.editable = editable
        self.dtype = dtype


class DatasetSummaryTableRow:
    """
    Stores attributes of a dataset
    """
    def __init__(self, path: str, dtype: str, n_rows: int, n_cols: int, download_url: str):
        self.path = path
        self.dtype = dtype
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.download_url = download_url


class AttributeTableData(PageData):
    """
    A list of editable attributes for a database AttributeTable
    """
    def __init__(self, current_user: User, record: Any):
        super(AttributeTableData, self).__init__(current_user, is_write_permitted(current_user, record))
        self.values = {'ID': AttributeTableRow('id', record.id, False),
                       'Name': AttributeTableRow('name', record.name, self.editable)}
        if hasattr(record, 'description'):
            self.values['Description'] = AttributeTableRow('description',
                                                           record.description if record.description is not None else '',
                                                           self.editable)
        if isinstance(record, SampleGroup):
            job = get_job(record.upload_job_id)
            self.values['Job'] = AttributeTableRow('job', job.name, href=get_item_link(job))
        if isinstance(record, User):
            self.values['Email'] = AttributeTableRow('email', record.email, False, href=f'mailto:{record.email}')
            if is_read_permitted(current_user, record.primary_user_group):
                self.values['Primary User Group'] = AttributeTableRow('primary_user_group',
                                                                      record.primary_user_group.name if record.primary_user_group is not None else None,
                                                                      False,
                                                                      get_item_link(record.primary_user_group) if record.primary_user_group is not None else None)
        if isinstance(record, OmicsRecordMixin):
            if is_read_permitted(current_user, record.owner):
                self.values['Owner'] = AttributeTableRow('owner',
                                                         record.owner.name if record.owner is not None else None,
                                                         False,
                                                         get_item_link(record.owner) if record.owner is not None else None)
            user_group_options = [SelectOption(group.id, group.name, group is record.user_group)
                                      for group in UserGroup.query.filter(UserGroup.members.contains(current_user)).all()]
            self.values['User Group'] = AttributeTableRow('user_group_id',
                                                          record.user_group.name if record.user_group is not None else None,
                                                          self.editable, None,
                                                          user_group_options, False)
            permissions_options = [
                SelectOption('all_can_read', 'Anyone can view?', record.all_can_read),
                SelectOption('group_can_read', 'User group members can view?', record.group_can_read),
                SelectOption('all_can_write', 'Anyone can edit or delete?', record.all_can_write),
                SelectOption('group_can_write', 'User group members can edit or delete', record.group_can_write)
            ]
            self.values['Permissions'] = AttributeTableRow('permissions', None,
                                                           is_write_permitted(current_user, record),
                                                           select_options=permissions_options,
                                                           select_multiple=True, select_composite=True)

        if isinstance(record, Collection):
            if record.parent is not None and is_read_permitted(current_user, record.parent):
                self.values['Parent Collection'] = AttributeTableRow('parent', f'{record.parent.name} (Collection {record.parent.id})', href=get_item_link(record.parent))
            else:
                self.values['Parent Collection'] = AttributeTableRow('parent', 'None')
            self.values['Kind'] = AttributeTableRow('kind', record.kind)
        if isinstance(record, Job):
            self.values['Type'] = AttributeTableRow('type', record.type)
            self.values['Status'] = AttributeTableRow('status', record.status)
            self.values['Submitted'] = AttributeTableRow('submitted', record.submission)
            self.values['Started'] = AttributeTableRow('start', record.start)
            self.values['Ended'] = AttributeTableRow('end', record.end)
            if is_read_permitted(current_user, record.owner):
                self.values['Submitted By'] = AttributeTableRow('owner', record.owner.name, href=get_item_link(record.owner))
        if isinstance(record, ExternalFile):
            self.values['Path'] = AttributeTableRow('filename', record.filename)
            self.values['File Type'] = AttributeTableRow('file_type', record.file_type)
            file_info = record.get_file_info()
            if file_info is not None:
                size_mb = file_info['st_size'] / (1024 * 1024.0)
                self.values['Size'] = AttributeTableRow('file_size', f'{size_mb:.3f} MB')
                self.values['File Modified'] = AttributeTableRow('file_mtime',
                                                                 datetime.fromtimestamp(file_info['st_mtime']).strftime(
                                                                     '%-d %b %Y %H:%M'))
        if isinstance(record, Base):
            self.values['Date Created'] = AttributeTableRow('created_on', record.created_on.strftime('%-d %b %Y %H:%M'))
            self.values['Date Modified'] = AttributeTableRow('updated_on',
                                                             record.updated_on.strftime('%-d %b %Y %H:%M'))


class FileAttributeTableData(PageData):
    """
    A list of editable attributes that come from a file. Dtypes are important and stored in a
    """
    def __init__(self, current_user: User, record: FileRecordMixin):
        super(FileAttributeTableData, self).__init__(current_user, is_write_permitted(current_user, record))
        dtypes = record.get_attribute_types()
        self.rows = [FileAttributeTableRow(key, value, dtypes[key], self.editable)
                     for key, value in record.get_file_attributes().items()]


class FileGroupAttributeTableData(PageData):
    """
    A list of noneditable attributes that come from a file's child groups.
    """

    def __init__(self, current_user: User, record: FileRecordMixin):
        super(FileGroupAttributeTableData, self).__init__(current_user, is_write_permitted(current_user, record))
        self.rows = [FileAttributeTableRow(key, value, type(value).__name__)
                     for key, value in record.get_group_attributes().items()]


class DatasetSummaryTableData(PageData):
    """
    A list of non-editable dataset information (path, dtype, size)
    Note that Omics dashboard does not support editing dataset attributes.
    """
    def __init__(self, current_user: User, record: Union[Sample, Collection]):
        super(DatasetSummaryTableData, self).__init__(current_user, False)
        if isinstance(record, Collection):
            self.rows = [DatasetSummaryTableRow(dataset['path'],
                                            dataset['dtype'],
                                            dataset['rows'],
                                            dataset['cols'],
                                            url_for('collections_api.download_collection',
                                                    collection_id=record.id,
                                                    path=dataset['path']))
                     for dataset in record.get_dataset_info()]
        elif isinstance(record, Sample):
            self.rows = [DatasetSummaryTableRow(dataset['path'],
                                                dataset['dtype'],
                                                dataset['rows'],
                                                dataset['cols'],
                                                url_for('samples_api.download_sample',
                                                        sample_id=record.id,
                                                        path=dataset['path']))
                         for dataset in record.get_dataset_info()]


class WorkflowModuleAttributeTableData:
    def __init__(self, workflow_module: WorkflowModule):
        self.editable = False
        # since we loaded from yaml, non-primitives should be only list or dict
        self.values = {
            key: AttributeTableRow(key, value) for key, value in workflow_module.get_workflow_module_contents().items()
            if not (isinstance(value, list) or isinstance(value, dict))
        }
