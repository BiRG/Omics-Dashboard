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


def start_job(workflow: Dict[str, Any], job: Dict[str, Any], owner: int):
    """
    Start a new job on the Cromwell job server
    :param workflow:
    :param job:
    :param owner:
    :return:
    """
    auth_token = get_jwt_by_id(owner)
    job['authToken'] = auth_token
    labels = json.dumps({'owner': str(owner)})
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
    url = f'{COMPUTESERVER}/workflows/v1'
    response = requests.get(url)
    return response.json()


def get_job(job_id: str) -> Dict[str, Any]:
    """
    Get information about a job running on the Cromwell job server.
    :param job_id:
    :return:
    """
    url = f'{COMPUTESERVER}/workflows/v1/{job_id}/status'
    response = requests.get(url)
    return response.json()


def cancel_job(user_id: int, job_id: str) -> Dict[str, Any]:
    """
    Abort a running job on the Cromwell job server.
    :param user_id:
    :param job_id:
    :return:
    """
    data = json.loads(requests.get(f'{COMPUTESERVER}/workflows/v1/{job_id}/labels'))
    if data['owner'] == user_id or is_admin(user_id):
        response = requests.post(f'{COMPUTESERVER}/workflows/v1/{job_id}/abort')
        return response.json()
    raise AuthException('User %s is not authorized to resume job %s' % (str(user_id), str(job_id)))


def resume_job(user_id: int, job_id: str) -> Dict[str, Any]:
    """
    Release the hold on a job on the Cromwell job server.
    :param user_id:
    :param job_id:
    :return:
    """
    data = json.loads(requests.get(f'{COMPUTESERVER}/workflows/v1/{job_id}/labels'))
    if data['owner'] == user_id or data['owner'] < 0 or is_admin(user_id):
        response = requests.post(f'{COMPUTESERVER}/workflows/v1/{job_id}/releaseHold')
        return response.json()
    raise AuthException('User %s is not authorized to resume job %s' % (str(user_id), str(job_id)))


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


def check_jobserver_token(token: str):
    """Check if a jobserver token is in the database."""
    return db.query_db('select * from JobServerTokens where value = ?', [str(token)]) is not None
