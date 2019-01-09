import os
from typing import List, Dict, Any

import ruamel.yaml as yaml
import json

from data_tools.users import is_read_permitted, is_write_permitted, get_read_permitted_records
from data_tools.util import AuthException, DATADIR, MODULEDIR
from data_tools.db import User, Workflow, db


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
    return get_read_permitted_records(user, Workflow.query.all())


def get_workflow(user: User, workflow_id: int) -> Workflow:
    """
    Get workflow metadata.
    :param user:
    :param workflow_id:
    :return:
    """
    workflow = Workflow.query.filter_by(id=workflow_id).first()
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
        for key, value in new_data.items():
            if key in workflow.to_dict() and key is not 'filename':
                workflow.__setattr__(key, value)
        if 'workflow' in new_data:
            if workflow.file_type == 'json':
                json.dump(open(workflow.filename, 'w'), new_data['workflow'])
            elif workflow.file_type == 'yaml':
                yaml.dump(open(workflow.filename, 'w'), new_data['workflow'])
            else:
                open(workflow.filename, 'w').write(new_data['workflow'])
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
    workflow = Workflow(owner_id=user.id, creator_id=user.id)
    for key, value in data.items():
        if key in workflow.to_dict() and key is not 'filename':
            workflow.__setattr__(key, value)
    db.commit()
    workflow.filename = f'{DATADIR}/workflows/{workflow.id}.{workflow.workflow_language}'
    db.commit()
    if 'workflow' in data:
        if workflow.file_type == 'json':
            json.dump(open(workflow.filename, 'w'), data['workflow'])
        elif workflow.file_type == 'yaml':
            yaml.dump(open(workflow.filename, 'w'), data['workflow'])
        else:
            open(workflow.filename, 'w').write(data['workflow'])
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


def get_modules(module_path: str=None) -> List[Dict[str, Any]]:
    """
    Get available modules for use in workflows.
    :return:
    """
    module_path = MODULEDIR if module_path is None else module_path
    modules = []
    for directory, subdirectories, files in os.walk(module_path):
        dir_info = {}
        if 'info.json' in files:
            dir_info = json.load(open(os.path.join(module_path, directory, 'info.json')))
        if 'name' not in dir_info:
            dir_info['name'] = directory
        main_package = dir_info['package'] if 'package' in dir_info else None
        package = dir_info['name'] if 'name' in dir_info else None
        package_description = dir_info['description'] if 'description' in dir_info else None
        print('reading files')
        print(files)
        for filename in files:
            if os.path.splitext(filename)[1] == '.cwl':
                path = os.path.join(module_path, directory, filename)
                tool_def = get_module(path)
                module = {
                    'package_name': dir_info['name'],
                    'label': tool_def['label'] if 'label' in tool_def else '',
                    'description': tool_def['doc'] if 'doc' in tool_def else '',
                    'package': main_package,
                    'path': path,
                    'subpackage': package,
                    'subpackage_description': package_description,
                    'tool_definition': tool_def
                }
                modules.append(module)
    return modules


# noinspection PyTypeChecker
def get_module(path: str) -> Dict[str, Any]:
    """
    Get CWL CommandLineTool definition as a dictionary.
    :param path:
    :return:
    """
    with open(path, 'r') as stream:
        data = yaml.safe_load(stream)
        if 'cwlVersion' not in data:
            raise yaml.YAMLError('Not a CWL file')
        data['module_path'] = path
        return data


def get_module_by_id(base_path: str, module_id: int) -> Dict[str, Any]:
    """
    Get a CWL CommandLineTool with a particular id definition as a dictionary.
    :param base_path:
    :param module_id:
    :return:
    """
    yaml_files = [f for f in os.listdir(base_path) if os.path.isfile(os.path.join(base_path, f))
                  and os.path.splitext(f)[-1] == 'cwl']
    for f in yaml_files:
        wf_module = get_module(f)
        if wf_module['id'] == module_id:
            return wf_module
    raise ValueError(f'Module with id {module_id} does not exist in {base_path}')
