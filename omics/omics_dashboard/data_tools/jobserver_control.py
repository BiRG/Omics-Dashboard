import json
import os
import uuid
from io import StringIO
from typing import Dict, Any, List

import requests
from ruamel import yaml as yaml

from data_tools.database import db
from data_tools.users import get_jwt_by_id, is_admin
from data_tools.util import AuthException, COMPUTESERVER, TMPDIR


def start_job(workflow: Dict[str, Any], job: Dict[str, Any], owner: int, wf_type: str) -> Dict[str, Any]:
    """
    Start a new job on the Cromwell job server
    :param workflow:
    :param job:
    :param owner:
    :param wf_type: Either 'upload' or 'analysis'
    :return:
    """
    auth_token = get_jwt_by_id(owner)
    job['authToken'] = auth_token
    labels = json.dumps({'owner': str(owner), 'type': wf_type})
    files = {'workflowSource': StringIO(),
             'workflowInputs': StringIO(),
             'labels': labels}
    yaml.safe_dump(workflow, files['workflowSource'])
    yaml.safe_dump(job, files['workflowInputs'])
    files['workflowInputs'].seek(0)
    files['workflowSource'].seek(0)
    params = {'workflowType': 'CWL', 'workflowTypeVersion': 'v1.0'}
    url = f'{COMPUTESERVER}/api/workflows/v1'
    res = requests.post(url,
                        headers={'Authorization': auth_token},
                        data=params,
                        files=files)
    try:
        return res.json()
    except Exception:
        raise RuntimeError('Invalid response from job server. Is the server running?')


def get_jobs() -> List[Dict[str, Any]]:
    """
    Get the jobs list from the Cromwell job server.
    :return:
    """
    url = f'{COMPUTESERVER}/api/workflows/v1/query?labelor=type:upload&labelor=type:analysis'
    response = requests.get(url)
    job_data = response.json()['results']
    for entry in job_data:
        label_res = requests.get(f'{COMPUTESERVER}/api/workflows/v1/{entry["id"]}/labels')
        entry.update(label_res.json()['labels'])
    return job_data


def get_job(job_id: str) -> Dict[str, Any]:
    """
    Get information about a job running on the Cromwell job server.
    :param job_id:
    :return:
    """
    job_url = f'{COMPUTESERVER}/api/workflows/v1/query?id={job_id}'
    job_response = requests.get(job_url)
    job_data = job_response.json()['results'][0]
    label_url = f'{COMPUTESERVER}/api/workflows/v1/{job_id}/labels'
    label_response = requests.get(label_url)
    label_data = label_response.json()['labels']
    job_data.update(label_data)
    # timing_url = f'{COMPUTESERVER}/api/workflows/v1/{job_id}/timing'
    # timing_response = requests.get(timing_url)
    # job_data['timing'] = timing_response.text
    return job_data


def cancel_job(user_id: int, job_id: str) -> Dict[str, Any]:
    """
    Abort a running job on the Cromwell job server.
    :param user_id:
    :param job_id:
    :return:
    """
    data = json.loads(requests.get(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/labels'))
    if data['owner'] == user_id or is_admin(user_id):
        response = requests.post(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/abort')
        return response.json()
    raise AuthException(f'User {user_id} is not authorized to resume job {job_id}')


def resume_job(user_id: int, job_id: str) -> Dict[str, Any]:
    """
    Release the hold on a job on the Cromwell job server.
    :param user_id:
    :param job_id:
    :return:
    """
    data = json.loads(requests.get(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/labels'))
    if data['owner'] == user_id or data['owner'] < 0 or is_admin(user_id):
        response = requests.post(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/releaseHold')
        return response.json()
    raise AuthException(f'User {user_id} is not authorized to resume job {job_id}')


def create_jobserver_token() -> str:
    """
    Create a "jobserver token"

    The jobserver token is no longer used by the jobserver, but it is the name of a temporary directory where files
    that the jobserver can consume can be placed.
    :return:
    """
    token = str(uuid.uuid4())
    while token in os.listdir(f'{TMPDIR}'):
        token = str(uuid.uuid4())
    db.query_db('insert into JobServerTokens (value) values (?)', [str(token)])
    return token


def check_jobserver_token(token: str) -> bool:
    """
    Check if a jobserver token is in the database.
    :param token:
    :return:
    """
    return db.query_db('select * from JobServerTokens where value = ?', [str(token)]) is not None


def get_job_chart_metadata(job_id: str) -> str:
    """
    Get a string containing a javascript object used to draw the Gannt chart for a job's timing
    :param job_id:
    :return:
    """
    include_keys = ['start', 'end', 'executionStatus', 'executionEvents', 'subWorkflowMetadata']
    url = f'{COMPUTESERVER}/api/workflows/v1/{job_id}/metadata' \
          f'?expandSubWorkflows=true&includeKeys={"&includeKeys=".join(include_keys)}'
    response = requests.get(url)
    return response.json()


def prepare_workflow(workflow: Dict[str, any]) -> Dict[str, any]:
    workflow['inputs'].append(
        {
            'id': 'omicsAuthToken',
            'type': 'string'
        },
        {
            'id': 'omicsUrl',
            'type': 'string'
        }
    )
    for step in workflow['steps']:
        for
