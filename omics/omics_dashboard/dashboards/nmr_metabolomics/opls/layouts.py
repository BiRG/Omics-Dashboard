import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from flask_login import current_user

from dashboards.navbar import get_navbar
from data_tools.access_wrappers.analyses import get_analyses
from data_tools.access_wrappers.collections import get_collections
from .opls_data import OPLSData


def get_load_results_form():
    try:
        analysis_options = [
            {'label': f'{analysis.id}: {analysis.name}', 'value': analysis.id}
            for analysis in get_analyses(current_user)
        ]
    except:
        analysis_options = []

    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user, {'kind': 'results'})
            if collection.get_attr('analysis_type', safe=True) == 'opls'
        ]
    except:
        collection_options = []
    try:
        opls_data = OPLSData(load_data=True)
        loaded_badges = opls_data.get_results_collection_badges()
    except:
        loaded_badges = [html.Span([dbc.Badge('None', className='badge-pill')])]

    return dbc.Form(
        [
            html.H5('Load Results'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Results Collection ID', html_for='results-collection-id'),
                                    dcc.Dropdown(options=collection_options, id='results-collection-id', multi=False)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Results collection'),
                                    dcc.Loading(
                                        [
                                            dbc.InputGroup(
                                                [
                                                    dbc.Button('Get', id='get-results-collection',
                                                               className='col-sm-2 btn-success'),
                                                    html.H4(html.Div(loaded_badges, id='loaded-results-collection'),
                                                            id='loaded-results-collection-wrapper',
                                                            className='col-sm-10')
                                                ], id='loaded-results-display'
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            html.H5('Save Results'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Results', html_for='results-select'),
                                    dcc.Dropdown(id='results-select',
                                                 multi=True,
                                                 options=[
                                                     {'label': 'Feature P-Values', 'value': 'feature_p_values'},
                                                     {'label': 'Regression coefficients', 'value': 'coef'},
                                                     {'label': 'Scores', 'value': 'scores'},  # t and t_ortho
                                                     {'label': 'Orthogonal Scores', 'value': 'orthogonal_scores'},
                                                     {'label': 'R-squared/Q-squared', 'value': 'r_squared'},
                                                     {'label': 'Loadings', 'value': 'loadings'},
                                                     {'label': 'Orthogonal Loadings', 'value': 'orthogonal_loadings'},
                                                     {'label': 'Weights', 'value': 'weights'},
                                                     {'label': 'Orthogonal Weights', 'value': 'orthogonal_weights'},
                                                 ])
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('File Format', html_for='file-format-select'),
                                    dcc.Dropdown(id='file-format-select',
                                                 multi=True,
                                                 options=[
                                                     {'label': 'CSV', 'value': 'csv'},
                                                     {'label': 'HDF5', 'value': 'hdf5'}
                                                 ])
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Assemble results', html_for='download-button-group'),
                                    dbc.FormGroup(
                                        [
                                            dbc.Button([html.I(className='fas fa-cogs'), ' Prepare'],
                                                       id='download-button',
                                                       className='btn btn-info')
                                        ], id='download-button-group'
                                    )
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Download', html_for='download-link-group'),
                                    dbc.FormGroup(
                                        [
                                            html.A([html.I(className='fas fa-download'), ' Download'],
                                                   id='download-link', className='btn btn-secondary disabled')
                                        ], id='download-link-group'
                                    )
                                ]
                            )
                        ]
                    )
                ], className='form-row'
            ),
            dcc.Loading(html.Small('', id='download-message', className='form-text')),
            # will inject link when results posted
            html.H5('Save Plots'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['File Format',
                                               html.Abbr('\uFE56',
                                                         title='For publication-quality images, save as SVG and use an '
                                                               'image editor to export a TIFF file at the requested DPI')],
                                              html_for='plot-file-format-select'),
                                    dcc.Dropdown(id='plot-file-format-select',
                                                 multi=True,
                                                 options=[
                                                     {'label': 'PNG', 'value': 'png'},
                                                     {'label': 'JPEG', 'value': 'jpg'},
                                                     {'label': 'SVG', 'value': 'svg'},
                                                 ])
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Assemble plots', html_for='plot-download-button-group'),
                                    dbc.FormGroup(
                                        [
                                            dbc.Button([html.I(className='fas fa-cogs'), ' Prepare'],
                                                       id='plot-download-button',
                                                       className='btn btn-info')
                                        ], id='plot-download-button-group'
                                    )
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Download', html_for='plot-download-link-group'),
                                    dbc.FormGroup(
                                        [
                                            html.A([html.I(className='fas fa-download'), ' Download'],
                                                   id='plot-download-link', className='btn btn-secondary disabled')
                                        ], id='plot-download-link-group'
                                    )
                                ]
                            )
                        ]
                    )
                ], className='form-row'
            ),
            dcc.Loading(html.Small('', id='plot-download-message', className='form-text')),
            # will inject link when results posted
            html.H5('Post transformed collection'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Name', html_for='name-input'),
                                    dbc.Input(id='name-input')
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Analysis', html_for='analysis-select'),
                                    dcc.Dropdown(id='analysis-select', options=analysis_options)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Post', html_for='post-button-group'),
                                    dbc.FormGroup(
                                        [
                                            dbc.Button([html.I(className='fas fa-upload'), ' Post'],
                                                       id='post-button',
                                                       className='btn btn-success')
                                        ], id='post-button-group'
                                    )
                                ]
                            )
                        ]
                    )
                ], className='form-row'
            ),
            dcc.Loading(html.Small('', id='post-message', className='form-text'))
            # will inject link when results posted
        ]
    )


def get_opls_options_form():
    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user, {'kind': 'data'})
        ]
    except:
        collection_options = []
    try:
        opls_data = OPLSData(load_data=True)
        label_options = [{'label': label, 'value': label} for label in opls_data.labels]
        label_options_with_type = [{'label': label, 'value': label} for label in opls_data.get_label_data(True)]
        loaded_badges = opls_data.get_collection_badges()
        collection_load_info = opls_data.get_collection_load_info()
    except:
        loaded_badges = [html.Span([dbc.Badge('None', className='badge-pill')])]
        collection_load_info = 'Loaded collections.'
        label_options = []
        label_options_with_type = []

    return dbc.Form(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Collection ID', html_for='collection-id'),
                                    dcc.Dropdown(options=collection_options, id='collection-id', multi=False)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(collection_load_info, html_for='loaded-display',
                                              id='collections-label'),
                                    dcc.Loading(
                                        [
                                            dbc.InputGroup(
                                                [
                                                    dbc.Button('Get', id='get-collection',
                                                               className='col-sm-2 btn-success'),
                                                    html.H4(loaded_badges, id='loaded-collections',
                                                            className='col-sm-10')
                                                ], id='loaded-display'
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Target variable.', html.Abbr('\uFE56',
                                                                             title='The target ("y") variable.')],
                                              html_for='target-variable'),
                                    dcc.Dropdown(id='target-variable', options=label_options_with_type, multi=False)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Regression type.', html.Abbr('\uFE56',
                                                                             title='For categorical target variables,'
                                                                                   ' choose Discrimination. When The'
                                                                                   ' magnitudes of values are important'
                                                                                   ' choose Regression.')],
                                              html_for='regression-type'),
                                    dcc.Dropdown(id='regression-type',
                                                 options=[
                                                            {
                                                                'label': 'Regression',
                                                                'value': 'regression'
                                                            },
                                                            {
                                                                'label': 'Discrimination',
                                                                'value': 'discrimination'
                                                            }
                                                         ],
                                                 multi=False)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Multiclass discrimination behavior',
                                            html.Abbr('\uFE56',
                                                      title='How to handle multiclass targets. One regressor is'
                                                            ' created for each class or pair of classes and the '
                                                            'cross-validation is performed on each one separately. '
                                                            '"One v. One" will try to discriminate between each pair'
                                                            ' of classes. "One v. All" will discriminate each class '
                                                            'from all the other classes. You can select both.\n\n'
                                                            'If "Regression" is selected in the previous option, an '
                                                            'attempt will be made to coerce the values of the target '
                                                            'variable into floating-point numbers and treat the target '
                                                            'as a continuous variable and this option will be ignored.')
                                        ], html_for='multiclass-behavior'),
                                    dcc.Dropdown(id='multiclass-behavior',
                                                 options=[
                                                     {
                                                         'label': 'One v. one',
                                                         'value': 'one_v_one',
                                                     },
                                                     {
                                                         'label': 'One v. all',
                                                         'value': 'one_v_all'
                                                     }
                                                 ],
                                                 multi=True)
                                ]
                            )
                        ]
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Cross-validation folds',
                                            html.Abbr('\uFE56',
                                                      title='The number of test/train splits for the test to determine '
                                                            'the significance of regression quality metrics.')
                                        ], html_for='cross-val-k'),
                                    dbc.Input(id='cross-val-k', type='number', value=10, min=-1)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Minimum orthogonal components.',
                                            html.Abbr('\uFE56',
                                                      title='The minimum number of orthogonal components to remove.')
                                        ], html_for='min-n-components'),
                                    dbc.Input(id='min-n-components', type='number', value=1, min=1)
                                ]
                            )
                        ]
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Inner test \u03B1',
                                            html.Abbr('\uFE56',
                                                      title='A two-sided p-value threshold which is used to determine '
                                                            'which features need further scrutiny.')
                                        ], html_for='inner-test-alpha'),
                                    dbc.Input(id='inner-test-alpha', type='number', value=0.2, step=0.05)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Outer test \u03B1',
                                            html.Abbr('\uFE56',
                                                      title='A two-sided p-value threshold which is used to determine '
                                                            'which features are significant.')
                                        ], html_for='outer-test-alpha'),
                                    dbc.Input(id='outer-test-alpha', type='number', value=0.01, step=0.01)
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Metric test permutations',
                                            html.Abbr('\uFE56',
                                                      title='How many permutations (of the target) to determine '
                                                            'p-values for regression quality metrics.')
                                        ], html_for='permutations'),
                                    dbc.Input(id='permutations', type='number', value=1000)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Inner test permutations',
                                            html.Abbr('\uFE56',
                                                      title='How many permutations (of the data in one feature) to '
                                                            'perform for every feature to estimate its significance.')
                                        ], html_for='inner-permutations'),
                                    dbc.Input(id='inner-permutations', type='number', value=100)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(
                                        [
                                            'Outer test permutations',
                                            html.Abbr('\uFE56',
                                                      title='How many permutations (of the data in one feature) to '
                                                            'perform for every feature determined to be potentially '
                                                            'significant in the first round.')
                                        ], html_for='outer-permutations'),
                                    dbc.Input(id='outer-permutations', type='number', value=500)
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Scale by label(s)',
                                               html.Abbr('\uFE56',
                                                         title='The mean of the records satisfying conditions on these '
                                                               'fields will be subtracted from each record, then each'
                                                               ' record will be scaled by the standard deviation of the'
                                                               ' records satisfying the conditions.')],
                                              html_for='scale-by'),
                                    dcc.Dropdown(id='scale-by', options=label_options, multi=True),
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Scale by conditions',
                                               html.Abbr('\uFE56',
                                                         title='The conditions for the records to use for scaling. If '
                                                               'left blank, then no scaling is performed.')],
                                              html_for='scale-by-value'),
                                    dcc.Dropdown(id='scale-by-value', options=[{'label': 'All Records',
                                                                                'value': 'index'}], multi=True),
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Model by label(s)',
                                               html.Abbr('\uFE56',
                                                         title='Only consider records satisfying conditions on these'
                                                               ' fields.')],
                                              html_for='model-by'),
                                    dcc.Dropdown(id='model-by', options=label_options, multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Model by conditions',
                                               html.Abbr('\uFE56',
                                                         title='The conditions which must be satisfied for the records'
                                                               'to be considered.')],
                                              html_for='model-by-value'),
                                    dcc.Dropdown(id='model-by-value', options=[], multi=True)
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Ignore by label(s)',
                                               html.Abbr('\uFE56',
                                                         title='Exclude records satisfying conditions on these fields')],
                                              html_for='ignore-by'),
                                    dcc.Dropdown(id='ignore-by', options=label_options, multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Ignore by conditions',
                                               html.Abbr('\uFE56',
                                                         title='Conditions which apply to records to be excluded.')],
                                              html_for='ignore-by-value'),
                                    dcc.Dropdown(id='ignore-by-value', options=[], multi=True)
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Pair on label(s)',
                                               html.Abbr('\uFE56',
                                                         title='The paired analysis works on the difference between '
                                                               'records in one class and other records, where the '
                                                               'records are "paired" by some identity condition. The '
                                                               '"pair on" label is used to pair all the records with '
                                                               'equal values for that field.')],

                                              html_for='pair-on'),
                                    dcc.Dropdown(id='pair-on', options=label_options, multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Pair with label(s)',
                                               html.Abbr('\uFE56',
                                                         title='The "pair with" condition applies to the records to be '
                                                               'subtracted from the others')],
                                              html_for='pair-with'),
                                    dcc.Dropdown(id='pair-with', options=label_options, multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Pair with conditions',
                                               html.Abbr('\uFE56',
                                                         title='The condition which must apply for the records which '
                                                               'will be subtracted.')],
                                              html_for='pair-with-value'),
                                    dcc.Dropdown(id='pair-with-value', options=[], multi=True)
                                ]
                            )
                        ]
                    ),
                ]
            ),
            dbc.FormGroup(
                [
                    dcc.Loading(
                        [
                            dbc.Button('Run OPLS', id='opls-button', color='primary',
                                       className='btn btn-block form-control'),
                            html.Small('', id='message', className='form-text')
                        ]
                    )
                ]
            )
        ]
    )


def get_results_form():
    # check if results are loaded
    return [
        dbc.CardHeader(
            [
                dbc.Tabs(
                    [
                        dbc.Tab(label='Summary', tab_id='summary-tab'),
                        dbc.Tab(label='Quality Metrics', tab_id='quality-tab'),
                        dbc.Tab(label='Metric Permutation Tests', tab_id='kde-tab'),
                        dbc.Tab(label='Feature Permutation Tests', tab_id='feature-significance-tab')
                    ], id='results-tabs', active_tab='summary-tab', card=True
                ),
            ]
        ),
        dcc.Loading(dbc.CardBody(id='results-content'))
    ]


def get_layout():
    return html.Div(
        [
            get_navbar(),
            html.Br(),
            dbc.Container(
                [
                    html.H2('Orthogonal Projection to Latent Structures'),
                    dbc.Tabs(
                        [
                            dbc.Tab(dbc.Card(dbc.CardBody(get_opls_options_form())),
                                    id='opls-options-tab', label='OPLS Options'),
                            dbc.Tab(dbc.Card(dbc.CardBody(get_load_results_form())),
                                    id='save-results-tab', label='Load/Export Results'),
                            dbc.Tab(dbc.Card(get_results_form()),
                                    id='results-tab', label='Results')
                        ], id='tabs'
                    )
                ]
            )
        ]
    )

