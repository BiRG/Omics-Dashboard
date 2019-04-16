import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from flask_login import current_user

from dashboards.navbar import get_navbar
from data_tools.access_wrappers.collections import get_collections
from .pca_data import get_plot_data


def get_plot_options_form():
    return dbc.Form(
        [
            html.H5('Scores Plots'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('x-axis', html_for='abscissa-select'),
                                    dcc.Dropdown(id='abscissa-select', options=[], multi=False)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('y-axis', html_for='ordinate-select'),
                                    dcc.Dropdown(id='ordinate-select', options=[], multi=False)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Color by label(s)', html_for='color-by-select'),
                                    dcc.Dropdown(id='color-by-select', options=[], multi=True)
                                ]
                            )
                        ]
                    ),
                ], className='form-row'
            ),
            dbc.Row(
                [
                    dbc.FormGroup(
                        [
                            dbc.Button([html.I(className='fas fa-plus'), ' Add'], id='score-plot-add-button',
                                       className='btn btn-success')
                        ]
                    )
                ], className='form-row'
            ),
            dbc.Row(
                [
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem(
                                f'{score_plot["ordinate"]} vs {score_plot["abscissa"]} by {score_plot["color_by"]}')
                            for score_plot in get_plot_data()["score_plots"]
                        ], id='score-plot-list'
                    )
                ], className='form-row', id='score-plot-list-wrapper'
            ),
            dbc.Row(
                [
                    dbc.FormGroup(
                        [
                            dbc.Button([html.I(className='fas fa-eraser'), ' Clear'], id='score-plot-clear-button',
                                       className='btn btn-danger')
                        ]
                    )
                ], className='form-row'
            ),
            html.Br(),
            html.H5('Loadings Plots'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Loadings', html_for='loading-select'),
                                    dcc.Dropdown(id='loading-select', options=[], multi=True)
                                ]
                            )
                        ]
                    ),
                ], className='form-row'
            ),
            dbc.Row(
                [
                    dbc.FormGroup(
                        [
                            dbc.Button([html.I(className='fas fa-plus'), ' Add'], id='loading-plot-add-button',
                                       className='btn btn-success')
                        ]
                    )
                ], className='form-row'
            ),
            dbc.Row(
                [
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem(','.join([f'PC{component}' for component in loading_plot['indices']]))
                            for loading_plot in get_plot_data()['loading_plots']
                        ], id='loading-plot-list'
                    )
                ], className='form-row', id='loading-plot-list-wrapper'
            ),
            dbc.Row(
                [
                    dbc.FormGroup(
                        [
                            dbc.Button([html.I(className='fas fa-eraser'), ' Clear'], id='loading-plot-clear-button',
                                       className='btn btn-danger')
                        ]
                    )
                ], className='form-row'
            ),
            html.Br(),
            html.H5('Variance Plots'),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('PCs', html_for='variance-select'),
                                    dcc.Dropdown(id='variance-select', options=[], multi=True)
                                ]
                            )
                        ]
                    )
                ], className='form-row'
            ),
            dbc.Row(
                [
                    html.Div(
                        [
                            dbc.Checkbox(id='variance-autoscale'),
                            dbc.Label('Scale y axis?', className='form-check-label', html_for='variance-autoscale')
                        ], className='form-check form-check-inline'
                    )
                ], className='form-row'
            ),
            dbc.Row(
                [
                    dbc.FormGroup(
                        [
                            dbc.Button([html.I(className='fas fa-plus'), ' Add'], id='variance-plot-add-button',
                                       className='btn btn-success')
                        ]
                    )
                ], className='form-row'
            ),
            dbc.Row(
                [
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem(','.join([f'PC{component}' for component in variance_plot['indices']])
                                              + ' (autoscaled)' if variance_plot['scale_y'] else '')
                            for variance_plot in get_plot_data()['variance_plots']
                        ], id='variance-plot-list'
                    )
                ], className='form-row', id='variance-plot-list-wrapper'
            ),
            dbc.Row(
                [
                    dbc.FormGroup(
                        [
                            dbc.Button([html.I(className='fas fa-eraser'), ' Clear'], id='variance-plot-clear-button',
                                       className='btn btn-danger')
                        ]
                    )
                ], className='form-row'
            ),
            dbc.FormGroup(
                [
                    dbc.Button('Plot PCA Results', id='plot-button', color='primary',
                               className='btn btn-block form-control',
                               disabled=True)
                ]
            )
        ]
    )


def get_pca_options_form():
    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user)
        ]
    except Exception as e:
        collection_options = []

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
                                    dbc.Label(['Loaded collections'], html_for='loaded-display',
                                              id='collections-label'),
                                    dcc.Loading(
                                        [
                                            dbc.InputGroup(
                                                [
                                                    dbc.Button('Get', id='get-collection',
                                                               className='col-sm-2 btn-success'),
                                                    html.H4([dbc.Badge('None', className='badge-pill')],
                                                            id='loaded-collections', className='col-sm-10')
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
                                    dbc.Label('Scale by label(s)', html_for='scale-by'),
                                    dcc.Dropdown(id='scale-by', options=[], multi=True),
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Scale by conditions', html_for='scale-by-value'),
                                    dcc.Dropdown(id='scale-by-value', options=[], multi=True),
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
                                    dbc.Label('Filter by label(s)', html_for='filter-by'),
                                    dcc.Dropdown(id='filter-by', options=[], multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Filter by conditions', html_for='filter-by-value'),
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
                                    dbc.Label('Ignore by label(s)', html_for='ignore-by'),
                                    dcc.Dropdown(id='ignore-by', options=[], multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Ignore by conditions', html_for='ignore-by-value'),
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
                                    dbc.Label('Merge by label(s)', html_for='pair-by'),
                                    dcc.Dropdown(id='merge-by', options=[], multi=True)
                                ]
                            )
                        ]
                    ),
                    dbc.Col(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Label('Merge method', html_for='merge-by-method'),
                                    dcc.Dropdown(id='merge-by-method',
                                                 options=[
                                                     {'label': 'Mean', 'value': 'mean'},
                                                     {'label': 'Median', 'value': 'median'}
                                                 ], value='mean', multi=False)
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.FormGroup(
                [
                    dcc.Loading(
                        [
                            dbc.Button('Run PCA', id='pca-button', color='primary',
                                       className='btn btn-block form-control'),
                            html.Small('', id='message', className='form-text text-muted')
                        ]
                    )
                ]
            )
        ]
    )


def get_layout():
    return html.Div(
        [
            get_navbar(),
            dbc.Container([
                html.H1('Principal Component Analysis'),
                dbc.Card(
                    [
                        dbc.CardHeader('PCA Options', className='text-white bg-primary'),
                        dbc.CardBody(
                            [
                                get_pca_options_form()
                            ]
                        )
                    ]
                ),
                html.Br(),
                dbc.Card(
                    [
                        dbc.CardHeader('Plot Options', className='text-white bg-primary'),
                        dbc.CardBody(
                            [
                                get_plot_options_form()
                            ]
                        )
                    ]
                ),
                dbc.Card(
                    [
                        dbc.CardHeader('Scores', className='text-white bg-primary'),
                        dcc.Loading(
                            [
                                dbc.CardBody([], id='score-card-body')
                            ]
                        )
                    ],
                    id='scores-card', className='row mt-3'
                ),
                dbc.Card(
                    [
                        dbc.CardHeader('Loadings', className='text-white bg-primary'),
                        dcc.Loading(
                            [
                                dbc.CardBody([], id='loading-card-body')
                            ]
                        )
                    ], id='loadings-card', className='row mt-3'),
                dbc.Card(
                    [
                        dbc.CardHeader('Variance Explained', className='text-white bg-primary'),
                        dcc.Loading(
                            [
                                dbc.CardBody([], id='variance-card-body')
                            ]
                        )
                    ], id='variance-card', className='row mt-3'
                )
            ])
        ]
    )
