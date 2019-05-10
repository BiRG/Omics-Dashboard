import itertools
import traceback

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Output, Input, State
from flask import url_for

from dashboards.dashboard import Dashboard
from .layouts import get_layout
from .pca_data import get_plot_data, set_plot_data, PCAData, component_list


class PCADashboard(Dashboard):
    name = 'Principal Component Analysis'
    prefix = '/dashboards/pca/'
    description = 'Perform principal component analysis.'
    id = 'pca'

    @staticmethod
    def _on_label_key_select(label_keys, op='=='):
        if not label_keys or None in label_keys:
            raise ValueError('Callback triggered without action!')
        label_keys = sorted(label_keys)
        pca_data = PCAData()
        unique_values = [pca_data.unique_vals[val] for val in label_keys]
        option_pairs = list(itertools.product(*unique_values))
        queries = [' & '.join([f'{key}{op}"{value}"' for key, value in zip(label_keys, option_pair)])
                   for option_pair in option_pairs]
        query_labels = [','.join([f'{key}={value}' for key, value in zip(label_keys, option_pair)])
                        for option_pair in option_pairs]
        return [[{'label': query_label, 'value': query} for query_label, query in zip(query_labels, queries)]]

    @staticmethod
    def _register_callbacks(app):
        @app.callback(
            [Output('scale-by-value', 'options')],
            [Input('scale-by', 'value')]
        )
        def update_scale_by_options(label_keys):
            return PCADashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('filter-by-value', 'options')],
            [Input('filter-by', 'value')]
        )
        def update_filter_by_options(label_keys):
            return PCADashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('ignore-by-value', 'options')],
            [Input('ignore-by', 'value')]
        )
        def update_ignore_by_options(label_keys):
            return PCADashboard._on_label_key_select(label_keys, op='!=')

        @app.callback(
            [Output('pair-with-value', 'options')],
            [Input('pair-with', 'value')]
        )
        def update_pair_with_options(label_keys):
            if not label_keys or None in label_keys:
                raise ValueError('Callback triggered without action!')
            return PCADashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('scale-by', 'options'),
             Output('filter-by', 'options'),
             Output('ignore-by', 'options'),
             Output('pair-on', 'options'),
             Output('pair-with', 'options'),
             Output('color-by-select', 'options'),
             Output('label-by-select', 'options'),
             Output('loaded-collections', 'children'),
             Output('collections-label', 'children')],
            [Input('get-collection', 'n_clicks')],
            [State('collection-id', 'value')],
        )
        def get_collections(n_clicks, value):
            if not value or not n_clicks:
                raise ValueError('Callback triggered without value')
            pca_data = PCAData()
            pca_data.get_collections(value)
            label_data = pca_data.get_label_data()
            return (
                label_data,
                label_data,
                label_data,
                label_data,
                label_data,
                label_data,
                label_data,
                pca_data.get_collection_badges(),
                pca_data.get_collection_load_info()
            )

        @app.callback(
            [Output('message', 'children'),
             Output('plot-button', 'disabled'),
             Output('abscissa-select', 'options'),
             Output('abscissa-select', 'value'),
             Output('ordinate-select', 'options'),
             Output('ordinate-select', 'value'),
             Output('loading-select', 'options'),
             Output('loading-select', 'value'),
             Output('variance-select', 'options'),
             Output('variance-select', 'value'),
             Output('name-input', 'value')],
            [Input('pca-button', 'n_clicks')],
            [State('scale-by-value', 'value'),
             State('filter-by-value', 'value'),
             State('ignore-by-value', 'value'),
             State('pair-on', 'value'),
             State('pair-with-value', 'value')]
        )
        def perform_pca(n_clicks,
                        scale_by_queries,
                        filter_by_queries,
                        ignore_by_queries,
                        pair_on, pair_with_queries):
            if not n_clicks:
                raise ValueError('Callback triggered without click.')
            scale_by = ' | '.join(scale_by_queries) if scale_by_queries and len(scale_by_queries) else None
            filter_by = ' | '.join(filter_by_queries) if filter_by_queries and len(filter_by_queries) else None
            ignore_by = ' | '.join(ignore_by_queries) if ignore_by_queries and len(ignore_by_queries) else None
            pair_on = pair_on if pair_on and len(pair_on) else None
            pair_with = ' | '.join(pair_with_queries) if pair_with_queries and len(
                pair_with_queries) and pair_on else None
            pca_data = PCAData()
            try:
                message, name, message_color = pca_data.perform_pca(filter_by, ignore_by, scale_by, pair_on, pair_with)
                pc_options = pca_data.get_pc_options()
                all_pc_options = [option['value'] for option in pc_options]
                ten_pc_options = [option['value'] for option in pc_options[:10]]
            except Exception as e:
                message = [html.P([html.Strong('Error: '), f'{e}']),
                           html.Strong('Traceback:'),
                           html.P(html.Pre(traceback.format_exc(), className='text-white'))]
                message_color = 'danger'
                name = ''
                pc_options = []
                all_pc_options = []
                ten_pc_options = []

            return (
                dbc.Alert(message, color=message_color, dismissable=True),
                False,
                pc_options,
                0,
                pc_options,
                1,
                pc_options,
                ten_pc_options,
                pc_options,
                all_pc_options,
                name
            )

        @app.callback(
            [Output('score-plot-list', 'children')],
            [Input('score-plot-add-button', 'n_clicks')],
            [
                State('abscissa-select', 'value'),
                State('ordinate-select', 'value'),
                State('color-by-select', 'value'),
                State('label-by-select', 'value'),
                State('db-index', 'checked'),
                State('centroid', 'checked'),
                State('medoid', 'checked'),
                State('encircle-by-select', 'value')
            ]
        )
        def add_score_plot(n_clicks,
                           abscissa_value,
                           ordinate_value,
                           color_by_value,
                           label_by_value,
                           include_db_index,
                           include_centroid,
                           include_medoid,
                           encircle_by_value):
            if not n_clicks:
                raise ValueError('')

            plot_data = get_plot_data()
            plot_data['score_plots'].append(
                {
                    'ordinate': ordinate_value,
                    'abscissa': abscissa_value,
                    'color_by': color_by_value,
                    'label_by': label_by_value,
                    'include_centroid': include_centroid,
                    'include_medoid': include_medoid,
                    'encircle_by': encircle_by_value,
                    'include_db_index': include_db_index
                }
            )
            set_plot_data(plot_data)

            return [[
                dbc.ListGroupItem(f'PC{plot["ordinate"] + 1} vs PC{plot["abscissa"] + 1} by {plot["color_by"]}' + (
                    ' with DB Index' if plot['include_db_index'] else ''))
                for plot in plot_data['score_plots']
            ]]

        @app.callback(
            [Output('loading-plot-list', 'children')],
            [Input('loading-plot-add-button', 'n_clicks')],
            [State('loading-select', 'value')]
        )
        def add_loading_plot(n_clicks, loading_value):
            if not n_clicks:
                raise ValueError('')

            plot_data = get_plot_data()
            plot_data['loading_plots'].append(
                {
                    'indices': loading_value
                }
            )
            set_plot_data(plot_data)
            return [[dbc.ListGroupItem(component_list(plot['indices'])) for plot in plot_data['loading_plots']]]

        @app.callback(
            [Output('variance-plot-list', 'children')],
            [Input('variance-plot-add-button', 'n_clicks')],
            [State('variance-select', 'value'), State('variance-autoscale', 'checked')]
        )
        def add_variance_plot(n_clicks, indices, scale_y):
            if not n_clicks:
                raise ValueError('')
            plot_data = get_plot_data()
            plot_data['variance_plots'].append(
                {
                    'indices': indices,
                    'scale_y': scale_y
                }
            )
            set_plot_data(plot_data)
            return [[
                dbc.ListGroupItem(component_list(plot['indices'])
                                  + (' (scaled y-axis)' if plot['scale_y'] else ''))
                for plot in plot_data['variance_plots']
            ]]

        @app.callback(
            [Output('cumulative-variance-plot-list', 'children')],
            [Input('cumulative-variance-plot-add-button', 'n_clicks')],
            [State('cumulative-variance-input', 'value')]
        )
        def add_cumulative_variance_plot(n_clicks, threshold):
            if not n_clicks:
                raise ValueError('')
            plot_data = get_plot_data()
            plot_data['cumulative_variance_plots'].append({'threshold': float(threshold)})
            set_plot_data(plot_data)
            return [[
                dbc.ListGroupItem(
                    [
                        f"{cumulative_variance_plot['threshold']}"
                        for cumulative_variance_plot in plot_data['cumulative_variance_plots']
                    ]
                )
            ]]

        @app.callback(
            [Output('score-card-body', 'children'),
             Output('loading-card-body', 'children'),
             Output('variance-card-body', 'children'),
             Output('cumulative-variance-card-body', 'children')],
            [Input('plot-button', 'n_clicks')]
        )
        def update_figure(n_clicks):
            if not n_clicks:
                raise ValueError('Callback triggered without click.')
            plot_data = get_plot_data()
            pca_data = PCAData()
            return pca_data.get_plots(plot_data['score_plots'],
                                      plot_data['loading_plots'],
                                      plot_data['variance_plots'],
                                      plot_data['cumulative_variance_plots'])

        @app.callback(
            [Output('score-plot-list-wrapper', 'children')],
            [Input('score-plot-clear-button', 'n_clicks')]
        )
        def clear_score_plots(n_clicks):
            if not n_clicks:
                raise ValueError('no clicks!')
            plot_data = get_plot_data()
            plot_data['score_plots'] = []
            set_plot_data(plot_data)
            return [dbc.ListGroup([], id='score-plot-list')]

        @app.callback(
            [Output('loading-plot-list-wrapper', 'children')],
            [Input('loading-plot-clear-button', 'n_clicks')]
        )
        def clear_loading_plots(n_clicks):
            if not n_clicks:
                raise ValueError('no clicks!')
            plot_data = get_plot_data()
            plot_data['loading_plots'] = []
            set_plot_data(plot_data)
            return [dbc.ListGroup([], id='loading-plot-list')]

        @app.callback(
            [Output('variance-plot-list-wrapper', 'children')],
            [Input('variance-plot-clear-button', 'n_clicks')]
        )
        def clear_variance_plots(n_clicks):
            if not n_clicks:
                raise ValueError('no clicks!')
            plot_data = get_plot_data()
            plot_data['variance_plots'] = []
            set_plot_data(plot_data)
            return [dbc.ListGroup([], id='variance-plot-list')]

        @app.callback(
            [Output('cumulative-variance-plot-list-wrapper', 'children')],
            [Input('cumulative-variance-plot-clear-button', 'n_clicks')]
        )
        def clear_variance_plots(n_clicks):
            if not n_clicks:
                raise ValueError('no clicks!')
            plot_data = get_plot_data()
            plot_data['cumulative_variance_plots'] = []
            set_plot_data(plot_data)
            return [dbc.ListGroup([], id='cumulative-variance-plot-list')]

        @app.callback(
            [Output('download-link', 'href'),
             Output('download-link', 'className'),
             Output('download-message', 'children')],
            [Input('download-button', 'n_clicks')],
            [State('results-select', 'value'),
             State('file-format-select', 'value')]
        )
        def prepare_results_file(n_clicks, results_values, file_format_values):
            score_plot_data = get_plot_data()['score_plots']
            pca_data = PCAData()
            if not n_clicks:
                raise ValueError('no clicks')
            if not pca_data.results_exist:
                return '#', dbc.Alert('Results do not exist.', color='warning', dismissable=True)
            try:
                path = pca_data.download_results('scores' in results_values,
                                                 'loadings' in results_values,
                                                 'explained_variance' in results_values,
                                                 'db_indices' in results_values,
                                                 file_format_values,
                                                 score_plot_data)
                message = dbc.Alert(f'Prepared results file as {path}', color='success', dismissable=True)
                class_name = 'btn btn-success'
            except Exception as e:
                path = '#'
                message = dbc.Alert(f'{e}', color='danger', dismissable=True)
                class_name = 'btn btn-secondary disabled'
            return url_for('api.download_temporary_file', path=path), class_name, message

        @app.callback(
            [Output('plot-download-link', 'href'),
             Output('plot-download-link', 'className'),
             Output('plot-download-message', 'children')],
            [Input('plot-download-button', 'n_clicks')],
            [State('plot-file-format-select', 'value')]
        )
        def prepare_plots_file(n_clicks, file_format_values):
            plot_data = get_plot_data()
            pca_data = PCAData()
            if not n_clicks:
                raise ValueError('no clicks')
            if not pca_data.results_exist:
                return '#', dbc.Alert('Results do not exist.', color='warning', dismissable=True)
            try:
                path = pca_data.download_plots(plot_data['score_plots'],
                                               plot_data['loading_plots'],
                                               plot_data['variance_plots'],
                                               plot_data['cumulative_variance_plots'],
                                               file_format_values)
                message = dbc.Alert(f'Prepared plots file as {path}.', color='success', dismissable=True)
                class_name = 'btn btn-success'
            except Exception as e:
                path = '#'
                message = dbc.Alert(f'{e}', color='danger', dismissable=True)
                class_name = 'btn btn-secondary disabled'
            return url_for('api.download_temporary_file', path=path), class_name, message

        @app.callback(
            [Output('post-message', 'children')],
            [Input('post-button', 'n_clicks')],
            [State('name-input', 'value'), State('analysis-select', 'value')]
        )
        def post_results(n_clicks, name, analysis_ids):
            if not n_clicks:
                raise ValueError('no clicks')
            pca_data = PCAData()
            try:
                iter(analysis_ids)
            except TypeError:
                analysis_ids = [analysis_ids]
            try:
                return pca_data.post_results(name, analysis_ids)
            except Exception as e:
                return [dbc.Alert(f'{e}', dismissable=True, color='danger')]

    @staticmethod
    def _register_layout(app):
        app.layout = get_layout

    @staticmethod
    def _register_dash_app(app):
        app.title = PCADashboard.name
        PCADashboard._register_layout(app)
        PCADashboard._register_callbacks(app)

    @staticmethod
    def create_dash_app(server):
        # no users are logged in when this is created so we can't set light/dark theme preference
        app = dash.Dash(__name__,
                        server=server,
                        routes_pathname_prefix=PCADashboard.prefix,
                        requests_pathname_prefix='/omics' + PCADashboard.prefix,
                        external_stylesheets=[dbc.themes.FLATLY,
                                              'https://use.fontawesome.com/releases/v5.8.1/css/all.css'])
        # noinspection PyTypeChecker
        PCADashboard._register_dash_app(app)
        return app
