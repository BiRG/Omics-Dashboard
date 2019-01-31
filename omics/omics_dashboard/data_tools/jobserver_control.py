import json
import os
import uuid
from io import StringIO
from typing import Dict, Any, List

import requests
from ruamel import yaml as yaml

from data_tools.db import JobserverToken, User, Workflow, db
from data_tools.users import get_jwt
from data_tools.util import AuthException, COMPUTESERVER, TMPDIR, NotFoundException
import time


class Job:
    """
    Used for equivalence to the ORM models
    """
    def __init__(self, job_id):
        self.id = job_id
        self.name = f'Job {job_id}'
        # load lazily with refresh() because of jobserver delay
        self.owner_id = None
        self.owner = None
        self.user_group = None
        self.type = None
        self.submission = None
        self.start = None
        self.end = None
        self.status = None
        self.all_can_read = True
        self.all_can_write = False
        self.group_can_read = True
        self.group_can_write = False
        try:
            self.refresh()
        except NotFoundException:
            self.active = False

    def refresh(self):
        label_response = requests.get(f'{COMPUTESERVER}/api/workflows/v1/{self.id}/labels')
        if label_response.status_code == 404 or label_response.status_code == 400:
            raise NotFoundException(f'No job with id {self.id} found on jobserver.')
        label_response.raise_for_status()
        label_data = label_response.json()['labels']
        job_response = requests.get(f'{COMPUTESERVER}/api/workflows/v1/query?id={self.id}')
        job_data = job_response.json()['results'][0] if len(job_response.json()['results']) else {}
        job_data.update(label_data)
        self.owner_id = job_data['owner_id'] if 'owner_id' in job_data else None
        self.owner = User.query.filter_by(id=job_data['owner_id']).first() if 'owner_id' in job_data else None
        self.user_group = self.owner.primary_user_group if 'owner_id' in job_data else None
        self.type = job_data['type'] if 'type' in job_data else None
        self.submission = job_data['submission'] if 'submission' in job_data else None
        self.start = job_data['start'] if 'start' in job_data else None
        self.end = job_data['end'] if 'end' in job_data else None
        self.status = job_data['status'] if 'status' in job_data else None
        self.active = True

    def cancel(self):
        response = requests.post(f'{COMPUTESERVER}/api/workflows/v1/{self.id}/abort')
        return response.json()

    def resume(self):
        response = requests.post(f'{COMPUTESERVER}/api/workflows/v1/{self.id}/releaseHold')
        return response.json()

    def get_chart_metadata(self):
        include_keys = ['start', 'end', 'executionStatus', 'executionEvents', 'subWorkflowMetadata']
        url = f'{COMPUTESERVER}/api/workflows/v1/{self.id}/metadata' \
              f'?expandSubWorkflows=true&includeKeys={"&includeKeys=".join(include_keys)}'
        response = requests.get(url)
        return response.json()

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'user_group_id': self.user_group.id if self.user_group is not None else None,
            'type': self.type,
            'submission': self.submission,
            'start': self.start,
            'end': self.end,
            'status': self.status
        }


def get_jobs() -> List[Job]:
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
    return [Job(entry['id']) for entry in job_data]


def get_job(job_id: str) -> Job:
    """
    Get information about a job running on the Cromwell job server.
    :param job_id:
    :return:
    """
    return Job(job_id)  # can throw not found


def start_job(workflow: Dict[str, Any], job_params: Dict[str, Any], owner: User, wf_type='upload') -> Job:
    """
    Start a new job on the Cromwell job server
    :param workflow:
    :param job_params:
    :param owner:
    :param wf_type: Either 'upload' or 'analysis'
    :return:
    """
    auth_token = get_jwt(owner)
    job_params['authToken'] = auth_token
    labels = json.dumps({'owner_id': str(owner.id), 'type': wf_type})
    files = {'workflowSource': StringIO(),
             'workflowInputs': StringIO(),
             'labels': labels}
    yaml.safe_dump(workflow, files['workflowSource'])
    yaml.safe_dump(job_params, files['workflowInputs'])
    files['workflowInputs'].seek(0)
    files['workflowSource'].seek(0)
    params = {'workflowType': 'CWL', 'workflowTypeVersion': 'v1.0'}
    url = f'{COMPUTESERVER}/api/workflows/v1'
    res = requests.post(url,
                        headers={'Authorization': auth_token},
                        data=params,
                        files=files)
    try:
        return Job(res.json()['id'])
    except Exception:
        raise RuntimeError('Invalid response from job server. Is the server running?')


def cancel_job(user: User, job: Job) -> Dict[str, Any]:
    """
    Abort a running job on the Cromwell job server.
    :param user:
    :param job:
    :return:
    """
    job.refresh()
    if job.owner == user or user.admin:
        return job.cancel()
    raise AuthException(f'User {user.email} is not authorized to resume job {job.id}')


def resume_job(user: User, job: Job) -> Dict[str, Any]:
    """
    Release the hold on a job on the Cromwell job server.
    :param user:
    :param job:
    :return:
    """
    job.refresh()
    if job.owner == user or user.admin:
        return job.resume()
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


def get_job_chart_metadata(job: Job) -> str:
    """
    Get a string containing a javascript object used to draw the Gannt chart for a job's timing
    :param job:
    :return:
    """
    job.refresh()
    return job.get_chart_metadata()


def prepare_workflow(workflow: Dict[str, any]) -> Dict[str, any]:
    """
    Insert server-related parameters to workflow job
    :param workflow:
    :return:
    """
    workflow['inputs'].append(
        {
            'id': 'omics_auth_token',
            'type': 'string'
        },
        {
            'id': 'omics_url',
            'type': 'string'
        }
    )
    # TODO: do it
