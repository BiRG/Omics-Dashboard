import itertools

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

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
            if not value or not n_clicks:
                raise PreventUpdate('Callback triggered without value')
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

        @app.callback([Output('plot-wrapper', 'children')],
                      [Input('plot-button', 'n_clicks')],
                      [State('group-by-value', 'value'), State('label-by', 'value')])
        def update_plot(n_clicks, queries, labels):
            print(f'n_clicks={n_clicks}!')
            if not queries or not n_clicks:
                raise PreventUpdate('Callback triggered without value')
            viz_data = VisualizationData(True)
            return [viz_data.get_plot(queries, labels, get_plot_theme())]

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
