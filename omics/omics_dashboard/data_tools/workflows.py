import json
import os
from datetime import datetime
from typing import List, Dict, Any

from ruamel import yaml

from data_tools.db import User, Workflow, db
from data_tools.users import is_read_permitted, is_write_permitted, get_all_read_permitted_records
from data_tools.util import AuthException, NotFoundException, DATADIR, MODULEDIR


class WorkflowModule:
    def __init__(self,
                 path: str,
                 package_name: str,
                 package_description: str,
                 subpackage_name: str,
                 subpackage_description: str):
        self.path = path
        self.package_name = package_name
        self.package_description = package_description
        self.subpackage_name = subpackage_name
        self.subpackage_description = subpackage_description

        tool_definition = self.get_workflow_module_contents()
        self.label = tool_definition['label'] if 'label' in tool_definition else os.path.basename(path)
        self.description = tool_definition['doc'] if 'doc' in tool_definition else os.path.basename(path)
        self.id = tool_definition['id'] if 'id' in tool_definition else path
        self.name = self.id

        self.all_can_read = True
        self.all_can_write = True
        self.group_can_read = True
        self.group_can_write = True

    def get_workflow_module_contents(self, as_text=False):
        with open(self.path, 'r') as stream:
            data = yaml.safe_load(stream)
            if 'cwlVersion' not in data:
                raise ValueError('Not a CWL file')
            if as_text:
                stream.seek(0)
                return stream.read()
            return data

    def to_dict(self):
        return {
            'id': self.id,
            'path': self.path,
            'label': self.label,
            'description': self.description,
            'package': self.package_name,
            'package_description': self.package_description,
            'subpackage': self.subpackage_name,
            'subpackage_description': self.subpackage_description,
            'tool_definition': self.get_workflow_module_contents(),
            'created_on': datetime.fromtimestamp(os.path.getctime(self.path)).isoformat(),
            'updated_on': datetime.fromtimestamp(os.path.getmtime(self.path)).isoformat()
        }


def get_workflow_template(name: str, description: str, workflow_id: int) -> Dict[str, Any]:
    return {
        'class': 'Workflow',
        'cwlVersion': 'v1.0',
        'label': name,
        'doc': description,
        'id': f'workflow{workflow_id}',
        'inputs': [],
        'outputs': [],
        'steps': []
    }


def get_workflows(user: User) -> List[Workflow]:
    """
    Get a list of available saved workflows.
    :param user:
    :return:
    """
    return get_all_read_permitted_records(user, Workflow)


def get_workflow(user: User, workflow_id: int) -> Workflow:
    """
    Get workflow metadata.
    :param user:
    :param workflow_id:
    :return:
    """
    workflow = Workflow.query.filter_by(id=workflow_id).first()
    if workflow is None:
        raise NotFoundException(f'No workflow with id {workflow_id}.')
    if is_read_permitted(user, workflow):
        return workflow
    raise AuthException(f'User {user.email} is not permitted to access workflow {workflow_id}')


def update_workflow(user: User, workflow: Workflow, new_data: Dict[str, Any]) -> Workflow:
    """
    Update workflow metadata.
    :param user:
    :param workflow:
    :param new_data:
    :return:
    """
    if is_write_permitted(user, workflow):
        if 'id' in new_data:
            if Workflow.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'Workflow with id {new_data["id"]} already exists!')
        workflow.update(new_data)
        if 'workflow_definition' in new_data:
            if workflow.file_type == 'json':
                json.dump(new_data['workflow_definition'], open(workflow.filename, 'w+'))
            elif workflow.file_type == 'yaml':
                yaml.dump(new_data['workflow_definition'], open(workflow.filename, 'w+'))
            else:
                open(workflow.filename, 'w+').write(new_data['workflow_definition'])
        db.session.commit()
        return workflow
    raise AuthException(f'User {user.email} is not permitted to modify workflow {workflow.id}')


def create_workflow(user: User, data: Dict[str, Any]) -> Workflow:
    """
    Create a new workflow.
    :param user:
    :param data:
    :return:
    """
    if 'id' in data:  # cannot create with designated id
        del data['id']
    workflow = Workflow(creator=user, owner=user, last_editor=user, name=data['name'])
    db.session.add(workflow)
    db.session.commit()
    workflow.filename = f'{DATADIR}/workflows/{workflow.id}.{workflow.workflow_language}'
    print(workflow.filename)
    db.session.commit()
    if 'workflow_definition' not in data:
        data['workflow_definition'] = get_workflow_template(workflow.name,
                                                 data['description'] if 'description' in data else '',
                                                 workflow.id)
    with open(workflow.filename, 'w+') as file:
        if workflow.file_type == 'json':
            json.dump(data['workflow_definition'], file)
        elif workflow.file_type == 'yaml':
            yaml.dump(data['workflow_definition'], file)
        else:
            file.write(data['workflow_definition'])

    for key, value in data.items():
        if key in workflow.to_dict() and key is not 'filename':
            workflow.__setattr__(key, value)
    db.session.commit()
    return workflow


def delete_workflow(user: User, workflow: Workflow) -> Dict[str, str]:
    """
    Delete a workflow from the database and filesystem
    :param user:
    :param workflow:
    :return:
    """
    if is_write_permitted(user, workflow):
        workflow_id = workflow.id
        db.session.delete(workflow)
        db.session.commit()
        return {'message': f'Workflow {workflow_id} deleted.'}
    raise AuthException(f'User {user.email} is not permitted to modify analysis {workflow.id}')


def get_tool_definition(path: str) -> Dict[str, Any]:
    with open(path, 'r') as stream:
        data = yaml.safe_load(stream)
        if 'cwlVersion' not in data:
            raise yaml.YAMLError('Not a CWL file')
        data['module_path'] = path
        return data


def get_modules(module_path: str=None) -> List[WorkflowModule]:
    """
    Get available modules for use in workflows.
    :return:
    """
    module_path = MODULEDIR if module_path is None else module_path
    modules = []
    # find packages
    for directory, subdirectories, files in os.walk(module_path):
        dir_info = {}
        if 'info.json' in files:
            dir_info = json.load(open(os.path.join(directory, 'info.json')))
        if 'name' not in dir_info:
            dir_info['name'] = directory
        package_name = dir_info['name']
        package_description = dir_info['description'] if 'description' in dir_info else ''
        for filename in files:  # this is for files that are one directory deep
            if os.path.splitext(filename)[1] == '.cwl':
                path = os.path.join(directory, filename)
                tool_def = get_tool_definition(path)
                modules.append(WorkflowModule(path, package_name, package_description, '', ''))
        # Find subpackages
        for subdirectory in subdirectories:
            for _, subsubdirectories, subfiles in os.walk(subdirectory):
                subdir_info = {}
                if 'info.json' in subfiles:
                    subdir_info = json.load(open(os.path.join(directory, subdirectory, 'info.json')))
                if 'name' not in dir_info:
                    subdir_info['name'] = subdirectory
                subpackage_name = subdir_info['name']
                subpackage_description = subdir_info['description'] if 'description' in dir_info else ''
                for filename in subfiles:
                    if os.path.splitext(filename)[1] == '.cwl':
                        path = os.path.join(module_path, directory, filename)
                        tool_def = get_tool_definition(path)
                        modules.append(WorkflowModule(path, package_name, package_description, subpackage_name,
                                                      subpackage_description))
    return modules


def get_module(path: str) -> WorkflowModule:
    """
    Get CWL CommandLineTool definition as a dictionary.
    :param path:
    :return:
    """
    directory = os.path.dirname(path)  # a full path
    parent_dir = os.path.dirname(os.path.dirname(path))  # a full path

    # We try to find info.json in both paths. It's ok to not find it here, but if we can't find it in parent, we assume
    # current dir is a "package" and that this module belongs to no subpackages
    subdir_info_file = os.path.join(directory, 'info.json')
    subdir_info = json.load(open(subdir_info_file, 'r')) if os.path.isfile(subdir_info_file) \
        else {'name': os.path.basename(os.path.dirname(directory))}

    parent_dir_info_file = os.path.join(parent_dir, 'info.json')
    parent_dir_info = json.load(open(parent_dir_info_file, 'r')) if os.path.isfile(parent_dir_info_file) \
        else {'name': os.path.basename(os.path.dirname(parent_dir))}

    package_name = parent_dir_info['name'] if os.path.isfile(parent_dir_info_file) else subdir_info['name']
    package_description = parent_dir_info['description'] if 'description' in parent_dir_info \
        else subdir_info['description'] if 'description' in subdir_info else ''

    subpackage_name = subdir_info['name'] if os.path.isfile(parent_dir_info_file) else ''
    subpackage_description = \
        subdir_info['description'] if os.path.isfile(parent_dir_info_file) and 'description' in subdir_info else ''

    tool_def = yaml.safe_load(open(path, 'r'))
    if 'cwlVersion' not in tool_def:
        raise ValueError('Not a CWL file')
    return WorkflowModule(path, package_name, package_description, subpackage_name, subpackage_description)


def get_module_by_id(module_id: str, module_path: str = None) -> WorkflowModule:
    modules = get_modules(module_path)
    val = next((module for module in modules if module.id == module_id), None) if module_id is not None else None
    if val is None:
        raise ValueError(f'Module with id {module_id} not found in {module_path} or immediate subdirectories.')
    return val

