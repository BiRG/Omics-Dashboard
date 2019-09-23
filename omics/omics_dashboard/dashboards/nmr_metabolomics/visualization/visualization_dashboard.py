import itertools
import traceback

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from flask import url_for

from dashboards import Dashboard
from dashboards.dashboard import get_plot_theme, StyledDash
from .layouts import get_layout
from .visualization_data import VisualizationData


class VisualizationDashboard(Dashboard):
    name = 'Visualization'
    prefix = '/dashboards/visualization/'
    description = 'Visualize collections.'
    id = 'viz'

    @staticmethod
    def _on_label_key_select(label_keys, op='=='):
        if not label_keys or None in label_keys:
            raise PreventUpdate('Callback triggered without action!')
        label_keys = sorted(label_keys)
        viz_data = VisualizationData()
        unique_values = [viz_data.unique_vals[val] for val in label_keys]
        option_pairs = list(itertools.product(*unique_values))
        queries = [' & '.join([f'{key}{op}"{value}"' for key, value in zip(label_keys, option_pair)])
                   for option_pair in option_pairs]
        query_labels = [','.join([f'{key}={value}' for key, value in zip(label_keys, option_pair)])
                        for option_pair in option_pairs]
        return [[{'label': query_label, 'value': query} for query_label, query in zip(query_labels, queries)]]

    @staticmethod
    def _register_callbacks(app):
        @app.callback(
            [Output('group-by', 'options'),
             Output('label-by', 'options'),
             Output('loaded-collections', 'children'),
             Output('collections-label', 'children')],
            [Input('get-collection', 'n_clicks')],
            [State('collection-id', 'value')],
        )
        def get_collections(n_clicks, value):
            VisualizationDashboard.check_clicks(n_clicks)
            if not value:
                raise PreventUpdate('Nothing to load.')
            viz_data = VisualizationData()
            viz_data.get_collections(value)
            label_data = viz_data.get_label_data()
            return (
                label_data,
                label_data,
                viz_data.get_collection_badges(),
                viz_data.get_collection_load_info()
            )

        @app.callback([Output('group-by-value', 'options')], [Input('group-by', 'value')])
        def update_group_by_options(label_keys):
            return VisualizationDashboard._on_label_key_select(label_keys)

        @app.callback([Output('main-plot', 'figure')],
                      [Input('plot-button', 'n_clicks')],
                      [State('group-by-value', 'value'),
                       State('label-by', 'value'),
                       State('bin-collection', 'value'),
                       State('legend-style-select', 'value')])
        def update_plot(n_clicks, queries, labels, bin_collection_id, legend_style):
            VisualizationDashboard.check_clicks(n_clicks)
            if not queries:
                raise PreventUpdate('Nothing to plot!')
            viz_data = VisualizationData(True)
            return [viz_data.get_plot(queries, labels, get_plot_theme(), bin_collection_id, legend_style)]

        @app.callback(
            [Output('summary-table-wrapper', 'children')],
            [Input('main-plot', 'relayoutData')],
            [State('group-by-value', 'value'),
             State('label-by', 'value')]
        )
        def selection_changed(relayout_data, queries, labels):
            if relayout_data is not None:
                if 'xaxis.range[0]' and 'xaxis.range[1]' in relayout_data:
                    val1, val2 = relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']
                    x_min = min(val1, val2)
                    x_max = max(val1, val2)
                    viz_data = VisualizationData(True)
                    return [viz_data.get_summary(queries, labels, x_min, x_max, get_plot_theme())]
            return ['']

        @app.callback(
            [Output('download-link', 'href'),
             Output('download-link', 'className'),
             Output('download-message', 'children')],
            [Input('download-button', 'n_clicks')],
            [State('main-plot', 'figure'),
             State('file-format-select', 'value')]
        )
        def prepare_plot(n_clicks, figure, file_format):
            VisualizationDashboard.check_clicks(n_clicks)
            viz_data = VisualizationData(False)
            try:
                path = viz_data.save_figure(figure, file_format)
                message = dbc.Alert(f'Prepared plots file as {path}.', color='success', dismissable=True)
                class_name = 'btn btn-success'
            except Exception as e:
                path = '#'
                message = dbc.Alert([html.P([html.Strong('Error: '), f'{e}']),
                                     html.Strong('Traceback:'),
                                     html.P(html.Pre(traceback.format_exc(), className='text-white'))],
                                    color='danger', dismissable=True)
                class_name = 'btn btn-secondary disabled'
            return url_for('api.download_temporary_file', path=path), class_name, message

    @staticmethod
    def _register_layout(app):
        app.layout = get_layout

    @staticmethod
    def _register_dash_app(app):
        app.title = VisualizationDashboard.name
        VisualizationDashboard._register_layout(app)
        VisualizationDashboard._register_callbacks(app)

    @staticmethod
    def create_dash_app(server):
        # no users are logged in when this is created so we can't set light/dark theme preference
        app = StyledDash(__name__,
                         server=server,
                         routes_pathname_prefix=VisualizationDashboard.prefix,
                         requests_pathname_prefix='/omics' + VisualizationDashboard.prefix,
                         external_stylesheets=['https://use.fontawesome.com/releases/v5.8.1/css/all.css'])
        # noinspection PyTypeChecker
        VisualizationDashboard._register_dash_app(app)
        return app
