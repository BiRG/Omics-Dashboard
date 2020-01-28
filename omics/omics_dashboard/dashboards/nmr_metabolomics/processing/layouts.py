import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_daq as daq
from flask_login import current_user

from dashboards.nmr_metabolomics.processing.model import CollectionProcessingModel
from data_tools.wrappers.analyses import get_analyses
from data_tools.wrappers.collections import get_collections


def get_post_form():
    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user, {'kind': 'data'})
        ]
        analysis_options = [
            {'label': f'{analysis.id}: {analysis.name}', 'value': analysis.id}
            for analysis in get_analyses(current_user)
        ]
    except:
        collection_options = []
        analysis_options = []
    try:
        editor_data = CollectionProcessingModel(load_data=True)
        loaded_badges = editor_data.get_collection_badges()
        collection_load_info = editor_data.get_collection_load_info()
    except:
        loaded_badges = [html.Span([dbc.Badge('None', className='badge-pill')])]
        collection_load_info = 'Loaded collections.'

    return dbc.Card(
        dbc.CardBody(
            dbc.Form(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Collection IDs', html_for='collection-id'),
                                            dcc.Dropdown(options=collection_options, id='collection-id', multi=True)
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
                    html.H5('Post Collection'),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Name', html_for='name-input-wrapper-wrapper'),
                                            html.Div(
                                                html.Div(
                                                    dbc.Input(id='name-input'), id='name-input-wrapper'
                                                ), id='name-input-wrapper-wrapper'
                                            )
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Analyses', html_for='analysis-select'),
                                            dcc.Dropdown(id='analysis-select', options=analysis_options, multi=True)
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
        )
    )


def options_form():
    try:
        model = CollectionProcessingModel(load_data=True)
        label_options = [{'label': label, 'value': label} for label in model.labels]
    except:
        label_options = []
    normalize_tab_content = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Form(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Method', html_for='normalization-method'),
                                                dcc.Dropdown(options=[
                                                    {'label': 'Sum', 'value': 'sum'},  # option "sum"
                                                    {'label': 'Label (weight)', 'value': 'label'},  # option "label"
                                                    {'label': 'Active region', 'value': 'region'},  # No options
                                                    {'label': 'Min/max', 'value': 'min_max'},  # No options
                                                    {'label': 'Histogram', 'value': 'histogram'},
                                                    # options "n_bins", "n_std", "noise_ind"
                                                    {'label': 'Probability quotient', 'value': 'probability_quotient'}
                                                    # option "reference_type"
                                                ], id='normalization-method', value='sum')
                                            ]
                                        )
                                    )
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Sum', html_for='norm-sum'),
                                                dbc.Input(value=1000, step=1, min=0, type='number', id='norm-sum')
                                            ]
                                        )
                                    )
                                ], id='sum-normalization-form'
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Label', html_for='norm-label'),
                                                dcc.Dropdown(options=label_options, id='norm-label')
                                            ]
                                        )
                                    )
                                ], id='label-normalization-form', style={'display': 'none'}
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Intensity', html_for='peak-intensity'),
                                                dbc.Input(value=100, step=1, min=0, type='number', id='peak-intensity')
                                            ]
                                        )
                                    )
                                ], id='region-normalization-form', style={'display': 'none'}
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Reference labels', html_for='hist-ref-label'),
                                                dcc.Dropdown(options=[], id='hist-ref-label', multi=True)
                                            ]
                                        )
                                    ),
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Reference label values', html_for='hist-ref-query'),
                                                dcc.Dropdown(options=[], id='hist-ref-query', multi=True)
                                            ]
                                        )
                                    ),
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Reference Type', html_for='hist-ref-type'),
                                                dcc.Dropdown(options=[
                                                    {'label': 'Median', 'value': 'median'},
                                                    {'label': 'Mean', 'value': 'mean'}
                                                ], id='hist-ref-type', value='mean')
                                            ]
                                        )
                                    )
                                ], id='hist-normalization-form', style={'display': 'none'}
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Reference labels', html_for='pqn-ref-label'),
                                                dcc.Dropdown(options=[], id='pqn-ref-label', multi=True)
                                            ]
                                        )
                                    ),
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Reference label values', html_for='pqn-ref-query'),
                                                dcc.Dropdown(options=[], id='pqn-ref-query', multi=True)
                                            ]
                                        )
                                    ),
                                    dbc.Col(
                                        dbc.FormGroup(
                                            [
                                                dbc.Label('Reference Type', html_for='pqn-ref-type'),
                                                dcc.Dropdown(options=[
                                                    {'label': 'Median', 'value': 'median'},
                                                    {'label': 'Mean', 'value': 'mean'}
                                                ], id='pqn-ref-type', value='mean')
                                            ]
                                        )
                                    )
                                ], id='pqn-normalization-form', style={'display': 'none'}
                            ),
                            dbc.Row(
                                dbc.Col(
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Apply', html_for='normalization-apply-button-group'),
                                            dbc.FormGroup(
                                                dbc.Button('Apply', id='normalization-apply-button'),
                                                id='normalization-apply-button-group'
                                            )
                                        ]
                                    )
                                )
                            )
                        ]
                    )
                ]
            )
        ]
    )
    baseline_options = dbc.Form(
        [
            dbc.FormGroup(
                [
                    dbc.Label('Method', html_for='baseline-method'),
                    dcc.Dropdown(options=[{'label': 'Rolling ball', 'value': 'rolling_ball'}],
                                 id='baseline-method',
                                 value='rolling_ball')
                ]
            )
        ]
    )
    rolling_ball_options = dbc.Form(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Min/max window', html_for='rolling-ball-min-max'),
                                    dbc.Input(id='rolling-ball-min-max', type='number', value=21)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Smoothing window', html_for='rolling-ball-smoothing'),
                                    dbc.Input(id='rolling-ball-smoothing', type='number', value=13)
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Row(
                dbc.Col(
                    dbc.FormGroup(
                        [
                            dbc.Label('Apply', html_for='baseline-apply-button-group'),
                            dbc.FormGroup(
                                dbc.Button('Apply', id='baseline-apply-button'),
                                id='baseline-apply-button-group'
                            )
                        ]
                    )
                )
            )
        ]
    )
    baseline_tab_content = dbc.Card(
        [
            dbc.CardBody(
                [
                    baseline_options,
                    rolling_ball_options
                ]
            )
        ]
    )

    region_options = dbc.Form(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.FormGroup(
                            [
                                dbc.Label('Method', html_for='region-method'),
                                dcc.Dropdown(options=[
                                    {'label': 'Zero', 'value': 'zero'},
                                    {'label': 'Crop', 'value': 'crop'},
                                    {'label': 'Delete', 'value': 'delete'},
                                    {'label': 'Reference (Don not use!)', 'value': 'reference'}
                                ], id='region-method', value='zero')
                            ]
                        )
                    ),
                    dbc.Col(
                        dbc.FormGroup(
                            [
                                dbc.Label('Apply', html_for='region-apply-button-group'),
                                dbc.FormGroup(
                                    dbc.Button('Apply', id='region-apply-button'),
                                    id='region-apply-button-group'
                                )
                            ]
                        )
                    )
                ]
            )
        ]
    )
    region_tab_content = dbc.Card(
        [
            dbc.CardBody(
                [
                    region_options
                ]
            )
        ]
    )
    return dbc.Tabs(
        [
            dbc.Tab(get_post_form(), label='Get/Post'),
            dbc.Tab(normalize_tab_content, label='Normalize'),
            dbc.Tab(baseline_tab_content, label='Correct Baseline'),
            dbc.Tab(region_tab_content, label='Zero/Crop/Reference'),
        ]
    )


def preview_graph():
    return html.Div(
        [
            html.Div(dcc.Graph(id='preview-graph', config={'editable': True}), id='preview-graph-wrapper'),
            dbc.Form(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Label('Spectrum #', html_for='spectrum-index'),
                                        dbc.Input(type='number', value=0, step=1, min=0, id='spectrum-index')
                                    ]
                                )
                            ),
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Label('Max', html_for='region-max'),
                                        dbc.Input(type='number', value=0.1, id='region-max')
                                    ]
                                )
                            ),
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Label('Min', html_for='region-min'),
                                        dbc.Input(type='number', value=0, id='region-min')
                                    ]
                                )
                            ),
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Label('Range box', html_for='range-checklist'),
                                        dbc.Checklist(
                                            options=[
                                                {'label': 'Show', 'value': 'show_range_box'}
                                            ],
                                            value=[],
                                            id='range-checklist',
                                            switch=True
                                        )
                                    ]
                                )
                            ),
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Label('Finalize', html_for='finalize-button-group'),
                                        dbc.FormGroup(
                                            dbc.Button('Finalize', color='info', id='finalize-button'),
                                            id='finalize-button-group'
                                        )
                                    ]
                                )
                            )
                        ]
                    )
                ]
            )
        ]
    )


def get_layout():
    return html.Div(
        [
            html.Br(),
            dbc.Container(
                [
                    html.H2('Fix Spectra'),
                    preview_graph(),
                    options_form(),
                    html.Div([html.P(id='processing-log')], id='processing-log-wrapper')
                ]
            )
        ]
    )
