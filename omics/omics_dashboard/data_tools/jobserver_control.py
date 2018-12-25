import json
import os
import uuid
from io import StringIO
from typing import Dict, Any, List

import requests
from ruamel import yaml as yaml

from data_tools.db import JobserverToken, User, Workflow, db
from data_tools.users import get_jwt
from data_tools.util import AuthException, COMPUTESERVER, TMPDIR


def start_job(workflow: Dict[str, Any], job: Dict[str, Any], owner: User) -> Dict[str, Any]:
    """
    Start a new job on the Cromwell job server
    :param workflow:
    :param job:
    :param owner:
    :param wf_type: Either 'upload' or 'analysis'
    :return:
    """
    auth_token = get_jwt(owner)
    job['authToken'] = auth_token
    labels = json.dumps({'owner_id': str(owner.id), 'type': wf_type})
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


def cancel_job(user: User, job_id: str) -> Dict[str, Any]:
    """
    Abort a running job on the Cromwell job server.
    :param user:
    :param job_id:
    :return:
    """
    data = json.loads(requests.get(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/labels'))
    if data['owner_id'] == user.id or user.admin:
        response = requests.post(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/abort')
        return response.json()
    raise AuthException(f'User {user.email} is not authorized to resume job {job_id}')


def resume_job(user: User, job_id: str) -> Dict[str, Any]:
    """
    Release the hold on a job on the Cromwell job server.
    :param user_id:
    :param job_id:
    :return:
    """
    data = json.loads(requests.get(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/labels'))
    if data['owner'] == user.id or data['owner_id'] < 0 or user.admin:
        response = requests.post(f'{COMPUTESERVER}/api/workflows/v1/{job_id}/releaseHold')
        return response.json()
    raise AuthException(f'User {user.email} is not authorized to resume job {job_id}')


def create_jobserver_token() -> JobserverToken:
    """
    Create a "jobserver token"

    The jobserver token is no longer used by the jobserver, but it is the name of a temporary directory where files
    that the jobserver can consume can be placed.
    :return:
    """
    token = JobserverToken(value=str(uuid.uuid4()))
    while token.value in os.listdir(f'{TMPDIR}'):
        token = JobserverToken(value=str(uuid.uuid4()))
    db.session.add(token)
    db.session.commit()
    return token


def check_jobserver_token(token: str) -> bool:
    """
    Check if a jobserver token is in the database.
    :param token:
    :return:
    """
    return JobserverToken.query.filter_by(value=token).first() is not None


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
    """
    Insert server-related parameters to workflow job
    :param workflow:
    :return:
    """
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
    # TODO: do it
