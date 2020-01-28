import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from flask_login import current_user

from dashboards.nmr_metabolomics.collection_editor.model import CollectionEditorModel
from data_tools.wrappers.analyses import get_analyses
from data_tools.wrappers.collections import get_collections


def get_options_form():
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
        editor_data = CollectionEditorModel(load_data=True)
        label_options = [{'label': label, 'value': label} for label in editor_data.labels]
        loaded_badges = editor_data.get_collection_badges()
        collection_load_info = editor_data.get_collection_load_info()
        if len(loaded_badges) == 2:
            collection_ids = editor_data.unique_vals('original_collection_id')
            collection_id_options = [{'label': f'collection_id={i}', 'value': i} for i in collection_ids]
        else:
            collection_id_options = []
    except:
        loaded_badges = [html.Span([dbc.Badge('None', className='badge-pill')])]
        collection_load_info = 'Loaded collections.'
        label_options = []
        collection_id_options = []

    return dbc.Form(
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
            html.H5('Filter/Join Collections'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Filter by label(s)',
                                               html.Abbr('\uFE56',
                                                         title='Only consider records satisfying conditions on these'
                                                               ' fields.')],
                                              html_for='filter-by'),
                                    dcc.Dropdown(id='filter-by', options=label_options, multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['Filter by conditions',
                                               html.Abbr('\uFE56',
                                                         title='The conditions which must be satisfied for the records'
                                                               'to be considered.')],
                                              html_for='filter-by-value'),
                                    dcc.Dropdown(id='filter-by-value', options=[], multi=True)
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
                                    dbc.Label(['Join on label(s)',
                                               html.Abbr('\uFE56',
                                                         title='A combination of values forming a unique key on which '
                                                               'the two collections are joined.')],
                                              html_for='join-on'),
                                    dcc.Dropdown(id='join-on', options=label_options, multi=True,
                                                 disabled=(len(loaded_badges) != 2))
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label(['"Left" Collection ID',
                                               html.Abbr('\uFE56',
                                                         title='The collection id for the collection which will have '
                                                               'positive values for "x" and appear on the left side of '
                                                               'the plots')],
                                              html_for='positive-collection'),
                                    dcc.Dropdown(id='positive-collection', options=collection_id_options, multi=False,
                                                 disabled=(len(loaded_badges) != 2))
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


def get_layout():
    return html.Div(
        [
            html.Br(),
            dbc.Container(
                [
                    html.H2('Merge/Join/Filter Collections'),
                    get_options_form()
                ]
            )
        ]
    )
