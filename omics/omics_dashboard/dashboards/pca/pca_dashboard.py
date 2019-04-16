import itertools
import re

import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State

from dashboards.dashboard import Dashboard
from dashboards.pca.layouts import get_layout
from .pca_data import get_plot_data, set_plot_data, PCAData


class PCADashboard(Dashboard):
    name = 'Principal Component Analysis'
    prefix = '/dashboards/pca/'
    description = 'Perform principal component analysis.'
    id = 'pca'

    @staticmethod
    def _register_callbacks(app):
        @app.callback(
            [Output('scale-by-value', 'options'),
             Output('scale-by-value', 'value')],
            [Input('scale-by', 'value')]
        )
        def update_scale_by_options(value):
            if None in value:
                raise ValueError('Callback triggered without action!')
            value = sorted(value)
            print(value)
            pca_data = PCAData()
            unique_values = [pca_data.unique_vals[val] for val in value]
            option_pairs = list(itertools.product(*unique_values))
            option_labels = [', '.join([str(val) for val in option_pair]) for option_pair in option_pairs]
            option_values = [','.join([f'<{val}>' for val in option_pair]) for option_pair in option_pairs]
            return (
                [{'label': option_label, 'value': option_value}
                 for option_label, option_value in zip(option_labels, option_values)],
                option_values[0]
            )

        @app.callback(
            [Output('filter-by-value', 'options'),
             Output('filter-by-value', 'value')],
            [Input('filter-by', 'value')]
        )
        def update_filter_by_options(value):
            if None in value:
                raise ValueError('Callback triggered without action!')
            value = sorted(value)
            print(value)
            pca_data = PCAData()
            unique_values = [pca_data.unique_vals[val] for val in value]
            option_pairs = list(itertools.product(*unique_values))
            option_labels = [', '.join([str(val) for val in option_pair]) for option_pair in option_pairs]
            option_values = [','.join([f'<{val}>' for val in option_pair]) for option_pair in option_pairs]
            return (
                [{'label': option_label, 'value': option_value}
                 for option_label, option_value in zip(option_labels, option_values)],
                option_values[0]
            )

        @app.callback(
            [Output('ignore-by-value', 'options'),
             Output('ignore-by-value', 'value')],
            [Input('ignore-by', 'value')]
        )
        def update_ignore_by_options(value):
            if None in value:
                raise ValueError('Callback triggered without action!')
            value = sorted(value)
            print(value)

            pca_data = PCAData()
            unique_values = [pca_data.unique_vals[val] for val in value]
            option_pairs = list(itertools.product(*unique_values))
            option_labels = [', '.join([str(val) for val in option_pair]) for option_pair in option_pairs]
            option_values = [','.join([f'<{val}>' for val in option_pair]) for option_pair in option_pairs]
            return [{'label': option_label, 'value': option_value}
                    for option_label, option_value in zip(option_labels, option_values)], option_values[0]

        @app.callback(
            [Output('scale-by', 'options'),
             Output('filter-by', 'options'),
             Output('ignore-by', 'options'),
             Output('merge-by', 'options'),
             Output('color-by-select', 'options'),
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
             Output('variance-select', 'value')],
            [Input('pca-button', 'n_clicks')],
            [State('scale-by', 'value'),
             State('scale-by-value', 'value'),
             State('filter-by', 'value'),
             State('filter-by-value', 'value'),
             State('ignore-by', 'value'),
             State('ignore-by-value', 'value'),
             State('merge-by', 'value'),
             State('merge-by-method', 'value')]
        )
        def perform_pca(n_clicks,
                        scale_by, scale_by_values,
                        filter_by, filter_by_values,
                        ignore_by, ignore_by_values,
                        merge_by, merge_by_method):
            if not n_clicks:
                raise ValueError('Callback triggered without click.')
            params = {}
            pca_data = PCAData()

            def process_value(value):
                pattern = re.compile('<([\w\s]+)+>')
                return [group for group in pattern.findall(value)]

            if scale_by is not None and len(scale_by) and scale_by_values is not None and len(scale_by_values):
                params['scale_by'] = []
                split_values = [process_value(value) for value in scale_by_values]  # list of lists
                for split_value in split_values:
                    params['scale_by'] += [pair for pair in zip(scale_by, split_value)]

            if filter_by is not None and len(filter_by) and filter_by_values is not None and len(filter_by_values):
                params['filter_by'] = []
                split_values = [process_value(value) for value in filter_by_values]  # list of lists
                for split_value in split_values:
                    params['filter_by'] += [pair for pair in zip(filter_by, split_value)]

            if ignore_by is not None and len(ignore_by) and ignore_by_values is not None and len(ignore_by_values):
                params['ignore_by'] = []
                split_values = [process_value(value) for value in ignore_by_values]  # list of lists
                for split_value in split_values:
                    params['ignore_by'] += [pair for pair in zip(ignore_by, split_value)]

            if merge_by is not None and len(merge_by):
                params['merge_by'] = {'labels': merge_by, 'method': merge_by_method}

            message = pca_data.perform_pca(params)
            pc_options = pca_data.get_pc_options()
            all_pc_options = [option['value'] for option in pc_options]
            ten_pc_options = [option['value'] for option in pc_options[:10]]

            return (
                message,
                False,
                pc_options,
                0,
                pc_options,
                1,
                pc_options,
                ten_pc_options,
                pc_options,
                all_pc_options
            )

        @app.callback(
            [Output('score-plot-list', 'children')],
            [Input('score-plot-add-button', 'n_clicks')],
            [
                State('abscissa-select', 'value'),
                State('ordinate-select', 'value'),
                State('color-by-select', 'value'),
            ]
        )
        def add_score_plot(n_clicks, abscissa_value, ordinate_value, color_by_value):
            if not n_clicks:
                raise ValueError('')

            plot_data = get_plot_data()
            plot_data['score_plots'].append(
                {
                    'ordinate': ordinate_value,
                    'abscissa': abscissa_value,
                    'color_by': color_by_value
                }
            )
            set_plot_data(plot_data)

            return [[
                dbc.ListGroupItem(f'{plot["ordinate"] + 1} vs {plot["abscissa"] + 1} by {plot["color_by"]}')
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
            print(plot_data)
            plot_data['loading_plots'].append(
                {
                    'indices': loading_value
                }
            )
            set_plot_data(plot_data)

            return [[
                dbc.ListGroupItem(','.join([f'PC{loading + 1}' for loading in plot['indices']]))
                for plot in plot_data['loading_plots']
            ]]

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
                dbc.ListGroupItem(','.join([f'PC{component + 1}' for component in plot['indices']])
                                  + ' (autoscaled)' if plot['scale_y'] else '')
                for plot in plot_data['variance_plots']
            ]]

        @app.callback(
            [Output('score-card-body', 'children'),
             Output('loading-card-body', 'children'),
             Output('variance-card-body', 'children')],
            [Input('plot-button', 'n_clicks')]
        )
        def update_figure(n_clicks):
            if not n_clicks:
                raise ValueError('Callback triggered without click.')
            plot_data = get_plot_data()
            pca_data = PCAData()
            return pca_data.get_plots(plot_data['score_plots'], plot_data['loading_plots'], plot_data['variance_plots'])

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
        def clear_loading_plots(n_clicks):
            if not n_clicks:
                raise ValueError('no clicks!')
            plot_data = get_plot_data()
            plot_data['variance_plots'] = []
            set_plot_data(plot_data)
            return [dbc.ListGroup([], id='variance-plot-list')]

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
