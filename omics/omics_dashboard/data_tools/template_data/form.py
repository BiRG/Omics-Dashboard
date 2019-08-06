from typing import List, Any, Dict

from data_tools.access_wrappers.analyses import get_analyses
from data_tools.access_wrappers.collections import get_collections
from data_tools.access_wrappers.sample_creation import get_parsing_modules, get_preprocessing_modules
from data_tools.access_wrappers.samples import get_samples
from data_tools.access_wrappers.user_groups import get_included_groups
from data_tools.access_wrappers.users import get_users, get_all_read_permitted_records
from data_tools.db_models import User, Collection, Sample, ExternalFile
from data_tools.util import DATADIR


class SelectOption:
    """
    Data for putting into a 'select' tag
    """
    def __init__(self, value: str, contents: str, selected: bool = False):
        self.value = value
        self.contents = contents
        self.selected = selected


class FormEntry:
    """
    Stores data used for one line of a creation form.
    """
    def __init__(self, tag_id: str, name: str, label: str, value: Any = '', input_type: str = 'text',
                 select_options: List[SelectOption] = None,
                 select_multiple: bool = False):
        self.id = tag_id
        self.name = name
        self.label = label
        self.value = value  # usually a placeholder
        self.input_type = input_type  # 'email', 'password', 'checkbox', 'file' or 'select'
        self.select_options = select_options
        self.select_multiple = select_multiple


class JobInputEntry:
    def __init__(self, wf_input, current_user):
        if wf_input['id'] in ('omics_url', 'omics_auth_token'):
            self.editable = False
            self.value = 'Set by Omics Dashboard'
        else:
            self.editable = True
            self.value = wf_input['default'] if 'default' in wf_input else ''
        self.id = wf_input['id']
        if wf_input['type'].endswith('[]'):
            self.input_type = wf_input['type'][:-2]
            self.select_multiple = True
        else:
            self.input_type = wf_input['type']
            self.select_multiple = False
        self.label = wf_input['label'] if 'label' in wf_input else wf_input['id']
        self.doc = wf_input['doc'] if 'doc' in wf_input else ''
        self.select_options = []
        if wf_input['type'].startswith('File'):
            for collection in get_all_read_permitted_records(current_user, Collection):
                self.select_options.append(SelectOption(collection.filename,
                                                        f'Collection {collection.id}: {collection.name}'))
            for external_file in get_all_read_permitted_records(current_user, ExternalFile):
                if external_file.file_exists():
                    self.select_options.append(SelectOption(external_file.filename,
                                                            f'External File {external_file.id}: {external_file.name}'))


class JobOutputEntry:
    def __init__(self, wf_output):
        self.id = wf_output['id']
        self.input_type = wf_output['type']
        self.label = wf_output['label'] if 'label' in wf_output else wf_output['id']
        self.doc = wf_output['doc'] if 'doc' in wf_output else ''


class SubmitFormData:
    def __init__(self, current_user: User, workflow: Dict[str, Any], label: str):
        self.label = label
        self.inputs = []
        self.outputs = []
        self.current_user = current_user
        self.creates_files = False
        for wf_input in workflow['inputs']:
            self.inputs.append(JobInputEntry(wf_input, current_user))
        for wf_output in workflow['outputs']:
            self.outputs.append(JobOutputEntry(wf_output))
            if wf_output['type'].startswith('File'):
                self.creates_files = True
        if self.creates_files:
            self.create_form_data = CreateFormData(current_user, 'Result File', '_')
            analysis_options = [
                SelectOption(analysis.id, f'{analysis.id}: {analysis.name}') for analysis in get_analyses(current_user)
            ]

            self.create_form_data.entries.append(FormEntry('_groupWriteCheckbox', '_group_can_write',
                                                           'User group members can edit or delete?', True, 'checkbox'))
            self.create_form_data.entries.append(FormEntry('_analysisSelect', '_analysis_ids', 'Analyses',
                                                           input_type='select', select_options=analysis_options,
                                                           select_multiple=True))
        else:
            self.create_form_data = None


class CreateFormData:
    def __init__(self, current_user: User, label: str, prefix=''):
        self.label = label
        user_group_options = [SelectOption('', 'None', current_user.primary_user_group is None)] + \
                             [SelectOption(user_group.id,
                                           user_group.name,
                                           user_group is current_user.primary_user_group)
                              for user_group in get_included_groups(current_user, current_user)]
        self.entries = [
            FormEntry(f'{prefix}nameInput', f'{prefix}name', 'Name', 'Enter name'),
            FormEntry(f'{prefix}descriptionTextArea', f'{prefix}description', 'Description', 'Enter description',
                      'textarea'),
            FormEntry(f'{prefix}userGroupSelect', f'{prefix}user_group_id', 'User Group', '', 'select',
                      select_options=user_group_options),
            FormEntry(f'{prefix}allReadCheckbox', f'{prefix}all_can_read', 'Anyone can view?', True, 'checkbox'),
            FormEntry(f'{prefix}groupReadCheckbox', f'{prefix}group_can_read', 'User group members can view?', True,
                      'checkbox'),
            FormEntry(f'{prefix}allWriteCheckbox', f'{prefix}all_can_write', 'Anyone can edit or delete?', False,
                      'checkbox')
        ]


class AnalysisCreateFormData(CreateFormData):
    def __init__(self, current_user: User, selected_collections: List[Collection]=None):
        if selected_collections is None:
            selected_collections = []
        super(AnalysisCreateFormData, self).__init__(current_user, 'Create Analysis')
        self.entries.append(FormEntry('groupWriteCheckbox', 'group_can_write',
                                      'User group members can edit or delete?', True, 'checkbox'))
        collection_options = [
            SelectOption(collection.id, f'{collection.id}: {collection.name}', collection in selected_collections)
            for collection in get_collections(current_user)]
        self.entries.append(FormEntry('collectionSelect', 'collection_ids', 'Collections', input_type='select',
                                      select_options=collection_options, select_multiple=True))


class ExternalFileCreateFormData(CreateFormData):
    def __init__(self, current_user: User):
        super(ExternalFileCreateFormData, self).__init__(current_user, 'Create External File Record')
        self.entries.append(
            FormEntry('filenameInput', 'filename', f'Filename (relative to {DATADIR}/external/)', 'Enter filename'))
        self.entries.append(FormEntry('fileInput', 'file', 'File', input_type='file', select_multiple=False))


class CollectionCreateFormData(CreateFormData):
    def __init__(self, current_user: User, selected_samples: List[Sample] = None):
        if selected_samples is None:
            selected_samples = []
        super(CollectionCreateFormData, self).__init__(current_user, 'Create Collection')
        self.entries.append(FormEntry('groupWriteCheckbox', 'group_can_write',
                                      'User group members can edit or delete?', False, 'checkbox'))
        sample_options = [SelectOption(sample.id, f'{sample.id}: {sample.name}', sample in selected_samples)
                          for sample in get_samples(current_user)]
        sort_by_options = [SelectOption('base_sample_id', 'Sample ID', True)]
        if len(selected_samples):
            common_attributes = [key for key in selected_samples[0].get_file_attributes().keys()
                                 if all([key in sample.get_file_attributes() for sample in selected_samples])]
            sort_by_options = sort_by_options + [SelectOption(attr, attr, False) for attr in common_attributes]
        self.entries.append(FormEntry('sampleSelect', 'sample_ids', 'Samples', input_type='select',
                                      select_options=sample_options, select_multiple=True))
        self.entries.append(FormEntry('sortBySelect', 'sort_by', 'Sort By', input_type='select',
                                      select_options=sort_by_options))


class SampleCreateFormData(CreateFormData):
    def __init__(self, current_user: User):
        super(SampleCreateFormData, self).__init__(current_user, 'Create Sample Group')
        self.entries.append(FormEntry('groupWriteCheckbox', 'group_can_write',
                                      'User group members can edit or delete?', False, 'checkbox'))
        self.entries.append(FormEntry('fileInput', 'files', 'Files', input_type='file', select_multiple=True))
        parser_options = [SelectOption(module.path, module.label) for module in get_parsing_modules()]
        preproc_options = [SelectOption(module.path, module.label) for module in get_preprocessing_modules()]
        self.entries.append(FormEntry('parserSelect', 'parser', 'Parser (File Format)', input_type='select',
                                      select_options=parser_options))
        self.entries.append(FormEntry('preprocSelect', 'preproc', 'Preprocessor (Data Format)', input_type='select',
                                      select_options=preproc_options))


class WorkflowCreateFormData(CreateFormData):
    def __init__(self, current_user: User):
        super(WorkflowCreateFormData, self).__init__(current_user, 'Create Workflow')
        self.entries.append(FormEntry('groupWriteCheckbox', 'group_can_write',
                                      'User group members can edit or delete?', False, 'checkbox'))


class UserGroupCreateFormData:
    def __init__(self, current_user: User, selected_users: List[User]=None):
        self.label = 'Create User Group'
        if selected_users is None:
            selected_users = []
        self.entries = [
            FormEntry('nameInput', 'name', 'Name', 'Enter name',),
            FormEntry('descriptionTextArea', 'description', 'Description', 'Enter description', 'textarea')
        ]
        user_options = [SelectOption(user.id, user.name, user in selected_users) for user in get_users(current_user)]
        admin_options = [SelectOption(user.id, user.name, user.id == current_user.id)
                         for user in get_users(current_user)]
        self.entries.append(FormEntry('memberSelect', 'member_ids', 'Members (you will be a member))',
                                      input_type='select', select_options=user_options, select_multiple=True))
        self.entries.append(FormEntry('adminSelect', 'admin_ids', 'Admins (you will be an admin)',
                                      input_type='select', select_options=admin_options, select_multiple=True))


class RegisterFormData:
    def __init__(self):
        self.label = 'Register New Account'
        self.entries = [
            FormEntry('emailInput', 'email', 'Email address', 'example@test.net', 'email'),
            FormEntry('nameInput', 'name', 'Name', 'A. Person'),
            FormEntry('passwordInput1', 'password1', 'New password', 'Password', 'password'),
            FormEntry('passwordInput2', 'password2', 'Repeat new password', 'Password', 'password')
        ]


class LoginFormData:
    def __init__(self):
        self.label = 'Login to Your Account'
        self.entries = [
            FormEntry('emailInput', 'email', 'Email address', 'example@test.net', 'email'),
            FormEntry('passwordInput', 'password', 'Password', 'Password', 'password')
        ]


class ProfileUpdateFormData:
    def __init__(self, current_user: User):
        self.label = 'Update Profile'
        theme_options = [
            SelectOption('dark', 'Dark', current_user.theme == 'dark'),
            SelectOption('light', 'Light', current_user.theme == 'light')
        ]
        self.entries = [
            FormEntry('emailInput', 'email', 'Email address', current_user.email, 'email'),
            FormEntry('nameInput', 'name', 'Name', current_user.name),
            FormEntry('themeInput', 'theme', 'Theme', input_type='select', select_options=theme_options, select_multiple=False),
            FormEntry('passwordInput1', 'password1', 'New password', 'Password', 'password'),
            FormEntry('passwordInput2', 'password2', 'Repeat new password', 'Password', 'password')
        ]


class PasswordResetFormData:
    def __init__(self):
        self.label = 'Change User Password'
        self.entries = [
            FormEntry('changeEmailInput', 'changeEmail', 'User\'s email address', 'email@example.com', 'email'),
            FormEntry('passwordInput1', 'changePassword1', 'New password', 'Password', 'password'),
            FormEntry('passwordInput2', 'changePassword2', 'Repeat new password', 'Password', 'password')
        ]


