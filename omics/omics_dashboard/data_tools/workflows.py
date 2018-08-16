import os
from typing import List, Dict, Any

import ruamel.yaml as yaml
import json

from data_tools.database import db
from data_tools.users import is_read_permitted, is_write_permitted
from data_tools.util import AuthException, DATADIR, MODULEDIR
workflow_template = {}


def get_workflows(user_id: int) -> List[Dict[str, Any]]:
    """
    Get a list of available saved workflows.
    :param user_id:
    :return:
    """
    results = db.query_db('select * from Workflows;')
    return [result for result in results if is_read_permitted(user_id, result)]


def get_workflow(user_id: int, workflow_id: int) -> Dict[str, Any]:
    """
    Get workflow metadata.
    :param user_id:
    :param workflow_id:
    :return:
    """
    result = db.query_db('select * from Workflows where id=?;', [str(workflow_id)], True)
    if is_read_permitted(user_id, result):
        return result
    raise AuthException('User %s is not permitted to access analysis %s' % (str(user_id), str(workflow_id)))


def update_workflow(user_id: int, workflow_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update workflow metadata.
    :param user_id:
    :param workflow_id:
    :param new_data:
    :return:
    """
    analysis = db.query_db('select * from Workflows where id=?;', str(workflow_id), True)
    valid_keys = ['name', 'description', 'groupPermissions', 'allPermissions', 'userGroup']
    if is_write_permitted(user_id, analysis):
        query = 'update Analyses set ' \
                + ','.join([' %s = ?' % key for key, value in new_data.items() if key in valid_keys]) \
                + ' where id=?;'
        params = []
        [params.append(str(value)) for key, value in new_data.values() if key in valid_keys]
        params.append(str(workflow_id))
        db.query_db(query, params)
        return db.query_db('select * from Workflows where id=?;', [str(workflow_id)], True)
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(workflow_id)))


def create_workflow(user_id: int, data: Dict[str, Any]):
    """
    Create a new workflow.
    :param user_id:
    :param data:
    :return:
    """
    db.query_db('insert into Workflows '
                '(name, description, createdBy, owner, groupPermissions, allPermissions, userGroup)'
                'values (?, ?, ?, ?, ?, ?, ?);',
                [str(data['name']), str(data['description']), str(user_id), str(user_id), str(data['groupPermissions']),
                 str(data['allPermissions']), str(data['userGroup'])],
                True)
    workflow = db.query_db('select * from Workflows where id=last_insert_rowid()', (), True)
    filename = f'{DATADIR}/workflows/{workflow["id"]}.cwl'
    workflow_data = data['workflow'] if 'workflow' in data else workflow_template
    yaml.safe_dump(workflow_data, open(filename, 'w'))
    return workflow


def delete_workflow(user_id: int, workflow_id: int) -> Dict[str, str]:
    """
    Delete a workflow from the database and filesystem
    :param user_id:
    :param workflow_id:
    :return:
    """
    analysis = db.query_db('select * from Workflows where id=?;', str(workflow_id), True)
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from Workflows where id=?;', [str(workflow_id)])
        db.query_db('delete from WorkflowMemberships where workflowId=?;', [str(workflow_id)])
        os.remove(f'{DATADIR}/workflows/{workflow_id}.cwl')
        return {'message': 'analysis ' + str(workflow_id) + ' deleted'}
    raise AuthException('User %s is not permitted to modify analysis %s' % (str(user_id), str(workflow_id)))


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
        for file in files:
            if os.path.splitext(file)[1] == '.cwl':
                path = os.path.join(module_path, directory, file)
                tool_def = get_module(path)
                module = {
                    'packageName': dir_info['name'],
                    'label': tool_def['label'] if 'label' in tool_def else '',
                    'description': tool_def['doc'] if 'doc' in tool_def else '',
                    'package': main_package,
                    'path': tool_def['modulePath'],
                    'subPackage': package,
                    'subPackageDescription': package_description,
                    'toolDefinition': tool_def
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
        data['modulePath'] = path
        return data


def get_module_by_id(basepath: str, module_id: int) -> Dict[str, Any]:
    """
    Get a CWL CommandLineTool with a particular id definition as a dictionary.
    :param basepath:
    :param module_id:
    :return:
    """
    yaml_files = [f for f in os.listdir(basepath) if os.path.isfile(os.path.join(basepath, f))
                  and os.path.splitext(f)[-1] == 'cwl']
    for f in yaml_files:
        wf_module = get_module(f)
        if wf_module['id'] == module_id:
            return wf_module
    raise ValueError(f'Module with id {module_id} does not exist in {basepath}')
