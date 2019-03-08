from typing import Union

from flask import url_for

from data_tools.collections import get_collections
from data_tools.db import User, OmicsRecordMixin, Sample, Collection, SampleGroup, Analysis, Workflow, UserGroup, \
    ExternalFile
from data_tools.jobserver_control import Job
from data_tools.samples import get_samples
from data_tools.template_data.attribute_table import AttributeTableData, FileAttributeTableData, \
    WorkflowModuleAttributeTableData, DatasetSummaryTableData
from data_tools.template_data.form import ProfileUpdateFormData, PasswordResetFormData, SelectOption, FormEntry
from data_tools.template_data.label_column_table import LabelColumnTableData
from data_tools.template_data.list_table import ListTableData, FileListTableData
from data_tools.template_data.page import PageData
from data_tools.users import is_write_permitted, get_read_permitted_records
from data_tools.workflows import WorkflowModule
from helpers import get_update_url, get_list_url, get_download_url


class EntryPageData(PageData):
    def __init__(self,
                 current_user: User,
                 record: Union[OmicsRecordMixin, WorkflowModule, Job],
                 record_type: str):
        super(EntryPageData, self).__init__(current_user, is_write_permitted(current_user, record))
        self.id = record.id
        self.name = record.name
        self.update_url = get_update_url(record)
        self.list_url = get_list_url(record)
        self.attribute_table_data = AttributeTableData(current_user, record)
        self.record_type = record_type
        self.admin = current_user.admin


class FileEntryPageData(EntryPageData):
    def __init__(self,
                 current_user: User,
                 record: Union[Sample, Collection],
                 record_type: str):
        super(FileEntryPageData, self).__init__(current_user, record, record_type)
        self.file_attribute_table_data = FileAttributeTableData(current_user, record)
        self.dataset_summary_table_data = DatasetSummaryTableData(current_user, record)
        self.download_url = get_download_url(record)


class ExternalFilePageData(EntryPageData):
    def __init__(self,
                 current_user: User,
                 external_file: ExternalFile):
        super(ExternalFilePageData, self).__init__(current_user, external_file, 'External File')
        self.analysis_table_data = ListTableData(current_user, external_file.analyses, 'Analyses')
        self.download_url = get_download_url(external_file)


class CollectionPageData(FileEntryPageData):
    def __init__(self,
                 current_user: User,
                 collection: Collection
                 ):
        super(CollectionPageData, self).__init__(current_user, collection, 'Collection')
        self.label_column_table_data = LabelColumnTableData(current_user, collection)
        self.analysis_table_data = ListTableData(current_user, collection.analyses, 'Analyses')
        self.child_table_data = ListTableData(current_user, collection.children, 'Child Collections')


class SamplePageData(FileEntryPageData):
    def __init__(self,
                 current_user: User,
                 sample: Sample):
        super(SamplePageData, self).__init__(current_user, sample, 'Sample')
        self.sample_group_table_data = ListTableData(current_user, sample.sample_groups, 'Sample Groups')


class SampleGroupPageData(EntryPageData):
    def __init__(self,
                 current_user: User,
                 sample_group: SampleGroup):
        super(SampleGroupPageData, self).__init__(current_user, sample_group, 'Sample Group')

        attached = [sample in sample_group.samples for sample in get_samples(current_user)]
        self.sample_table_data = FileListTableData(current_user, get_samples(current_user), 'Samples', attached, 'Attached')
        self.attach_url = url_for('sample_groups_api.attach_sample', sample_group_id=sample_group.id)


class AnalysisPageData(EntryPageData):
    def __init__(self,
                 current_user: User,
                 analysis: Analysis):
        super(AnalysisPageData, self).__init__(current_user, analysis, 'Analysis')
        attached = [collection in analysis.collections for collection in get_collections(current_user)]
        self.collection_table_data = ListTableData(current_user, get_collections(current_user),
                                                   'Collections',
                                                   attached, 'Attached')
        self.attach_url = url_for('analyses_api.attach_collection', analysis_id=analysis.id)
        self.merge_url = url_for('collections_api.merge_collections')


class JobPageData(EntryPageData):
    def __init__(self, current_user: User, job: Job):
        super(JobPageData, self).__init__(current_user, job, 'Job')
        self.job_chart_url = url_for('jobs_api.get_chart_metadata', job_id=job.id)


class WorkflowPageData(EntryPageData):
    def __init__(self, current_user: User, workflow: Workflow):
        super(WorkflowPageData, self).__init__(current_user, workflow, 'Workflow')
        self.workflow_contents = workflow.get_workflow_contents()


class WorkflowModulePageData(EntryPageData):
    def __init__(self, current_user: User, workflow_module: WorkflowModule):
        super(WorkflowModulePageData, self).__init__(current_user, workflow_module, 'Workflow Module')
        self.workflow_module_contents = workflow_module.get_workflow_module_contents(as_text=True)
        self.attribute_table_data = WorkflowModuleAttributeTableData(workflow_module)


class UserPageData(EntryPageData):
    def __init__(self, current_user: User, target_user: User):
        super(UserPageData, self).__init__(current_user, target_user, 'User')
        user_groups = get_read_permitted_records(current_user, target_user.user_groups)
        user_group_admin = [target_user in user_group.admins for user_group in user_groups]
        self.target_admin = target_user.admin
        self.user_group_table_data = ListTableData(current_user,
                                                   get_read_permitted_records(current_user, target_user.user_groups),
                                                   f'{target_user.name}\'s User Groups',
                                                   special_val_heading='Admin',
                                                   special_vals=user_group_admin)


class UserGroupPageData(EntryPageData):
    def __init__(self, current_user: User, user_group: UserGroup):
        super(UserGroupPageData, self).__init__(current_user, user_group, 'User Group')
        members = get_read_permitted_records(current_user, user_group.members)
        admin = [user in user_group.admins for user in members]
        self.user_table_data = ListTableData(current_user, members, 'Group Members', admin, 'Admin')
        self.is_member = current_user in members
        self.is_primary = user_group == current_user.primary_user_group
        self.user_update_url = url_for('users_api.get_user', user_id=current_user.id)


class DashboardPageData(PageData):
    def __init__(self, current_user: User):
        super(DashboardPageData, self).__init__(current_user)
        self.analysis_table_data = ListTableData(current_user,
                                                 Analysis.query.filter(Analysis.owner_id == current_user.id).all(),
                                                 'Your Analyses')
        self.collection_table_data = ListTableData(current_user,
                                                   Collection.query.filter(Collection.owner_id == current_user.id).all(),
                                                   'Your Collections')
        user_group_admin = [current_user in user_group.admins for user_group in current_user.user_groups]
        self.user_group_table_data = ListTableData(current_user,
                                                   current_user.user_groups,
                                                   'Your User Groups',
                                                   special_val_heading='Admin',
                                                   special_vals=user_group_admin)


class SettingsPageData:
    def __init__(self, current_user: User):
        self.profile_update_form_data = ProfileUpdateFormData(current_user)
        self.admin = current_user.admin
        if current_user.admin:
            self.password_reset_form_data = PasswordResetFormData()
            user_group_options = [SelectOption(' ', 'None')] + [SelectOption(user_group.id, user_group.name) for user_group in UserGroup.query.all()]
            self.user_group_entry = FormEntry('primaryUserGroupSelect', 'primary_user_group', 'Primary user group',
                                              input_type='select',  select_options=user_group_options)

