import json
import os
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, Any, List

import requests
from ruamel import yaml as yaml

from data_tools.access_wrappers.external_files import create_external_file
from data_tools.access_wrappers.users import get_jwt
from data_tools.db_models import JobserverToken, User, db
from data_tools.util import AuthException, COMPUTESERVER, TMPDIR, NotFoundException, OMICSSERVER, DATADIR


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
        self.submission = datetime.utcfromtimestamp(0)
        self.start = datetime.utcfromtimestamp(0)
        self.end = datetime.utcfromtimestamp(0)
        self.status = None
        self.all_can_read = True
        self.all_can_write = False
        self.group_can_read = True
        self.group_can_write = False
        self.logs = {}
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
        self.submission = datetime.strptime(job_data['submission'],
                                            '%Y-%m-%dT%H:%M:%S.%fZ') if 'submission' in job_data else None
        self.start = datetime.strptime(job_data['start'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'start' in job_data else None
        self.end = datetime.strptime(job_data['end'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'end' in job_data else None
        self.status = job_data['status'] if 'status' in job_data else None
        self.active = True

    def get_flattened_logs(self):
        self.get_logs()
        try:
            return {
                f'{key}.{inner_key}': inner_value
                for key, value in self.logs.items()
                for inner_key, inner_value in value.items()
            }
        except Exception:
            return {}

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

    def get_logs(self):
        log_response = requests.get(f'{COMPUTESERVER}/api/workflows/v1/{self.id}/logs')
        try:
            self.logs = {
                key: {'stderr': open(value[0]['stderr']).read(), 'stdout': open(value[0]['stdout']).read()}
                for key, value in log_response.json()['calls'].items()}
        except:
            self.logs = log_response.json()

    def to_dict(self):
        self.get_logs()
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'user_group_id': self.user_group.id if self.user_group is not None else None,
            'type': self.type,
            'submission': self.submission,
            'start': self.start,
            'end': self.end,
            'status': self.status,
            'logs': self.logs
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


def start_job(workflow: Dict[str, Any], job_params: Dict[str, Any], owner: User, wf_type='upload', labels=None,
              options=None) -> Job:
    """
    Start a new job on the Cromwell job server
    :param workflow:
    :param job_params:
    :param owner:
    :param wf_type: Either 'upload' or 'analysis'
    :return:
    """
    options = options or {}
    labels = labels or {}
    auth_token = get_jwt(owner)
    job_params['omics_auth_token'] = auth_token
    job_params['omics_url'] = OMICSSERVER
    labels.update({'owner_id': str(owner.id), 'type': wf_type})
    files = {'workflowSource': StringIO(),
             'workflowInputs': StringIO(),
             'labels': json.dumps(labels),
             'workflowOptions': json.dumps(options)}
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
    res_text = ''
    try:
        res_text = res.text
        res.raise_for_status()
        return Job(res.json()['id'])
    except Exception:
        raise RuntimeError(f'Invalid response from job server. Is the server running? \n Response: {res_text}')


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
    raise AuthException(f'User {user.email} is not authorized to cancel job {job.id}')


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
    raise AuthException(f'User {user.email} is not authorized to resume job {job.id}')


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


def prepare_job_params(workflow_data, form_data, current_user, workflow_id):
    """
    Insert server-related parameters to workflow job
    :param workflow_data: The CWL workflow definition
    :param form_data: data to use as inputs.
    :param current_user: current user to own created external files
    :param workflow_id: id of the workflow (used for file naming purposes)
    :return: form_data, but corrected.
    """
    form_data = form_data.copy()
    workflow_data = workflow_data.copy()

    # outputs will create external files if they are files.
    def process_bool(val):
        return val.lower() == 'true'

    def token_with_escape(a):
        result = []
        token = ''
        state = 0
        for c in a:
            if state == 0:
                if c == '\\':
                    state = 1
                elif c == ',':
                    result.append(token)
                    token = ''
                else:
                    token += c
            elif state == 1:
                token += c
                state = 0
        result.append(token)
        return result

    def process_multiple(value, value_type):
        if value_type == str:
            return token_with_escape(value)
        return [value_type(val) for val in value.split(',')]

    for wf_input in workflow_data['inputs']:
        if wf_input['id'] == 'omics_url':
            form_data['omics_url'] = None  # set by job submission function
        elif wf_input['id'] == 'omics_auth_token':
            form_data['omics_auth_token'] = None
        elif wf_input['type'].endswith('[]') and not (
                wf_input['type'].startswith('File') or wf_input['type'].startswith('Directory')):
            if wf_input['type'].startswith('boolean'):
                type_ = process_bool
            elif wf_input['type'].startswith('float') or wf_input['type'].startswith('double'):
                type_ = float
            elif wf_input['type'].startswith('int') or wf_input['type'].startswith('long'):
                type_ = int
            else:
                type_ = str
            form_data[wf_input['id']] = process_multiple(form_data[wf_input['id']], type_)
    labels = {}
    # create an external file record for all the outputs
    if 'outputs' in workflow_data and len(workflow_data['outputs']):
        metadata_keys = ['analysis_ids', 'name', 'description', 'user_group_id', 'all_can_read', 'group_can_read',
                         'all_can_write', 'group_can_write']
        output_dir = os.path.join(DATADIR, 'external', f'workflow_{workflow_id}', str(uuid.uuid4()))
        Path(output_dir).mkdir(parents=True)
        file_metadata = {'filename': output_dir}
        for key in metadata_keys:
            if f'_{key}' in form_data:
                file_metadata[key] = form_data[f'_{key}']
                del form_data[f'_{key}']
        external_file = create_external_file(current_user, file_metadata)
        labels['output_file_record_id'] = str(external_file.id)
        form_data['outputs'] = {}
        for wf_output in workflow_data['outputs']:
            if 'outputSource' in wf_output:
                if isinstance(wf_output['outputSource'], list):
                    wf_output['outputSource'] = wf_output['outputSource'][0]
            form_data['outputs'][wf_output['id']] = {'outputDir': output_dir}
        options = {
            'final_workflow_outputs_dir': f'file://{output_dir}',
            'use_relative_output_paths': True
        }
    else:
        options = {}
    return form_data, workflow_data, labels, options
