import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from flask_login import current_user

from data_tools.wrappers.analyses import get_analyses
from data_tools.wrappers.collections import get_collections
from .model import PCAModel


def get_save_results_form():
    try:
        analysis_options = [
            {'label': f'{analysis.id}: {analysis.name}', 'value': analysis.id}
            for analysis in get_analyses(current_user)
        ]
    except:
        analysis_options = []

    return dbc.Card(
        dbc.CardBody(
            dbc.Form(
                [
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
                                                             {'label': 'Scores', 'value': 'scores'},
                                                             {'label': 'Loadings', 'value': 'loadings'},
                                                             {'label': 'Variance Explained',
                                                              'value': 'explained_variance'},
                                                             {'label': 'Davies-Bouldin Indices', 'value': 'db_indices'}
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
                                            dbc.Label('File Formats', html_for='plot-file-format-select'),
                                            dcc.Dropdown(options=[
                                                {'label': 'SVG', 'value': 'svg'},
                                                {'label': 'PNG', 'value': 'png'},
                                                {'label': 'JPEG', 'value': 'jpg'},
                                                {'label': 'PDF', 'value': 'pdf'},
                                                {'label': 'TIFF', 'value': 'tif'},
                                                {'label': 'EPS', 'value': 'eps'}
                                            ], value=['png'], clearable=False, multi=True, id='plot-file-format-select')
                                        ]
                                    )
                                ], className='col-2'
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Prepare', html_for='plot-download-button-group'),
                                            dbc.FormGroup(
                                                [
                                                    dbc.Button([html.I(className='fas fa-cogs')],
                                                               id='plot-download-button',
                                                               className='btn btn-info')
                                                ], id='plot-download-button-group'
                                            )
                                        ]
                                    )
                                ], className='col-1'
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Download', html_for='plot-download-link-group'),
                                            dbc.FormGroup(
                                                [
                                                    dcc.Loading(
                                                        html.A([html.I(className='fas fa-download')],
                                                               id='plot-download-link',
                                                               className='btn btn-secondary disabled')
                                                    )
                                                ], id='plot-download-link-group'
                                            )
                                        ]
                                    )
                                ], className='col-1'
                            )
                        ]
                    ),

                    dcc.Loading(html.Small('', id='plot-download-message', className='form-text')),
                    # will inject link when results posted
                    html.H5('Post Results'),
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
        )
    )


def get_plot_options_form():
    try:
        pca_data = PCAModel(load_data=True)
        label_options = [{'label': label, 'value': label} for label in pca_data.labels]
        results_exist = pca_data.results_exist
        pc_options = pca_data.get_pc_options()
    except:
        label_options = []
        results_exist = False
        pc_options = []
    plot_data = PCAModel.get_plot_data()
    return dbc.Card(
        dbc.CardBody(
            dbc.Form(
                [
                    html.H5('Scores Plots'),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('x-axis', html_for='abscissa-select'),
                                            dcc.Dropdown(id='abscissa-select', options=pc_options,
                                                         multi=False, value=0)
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('y-axis', html_for='ordinate-select'),
                                            dcc.Dropdown(id='ordinate-select',
                                                         options=pc_options, multi=False, value=1)
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('z-axis', html_for='applicate-select'),
                                            dcc.Dropdown(id='applicate-select',
                                                         options=[{'label': f'None', 'value': -1}] + pc_options,
                                                         multi=False, value=-1)
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Color by label(s)', html_for='color-by-select'),
                                            dcc.Dropdown(id='color-by-select',
                                                         options=label_options, multi=True)
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Point label(s)', html_for='label-by-select'),
                                            dcc.Dropdown(id='label-by-select',
                                                         options=label_options, multi=True)
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label(['Encircle metric',
                                                       html.Abbr('\uFE56',
                                                                 title='This will draw an oval shape to represent a category\'s'
                                                                       ' spread. These can be stacked as concentric rings.\n'
                                                                       'SEM: standard error of the mean\n'
                                                                       '\u03C3: standard deviation\n')],
                                                      html_for='encircle-by-select'),
                                            dcc.Dropdown(id='encircle-by-select',
                                                         options=[
                                                             {'label': '2 SEM', 'value': '2sem'},
                                                             {'label': 'SEM', 'value': '1sem'},
                                                             {'label': '2\u03C3', 'value': '2std'},
                                                             {'label': '\u03C3', 'value': '1std'},
                                                             {'label': 'Range', 'value': 'range'},
                                                             {'label': '95% Confidence', 'value': '95conf'},
                                                             {'label': '95th percentile', 'value': '95percentile'},
                                                         ],
                                                         multi=True)
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
                                    dbc.Checkbox(id='db-index'),
                                    dbc.Label([' Include DB index table?',
                                               html.Abbr('\uFE56',
                                                         title='Davies-Bouldin indices are calculated from the "Color by" label')],
                                              className='form-check-label', html_for='db-index')
                                ], className='form-check form-check-inline'
                            )
                        ], className='form-row'
                    ),
                    dbc.Row(
                        [
                            html.Div(
                                [
                                    dbc.Checkbox(id='centroid'),
                                    dbc.Label([' Mark centroids?',
                                               html.Abbr('\uFE56',
                                                         title='Centroids are calculated from the "Color by" label.')],
                                              className='form-check-label', html_for='centroid')
                                ], className='form-check form-check-inline'
                            )
                        ], className='form-row'
                    ),
                    dbc.Row(
                        [
                            html.Div(
                                [
                                    dbc.Checkbox(id='medoid'),
                                    dbc.Label([' Mark medoids?',
                                               html.Abbr('\uFE56',
                                                         title='Medoids are calculated from the "Color by" label.')],
                                              className='form-check-label', html_for='medoid')
                                ], className='form-check form-check-inline'
                            )
                        ], className='form-row'
                    ),
                    dbc.Row(
                        [
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
                                        f'PC{score_plot["ordinate"] + 1} vs PC{score_plot["abscissa"] + 1} '
                                        f'by {score_plot["color_by"]}')
                                    for score_plot in PCAModel.get_plot_data()["score_plots"]
                                ], id='score-plot-list'
                            )
                        ], className='form-row', id='score-plot-list-wrapper'
                    ),
                    dbc.Row(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Button([html.I(className='fas fa-eraser'), ' Clear'],
                                               id='score-plot-clear-button',
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
                                    dbc.ListGroupItem(PCAModel.component_list(plot['indices'])) for plot in
                                    plot_data['loading_plots']
                                ], id='loading-plot-list'
                            )
                        ], className='form-row', id='loading-plot-list-wrapper'
                    ),
                    dbc.Row(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Button([html.I(className='fas fa-eraser'), ' Clear'],
                                               id='loading-plot-clear-button',
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
                                    dbc.Label(' Scale y axis?', className='form-check-label',
                                              html_for='variance-autoscale')
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

                                    dbc.ListGroupItem(PCAModel.component_list(plot['indices'])
                                                      + (' (scaled y-axis)' if plot['scale_y'] else ''))
                                    for plot in plot_data['variance_plots']
                                ], id='variance-plot-list'
                            )
                        ], className='form-row', id='variance-plot-list-wrapper'
                    ),
                    dbc.Row(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Button([html.I(className='fas fa-eraser'), ' Clear'],
                                               id='variance-plot-clear-button',
                                               className='btn btn-danger')
                                ]
                            )
                        ], className='form-row'
                    ),
                    html.H5('Cumulative Variance Plots'),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label('Variance Threshold', html_for='cumulative-variance-input'),
                                            dbc.Input(id='cumulative-variance-input', type='number', value=95)
                                        ]
                                    )
                                ]
                            )
                        ], className='form-row'
                    ),
                    dbc.Row(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Button([html.I(className='fas fa-plus'), ' Add'],
                                               id='cumulative-variance-plot-add-button',
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
                                        [
                                            f"{cumulative_variance_plot['threshold']}"
                                            for cumulative_variance_plot in
                                            PCAModel.get_plot_data()['cumulative_variance_plots']
                                        ]
                                    )
                                ], id='cumulative-variance-plot-list'
                            )
                        ], className='form-row', id='cumulative-variance-plot-list-wrapper'
                    ),
                    dbc.Row(
                        [
                            dbc.FormGroup(
                                [
                                    dbc.Button([html.I(className='fas fa-eraser'), ' Clear'],
                                               id='cumulative-variance-plot-clear-button',
                                               className='btn btn-danger')
                                ]
                            )
                        ], className='form-row'
                    )
                ]
            )
        )
    )


def get_pca_options_form():
    try:
        collection_options = [
            {'label': f'{collection.id}: {collection.name}', 'value': collection.id}
            for collection in get_collections(current_user, {'kind': 'data'})
        ]
    except:
        collection_options = []
    try:
        pca_data = PCAModel(load_data=True)
        label_options = [{'label': label, 'value': label} for label in pca_data.labels]
        loaded_badges = pca_data.get_collection_badges()
        collection_load_info = pca_data.get_collection_load_info()
    except:
        loaded_badges = [html.Span([dbc.Badge('None', className='badge-pill')])]
        collection_load_info = 'Loaded collections.'
        label_options = []

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
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label(['Project by label(s)',
                                                       html.Abbr('\uFE56',
                                                                 title='Select additional data to be projected'
                                                                       ' on the PC axes created by the model.')],
                                                      html_for='additional-projection'),
                                            dcc.Dropdown(id='project-by', options=label_options, multi=True)
                                        ]
                                    )
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.FormGroup(
                                        [
                                            dbc.Label(['Project by conditions',
                                                       html.Abbr('\uFE56',
                                                                 title='The conditions which must be satisfied for the records'
                                                                       ' to be projected.')],
                                                      html_for='project-by-value'),
                                            dcc.Dropdown(id='project-by-value', options=[], multi=True)
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
                                    html.Small('', id='message', className='form-text')
                                ]
                            )
                        ]
                    )
                ]
            )
        )
    )


def get_plot_display_form():
    return dbc.Card(
        [
            dbc.CardHeader(
                dbc.Tabs(
                    [
                        dbc.Tab(label='Scores', tab_id='score-plot-tab'),
                        dbc.Tab(label='Loadings', tab_id='loadings-plot-tab'),
                        dbc.Tab(label='Variance', tab_id='variance-plot-tab'),
                        dbc.Tab(label='Cumulative Variance', tab_id='cumulative-variance-plot-tab')
                    ], id='plot-tabs', active_tab='score-plot-tab', card=True
                )
            ),
            dbc.CardBody(html.Div(id='plot-content'), id='plot-content-wrapper')
        ]
    )


def get_layout():
    return html.Div(
        [
            html.Br(),
            dbc.Container([
                html.H2('Principal Component Analysis'),
                dbc.Tabs(
                    [
                        dbc.Tab(get_pca_options_form(), id='pca-options-tab', label='PCA Options'),
                        dbc.Tab(get_plot_options_form(), id='plot-options-tab', label='Plot Options'),
                        dbc.Tab(get_save_results_form(), id='save-tab', label='Save Results'),
                        dbc.Tab(get_plot_display_form(), id='plot-tab', label='View Plots')
                    ], id='main-tabs'
                )
            ]),
            html.Div('in', id='units-history', style={'display': 'none'}),
            html.Div(100, id='dpi-history', style={'display': 'none'})
        ]
    )
