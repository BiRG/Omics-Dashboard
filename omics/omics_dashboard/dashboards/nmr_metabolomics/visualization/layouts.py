import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from flask_login import current_user

from dashboards.navbar import get_navbar
from dashboards.nmr_metabolomics.visualization.visualization_data import VisualizationData
from data_tools.access_wrappers.collections import get_collections


def get_plot_options_form():
    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user, {'kind': 'data'})
        ]
    except:
        collection_options = []
    try:
        viz_data = VisualizationData(load_data=True)
        label_options = [{'label': label, 'value': label} for label in viz_data.labels]
        loaded_badges = viz_data.get_collection_badges()
        collection_load_info = viz_data.get_collection_load_info()
    except:
        loaded_badges = [html.Span([dbc.Badge('None', className='badge-pill')])]
        collection_load_info = 'Loaded collections.'
        label_options = []

    return dbc.Form(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Collection ID', html_for='collection-id'),
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
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Group By', html_for='group-by'),
                                    dcc.Dropdown(options=label_options, id='group-by', multi=True)
                                ]
                            )
                        ], className='col-3'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Display Groups', html_for='group-by-value'),
                                    dcc.Dropdown(options=[], id='group-by-value', multi=True)
                                ]
                            )
                        ], className='col-4'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Label By', html_for='label-by'),
                                    dcc.Dropdown(options=label_options, id='label-by', multi=True)
                                ]
                            )
                        ], className='col-3'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Update Plot', html_for='plot-button-group'),
                                    dbc.InputGroup(
                                        [
                                            dbc.Button('Plot', color='primary', id='plot-button')
                                        ], id='plot-button-group'
                                    )
                                ]
                            )
                        ], className='col-2'
                    )
                ]
            ),
        ]
    )


def get_layout():
    return html.Div(
        [
            get_navbar(),
            html.Br(),
            dbc.Container(
                [
                    html.H2('Visualize Collections'),
                    dbc.Card(
                        dbc.CardBody(get_plot_options_form())
                    ),
                    dbc.Card(
                        dbc.CardBody(dcc.Loading(html.Div(dcc.Graph(id='main-plot'), id='plot-wrapper')))
                    )
                ]
            )
        ]
    )
