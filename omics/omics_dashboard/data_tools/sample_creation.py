import json
import os
from typing import List, Dict, Any

from data_tools.samples import create_placeholder_samples
from data_tools.users import get_jwt_by_id
from data_tools.workflows import get_modules
from data_tools.jobserver_control import create_jobserver_token
from data_tools.util import TMPDIR, DATADIR, MODULEDIR


def create_sample_creation_workflow(user_id: int, input_filenames: List[str], metadata: Dict[str, Any]):
    """
    Create a CWL workflow for the sample upload process.
    :param user_id:
    :param input_filenames:
    :param metadata:
    :return:
    """
    # generate tmpdir for this temporary workflow
    new_metadata = dict(metadata)
    token = create_jobserver_token()
    directory = f'{TMPDIR}/{token}'
    os.mkdir(directory)
    metadata_filename = f'{directory}/metadata.json'
    metadata['sampleGroupName'] = metadata['name']
    del metadata['name']
    with open(metadata_filename, 'w') as file:
        json.dump(new_metadata, file)
    with open(f'{directory}/wfdata.json', 'w') as file:
        json.dump({'owner': user_id}, file)
    new_filenames = [f'{directory}/{os.path.basename(input_filename)}' for input_filename in input_filenames]
    [os.rename(input_filename, new_filename) for input_filename, new_filename in zip(input_filenames, new_filenames)]
    prefix = new_metadata['name']
    new_metadata['name'] = f'PLACEHOLDER <{prefix}>'
    output_ids = create_placeholder_samples(new_metadata, len(input_filenames))
    del new_metadata['name']
    workflow = {
        'cwlVersion': 'v1.0',
        'class': 'Workflow',
        'inputs':
            [
                {
                    'id': 'inputFiles',
                    'type': 'File[]'
                },
                {
                    'id': 'metadataFile',
                    'type': 'File'
                },
                {
                    'id': 'dataDirectory',
                    'type': 'Directory'
                },
                {
                    'id': 'prefix',
                    'type': 'string'
                },
                {
                    'id': 'firstId',
                    'type': 'int'
                },
                {
                    'id': 'authToken',
                    'type': 'string'
                },
                {
                    'id': 'wfToken',
                    'type': 'string'
                },
                {
                    'id': 'omicsUrl',
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
                            'id': 'inputFiles',
                            'source': 'inputFiles'
                        },
                        {
                            'id': 'prefix',
                            'source': 'prefix'
                        }
                    ],
                    'out': [{'id': 'outputFiles'}]
                },
                {
                    'id': 'process',
                    'run': new_metadata["preproc"],
                    'in': [
                        {
                            'id': 'inputFiles',
                            'source': 'parse/outputFiles'
                        }
                    ],
                    'out': [{'id': 'outputFiles'}]
                },
                {
                    'id': 'update',
                    'run': f'{MODULEDIR}/omics-service/uploadsamples.cwl',
                    'in':
                        [
                            {'id': 'inputFiles',
                             'source': 'process/outputFiles'},
                            {'id': 'metadataFile',
                             'source': 'metadataFile'},
                            {'id': 'idStart',
                             'source': 'firstId'},
                            {'id': 'wfToken',
                             'source': 'wfToken'},
                            {'id': 'omicsUrl',
                             'source': 'omicsUrl'},
                            {'id': 'authToken',
                             'source': 'authToken'}
                        ],
                    'out': [{'id': 'responses'}]
                }
            ]
    }
    job = {
        'inputFiles': [{'path': filename, 'class': 'File'} for filename in new_filenames],
        'metadataFile': {'path': metadata_filename,
                         'class': 'File'},
        'dataDirectory': {'path': f'{DATADIR}/samples',
                          'class': 'Directory'},
        'prefix': prefix,
        'firstId': min(output_ids),
        'authToken': get_jwt_by_id(user_id),
        'wfToken': token,
        'omicsUrl': os.environ['OMICSSERVER']
    }
    # perhaps move execution here?
    return {'workflow': workflow, 'job': job, 'outputIds': output_ids}


def get_preprocessing_modules() -> List[Dict[str, Any]]:
    """
    Get modules used for the preprocessing step of the sample upload process
    :return:
    """
    return get_modules(f'{MODULEDIR}/sample-processing')


def get_parsing_modules() -> List[Dict[str, Any]]:
    """
    Get the modules which may be used for the parsing step of the sample upload process
    :return:
    """
    return get_modules(f'{MODULEDIR}/sample-parsing')
