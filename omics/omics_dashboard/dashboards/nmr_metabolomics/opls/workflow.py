import os

from config.config import MODULEDIR

workflow = {
    'class': 'Workflow',
    'cwlVersion': 'v1.0',
    'doc': 'A workflow to perform OPLS',
    'id': 'workflow4',
    'inputs': [
        {
            'id': 'omics_url',
            'type': 'string'
        },
        {
            'id': 'omics_auth_token',
            'type': 'string'
        },
        {
            'id': 'collection_id',
            'type': 'int'
        },
        {
            'id': 'one_v_all',
            'type': 'boolean'
        },
        {
            'id': 'one_v_one',
            'type': 'boolean'
        },
        {
            'id': 'ignore_by_query',
            'type': ['string', 'null']
        },
        {
            'id': 'model_by_query',
            'type': ['string', 'null']
        },
        {
            'id': 'pair_on_label',
            'type': ['string', 'null']
        },
        {
            'id': 'pair_with_query',
            'type': ['string', 'null']
        },
        {
            'id': 'scale_by_query',
            'type': ['string', 'null']
        },
        {
            'id': 'metric_test_permutations',
            'type': 'long'
        },
        {
            'id': 'min_n_components',
            'type': 'long'
        },
        {
            'id': 'outer_test_alpha',
            'type': 'float'
        },
        {
            'id': 'outer_test_permutations',
            'type': 'long'
        },
        {
            'id': 'target',
            'type': 'string'
        },
        {
            'id': 'k',
            'type': 'long'
        },
        {
            'id': 'inner_test_permutations',
            'type': 'long'
        },
        {
            'id': 'inner_test_alpha',
            'type': 'float'
        },
        {
            'id': 'force_regression',
            'type': ['boolean', 'null']
        },
        {
            'id': 'results_collection_id',
            'type': 'long'
        }
    ],
    'label': 'OPLS',
    'outputs': [],
    'steps': [
        {
            'id': 'get_collection',
            'in': [
                {
                    'id': 'collection_id',
                    'source': 'collection_id'
                },
                {
                    'id': 'omics_url',
                    'source': 'omics_url'
                },
                {
                    'id': 'omics_auth_token',
                    'source': 'omics_auth_token'
                }
            ],
            'label': 'Get Collection',
            'out': [
                {
                    'id': 'collection_file'
                }
            ],
            'run': os.path.join(MODULEDIR, 'omics-service', 'get_collection.cwl')
        },
        {
            'id': 'get_split_dataframe',
            'in': [
                {
                    'id': 'input_file',
                    'source': 'get_collection/collection_file'
                }
            ],
            'label': 'Get Split DataFrames',
            'out': [
                {
                    'id': 'output_file'
                }
            ],
            'run': os.path.join(MODULEDIR, 'data-manipulation', 'get_split_dataframe.cwl')
        },
        {
            'id': 'multivariate_preproc',
            'in': [
                {
                    'id': 'dataframe_file',
                    'source': 'get_split_dataframe/output_file'
                },
                {
                    'id': 'scale_by_query',
                    'source': 'scale_by_query'
                },
                {
                    'id': 'model_by_query',
                    'source': 'model_by_query'
                },
                {
                    'id': 'ignore_by_query',
                    'source': 'ignore_by_query'
                },
                {
                    'id': 'pair_on_label',
                    'source': 'pair_on_label'
                },
                {
                    'id': 'pair_with_query',
                    'source': 'pair_with_query'
                }
            ],
            'label': 'Multivariate Preprocessing',
            'out': [
                {
                    'id': 'output_file'
                }
            ],
            'run': os.path.join(MODULEDIR, 'nmr-metabolomics', 'processing', 'multivariate_preproc.cwl')
        },
        {
            'id': 'multiclass_split',
            'in': [
                {
                    'id': 'input_file',
                    'source': 'multivariate_preproc/output_file'
                },
                {
                    'id': 'target',
                    'source': 'target'
                },
                {
                    'id': 'one_v_one',
                    'source': 'one_v_one'
                },
                {
                    'id': 'one_v_all',
                    'source': 'one_v_all'
                }
            ],
            'out': [
                {
                    'id': 'output_file'
                }
            ],
            'run': os.path.join(MODULEDIR, 'data-manipulation', 'multiclass_split.cwl'),
        },
        {
            'id': 'opls',
            'in': [
                {
                    'id': 'dataframes',
                    'source': 'multiclass_split/output_file'
                },
                {
                    'id': 'k',
                    'source': 'k'
                },
                {
                    'id': 'min_n_components',
                    'source': 'min_n_components'
                },
                {
                    'id': 'inner_test_alpha',
                    'source': 'inner_test_alpha'
                },
                {
                    'id': 'outer_test_alpha',
                    'source': 'outer_test_alpha'
                },
                {
                    'id': 'metric_test_permutations',
                    'source': 'metric_test_permutations'
                },
                {
                    'id': 'inner_test_permutations',
                    'source': 'inner_test_permutations'
                },
                {
                    'id': 'outer_test_permutations',
                    'source': 'outer_test_permutations'
                },
                {
                    'id': 'force_regression',
                    'source': 'force_regression'
                }
            ],
            'label': 'Perform OPLS',
            'out': [
                {
                    'id': 'results_file'
                }
            ],
            'run': os.path.join(MODULEDIR, 'nmr-metabolomics', 'analysis', 'opls.cwl')
        },
        {
            'id': 'update_collection',
            'in': [
                {
                    'id': 'input_file',
                    'source': 'opls/results_file'
                },
                {
                    'id': 'collection_id',
                    'source': 'results_collection_id'
                },
                {
                    'id': 'omics_url',
                    'source': 'omics_url'
                },
                {
                    'id': 'omics_auth_token',
                    'source': 'omics_auth_token'
                }
            ],
            'label': 'Update Collections(s)',
            'out': [
                {
                    'id': 'error_responses'
                }
            ],
            'run': os.path.join(MODULEDIR, 'omics-service', 'update_collection.cwl')
        }
    ]
}
