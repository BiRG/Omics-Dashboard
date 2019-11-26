import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from flask_login import current_user

from dashboards.navbar import get_navbar
from dashboards.nmr_metabolomics.visualization.model import VisualizationModel
from data_tools.wrappers.collections import get_collections


def get_plot_options_form():
    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user, {'kind': 'data'})
        ]
    except:
        collection_options = []
    try:
        viz_data = VisualizationModel(load_data=True)
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
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Display Groups', html_for='group-by-value'),
                                    dcc.Dropdown(options=[], id='group-by-value', multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Label By', html_for='label-by'),
                                    dcc.Dropdown(options=label_options, id='label-by', multi=True)
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
                                    dbc.Label('Show Bins From', html_for='bin-collection'),
                                    dcc.Dropdown(options=collection_options, id='bin-collection', multi=False)
                                ]
                            )
                        ], className='col-5'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Legend Style', html_for='legend-style-select'),
                                    dcc.Dropdown(options=[
                                        {'label': 'Full', 'value': 'full'},
                                        {'label': 'Groups', 'value': 'groups'},
                                        {'label': 'None', 'value': 'none'}
                                    ], value='full', id='legend-style-select', clearable=False)
                                ]
                            )
                        ], className='col-3'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Background Color', html_for='background-color-select'),
                                    dcc.Dropdown(options=[
                                        {'label': 'Transparent', 'value': 'rgba(0,0,0,0)'},
                                        {'label': 'White', 'value': 'rgba(255,255,255,1)'},
                                    ], value='rgba(0,0,0,0)', id='background-color-select', clearable=False)
                                ]
                            )
                        ], className='col-3'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Plot', html_for='plot-button-group'),
                                    dbc.InputGroup(
                                        [
                                            dbc.Button('Plot', color='primary', id='plot-button')
                                        ], id='plot-button-group'
                                    )
                                ]
                            )
                        ], className='col-1'
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Width', html_for='width-input'),
                                    dbc.Input(type='number', min=0, step=0.25, value=6.5, id='width-input')
                                ]
                            )
                        ], className='col-2'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Height', html_for='height-input'),
                                    dbc.Input(type='number', min=0, step=0.25, value=4, id='height-input')
                                ]
                            )
                        ], className='col-2'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Units', html_for='units-select'),
                                    dcc.Dropdown(options=[
                                        {'label': 'in', 'value': 'in'},
                                        {'label': 'cm', 'value': 'cm'},
                                        {'label': 'px', 'value': 'px'}
                                    ], value='in', clearable=False, id='units-select')
                                ]
                            )
                        ], className='col-1'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('DPI', html_for='dpi-select'),
                                    dbc.Input(type='number', min=50, step=25, value=100, id='dpi-input')
                                ]
                            )
                        ], className='col-2'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('File Format', html_for='file-format-select'),
                                    dcc.Dropdown(options=[
                                        {'label': 'SVG', 'value': 'svg'},
                                        {'label': 'PNG', 'value': 'png'},
                                        {'label': 'JPEG', 'value': 'jpg'},
                                        {'label': 'PDF', 'value': 'pdf'},
                                        {'label': 'TIFF', 'value': 'tif'},
                                        {'label': 'EPS', 'value': 'eps'}
                                    ], value='png', clearable=False, id='file-format-select')
                                ]
                            )
                        ], className='col-2'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Prepare', html_for='download-button-group'),
                                    dbc.FormGroup(
                                        [
                                            dbc.Button([html.I(className='fas fa-cogs')],
                                                       id='download-button',
                                                       className='btn btn-info')
                                        ], id='download-button-group'
                                    )
                                ]
                            )
                        ], className='col-1'
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Download', html_for='download-link-group'),
                                        dbc.FormGroup(
                                            [
                                                dcc.Loading(
                                                    html.A([html.I(className='fas fa-download')],
                                                           id='download-link', className='btn btn-secondary disabled')
                                                )
                                            ], id='download-link-group'
                                        )
                                ]
                            )
                        ], className='col-1'
                    )
                ]
            ),
            dbc.Row(dcc.Loading(html.Small('', id='download-message', className='form-text'))),
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
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            get_plot_options_form()
                                        )
                                    )
                                ], label='Options', tab_id='options-tab'),
                            dbc.Tab(
                                [
                                    dbc.Card(
                                        dbc.CardBody(dcc.Loading(html.Div(dcc.Graph(id='main-plot'),
                                                                          id='plot-wrapper')))
                                    ),
                                    dbc.Card(
                                        dbc.CardBody(id='summary-table-wrapper')
                                    )
                                ], label='Plot', tab_id='plot-tab')
                        ], id='main-tabs', active_tab='options-tab'
                    )
                ]
            ),
            html.Div('in', id='units-history', style={'display': 'none'}),
            html.Div(100, id='dpi-history', style={'display': 'none'})
        ]
    )
