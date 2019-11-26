import json
import os
from typing import List, Dict, Any

from data_tools.access_wrappers.jobserver_control import create_jobserver_token
from data_tools.access_wrappers.samples import create_placeholder_samples
from data_tools.access_wrappers.users import get_jwt
from data_tools.access_wrappers.workflows import get_modules, WorkflowModule
from data_tools.db_models import User
from data_tools.config import TMPDIR, DATADIR, MODULEDIR


def create_sample_creation_workflow(user: User, input_filenames: List[str], metadata: Dict[str, Any]):
    """
    Create a CWL workflow for the sample upload process.
    :param user:
    :param input_filenames:
    :param metadata:
    :return:
    """
    # generate tmpdir for this temporary workflow
    new_metadata = dict(metadata)
    token = create_jobserver_token()
    directory = f'{TMPDIR}/{token.value}'
    os.mkdir(directory)
    metadata_filename = f'{directory}/metadata.json'
    metadata['sample_group_name'] = metadata['name']
    del metadata['name']
    with open(metadata_filename, 'w') as file:
        json.dump(new_metadata, file)
    with open(f'{directory}/wfdata.json', 'w') as file:
        json.dump({'owner': user.id}, file)
    new_filenames = [f'{directory}/{os.path.basename(input_filename)}' for input_filename in input_filenames]
    [os.rename(input_filename, new_filename) for input_filename, new_filename in zip(input_filenames, new_filenames)]
    prefix = new_metadata['name']
    new_metadata['name'] = f'PLACEHOLDER <{prefix}>'
    placeholder_samples = create_placeholder_samples(user, new_metadata, len(input_filenames))
    del new_metadata['name']
    workflow = {
        'cwlVersion': 'v1.0',
        'class': 'Workflow',
        'inputs':
            [
                {
                    'id': 'input_files',
                    'type': 'File[]'
                },
                {
                    'id': 'metadata_file',
                    'type': 'File'
                },
                {
                    'id': 'data_directory',
                    'type': 'Directory'
                },
                {
                    'id': 'prefix',
                    'type': 'string'
                },
                {
                    'id': 'first_id',
                    'type': 'int'
                },
                {
                    'id': 'omics_auth_token',
                    'type': 'string'
                },
                {
                    'id': 'wf_token',
                    'type': 'string'
                },
                {
                    'id': 'omics_url',
                    'type': 'string'
                }
            ],
        'outputs':
            [
                {
                    'id': 'responses',
                    'outputSource': 'update/responses',
                    'type': 'string'
                }
            ],
        'steps':
            [
                {
                    'id': 'parse',
                    'run': new_metadata["parser"],
                    'in': [
                        {
                            'id': 'input_files',
                            'source': 'input_files'
                        },
                        {
                            'id': 'prefix',
                            'source': 'prefix'
                        }
                    ],
                    'out': [{'id': 'output_files'}]
                },
                {
                    'id': 'process',
                    'run': new_metadata["preproc"],
                    'in': [
                        {
                            'id': 'input_files',
                            'source': 'parse/output_files'
                        }
                    ],
                    'out': [{'id': 'output_files'}]
                },
                {
                    'id': 'update',
                    'run': f'{MODULEDIR}/omics-service/upload_samples.cwl',
                    'in':
                        [
                            {'id': 'input_files',
                             'source': 'process/output_files'},
                            {'id': 'metadata_file',
                             'source': 'metadata_file'},
                            {'id': 'id_start',
                             'source': 'first_id'},
                            {'id': 'wf_token',
                             'source': 'wf_token'},
                            {'id': 'omics_url',
                             'source': 'omics_url'},
                            {'id': 'auth_token',
                             'source': 'omics_auth_token'}
                        ],
                    'out': [{'id': 'responses'}]
                }
            ]
    }
    job = {
        'input_files': [{'path': filename, 'class': 'File'} for filename in new_filenames],
        'metadata_file': {'path': metadata_filename,
                          'class': 'File'},
        'data_directory': {'path': f'{DATADIR}/samples',
                           'class': 'Directory'},
        'prefix': prefix,
        'first_id': min([sample.id for sample in placeholder_samples]),
        'omics_auth_token': get_jwt(user),
        'wf_token': token.value,
        'omics_url': os.environ['OMICSSERVER']
    }
    # perhaps move execution here?
    return {'workflow': workflow, 'job': job, 'output_ids': [sample.id for sample in placeholder_samples]}


def get_preprocessing_modules() -> List[WorkflowModule]:
    """
    Get modules used for the preprocessing step of the sample upload process
    :return:
    """
    return get_modules(f'{MODULEDIR}/sample-processing')


def get_parsing_modules() -> List[WorkflowModule]:
    """
    Get the modules which may be used for the parsing step of the sample upload process
    :return:
    """
    return get_modules(f'{MODULEDIR}/sample-parsing')
