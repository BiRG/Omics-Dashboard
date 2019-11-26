import itertools
import traceback

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Output, Input, State
from flask import url_for
from rq.job import Job

from dashboards.dashboard import Dashboard, StyledDash, get_plot_theme
from helpers import log_internal_exception
from .layouts import get_layout
from .model import OPLSModel
import config.redis_config as rds


class OPLSDashboard(Dashboard):
    name = 'Orthogonal Projection To Latent Structures'
    prefix = '/dashboards/opls/'
    description = 'Perform orthogonal projection to latent structures.'
    id = 'opls'

    @staticmethod
    def _on_label_key_select(label_keys, op='=='):
        OPLSDashboard.check_dropdown(label_keys)
        label_keys = sorted(label_keys)
        opls_data = OPLSModel()
        unique_values = [opls_data.unique_vals[val] for val in label_keys]
        option_pairs = list(itertools.product(*unique_values))
        queries = ['index'] + [' & '.join([f'{key}{op}"{value}"' for key, value in zip(label_keys, option_pair)])
                               for option_pair in option_pairs]
        query_labels = ['All Records'] + [','.join([f'{key}={value}' for key, value in zip(label_keys, option_pair)])
                                          for option_pair in option_pairs]
        return [[{'label': query_label, 'value': query}
                 for query_label, query in zip(query_labels, queries)
                 if opls_data.query_exists(query)]]

    @staticmethod
    def _register_callbacks(app):
        @app.callback(
            [Output('scale-by-value', 'options')],
            [Input('scale-by', 'value')]
        )
        def update_scale_by_options(label_keys):
            return OPLSDashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('model-by-value', 'options')],
            [Input('model-by', 'value')]
        )
        def update_model_by_options(label_keys):
            return OPLSDashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('ignore-by-value', 'options')],
            [Input('ignore-by', 'value')]
        )
        def update_ignore_by_options(label_keys):
            return OPLSDashboard._on_label_key_select(label_keys, op='!=')

        @app.callback(
            [Output('pair-with-value', 'options')],
            [Input('pair-with', 'value')]
        )
        def update_pair_with_options(label_keys):
            OPLSDashboard.check_dropdown(label_keys)
            return OPLSDashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('scale-by', 'options'),
             Output('model-by', 'options'),
             Output('ignore-by', 'options'),
             Output('pair-on', 'options'),
             Output('pair-with', 'options'),
             Output('target-variable', 'options'),
             Output('loaded-collections', 'children'),
             Output('collections-label', 'children')],
            [Input('get-collection', 'n_clicks')],
            [State('collection-id', 'value')],
        )
        def get_collections(n_clicks, value):
            OPLSDashboard.check_clicks(n_clicks)
            opls_data = OPLSModel()
            opls_data.get_collections(value)
            label_data = opls_data.get_label_data()
            label_data_with_type = opls_data.get_label_data(with_type=True)
            return (
                label_data,
                label_data,
                label_data,
                label_data,
                label_data,
                label_data_with_type,
                opls_data.get_collection_badges(),
                opls_data.get_collection_load_info()
            )

        @app.callback(
            [Output('loaded-results-collection', 'children')],
            [Input('get-results-collection', 'n_clicks')],
            [State('results-collection-id', 'value')]
        )
        def load_results(n_clicks, results_collection_id):
            OPLSDashboard.check_clicks(n_clicks)
            opls_data = OPLSModel()
            opls_data.get_results_collection(results_collection_id)
            return opls_data.get_results_collection_badges()

        @app.callback(
            [Output('message', 'children'),
             Output('loaded-results-collection-wrapper', 'children')],
            [Input('opls-button', 'n_clicks')],
            [State('scale-by-value', 'value'),
             State('model-by-value', 'value'),
             State('ignore-by-value', 'value'),
             State('pair-on', 'value'),
             State('pair-with-value', 'value'),
             State('target-variable', 'value'),
             State('regression-type', 'value'),
             State('multiclass-behavior', 'value'),
             State('min-n-components', 'value'),
             State('cross-val-k', 'value'),
             State('inner-test-alpha', 'value'),
             State('outer-test-alpha', 'value'),
             State('permutations', 'value'),
             State('inner-permutations', 'value'),
             State('outer-permutations', 'value')]
        )
        def perform_opls(n_clicks,
                         scale_by_queries,
                         model_by_queries,
                         ignore_by_queries,
                         pair_on, pair_with_queries,
                         target,
                         regression_type,
                         multiclass_behavior,
                         min_n_components,
                         cross_val_k,
                         inner_test_alpha,
                         outer_test_alpha,
                         permutations,
                         inner_permutations,
                         outer_permutations):
            OPLSDashboard.check_clicks(n_clicks)
            scale_by = ' | '.join(scale_by_queries) if scale_by_queries and len(scale_by_queries) else None
            model_by = ' | '.join(model_by_queries) if model_by_queries and len(model_by_queries) else None
            ignore_by = ' | '.join(ignore_by_queries) if ignore_by_queries and len(ignore_by_queries) else None
            pair_on = pair_on if pair_on and len(pair_on) else None
            pair_with = ' | '.join(pair_with_queries) if pair_with_queries and len(
                pair_with_queries) and pair_on else None
            opls_data = OPLSModel()
            try:
                if target is None:
                    raise ValueError('Please select a target variable (y).')
                message, name, message_color = opls_data.submit_job(model_by,
                                                                    ignore_by,
                                                                    scale_by,
                                                                    pair_on,
                                                                    pair_with,
                                                                    target,
                                                                    regression_type,
                                                                    multiclass_behavior,
                                                                    min_n_components,
                                                                    cross_val_k,
                                                                    inner_test_alpha,
                                                                    outer_test_alpha,
                                                                    permutations,
                                                                    inner_permutations,
                                                                    outer_permutations)
                badges = opls_data.get_results_collection_badges()
            except Exception as e:
                log_internal_exception(e)
                message = [html.P([html.Strong('Error: '), f'{e}']),
                           html.Strong('Traceback:'),
                           html.P(html.Pre(traceback.format_exc(), className='text-white'))]
                message_color = 'danger'
                badges = [html.Span([dbc.Badge('None', className='badge-pill', color='warning'), ' '])]
            return (
                dbc.Alert(message, color=message_color, dismissable=True),
                html.Div(badges, id='loaded-results-collection')
            )

        @app.callback([Output('results-content', 'children')],
                      [Input('results-tabs', 'active_tab')])
        def switch_results_tab(at):
            try:
                opls_data = OPLSModel()
                theme = get_plot_theme()
                if at == 'summary-tab':
                    return [dbc.Card(dbc.CardBody(opls_data.get_summary_tables(theme)))]
                elif at == 'quality-tab':
                    return [dbc.Card(dbc.CardBody(opls_data.get_quality_plots(theme)))]
                elif at == 'kde-tab':
                    return [dbc.Card(dbc.CardBody(opls_data.get_metric_kde_plots(theme)))]
                elif at == 'feature-significance-tab':
                    return [dbc.Card(dbc.CardBody(opls_data.get_loading_significance_tables(theme)))]
                else:
                    return [dbc.Card(dbc.CardBody(html.H6('Error occurred.')))]
            except Exception as e:
                log_internal_exception(e)
                return [dbc.Card(dbc.CardBody([html.H6('Error occurred.'), html.Code(traceback.format_exc())]))]

        @app.callback(
            [Output('width-input', 'value'),
             Output('height-input', 'value'),
             Output('units-history', 'children'),
             Output('dpi-history', 'children')],
            [Input('units-select', 'value'),
             Input('dpi-input', 'value')],
            [State('width-input', 'value'),
             State('height-input', 'value'),
             State('units-history', 'children'),
             State('dpi-history', 'children')]
        )
        def update_units(units, dpi, width, height, prev_units, prev_dpi):
            return Dashboard.convert_image_size_units(units, dpi, width, height, prev_units, prev_dpi)

        @app.callback(
            [Output('results-tabs', 'active_tab')],
            [Input('tabs', 'active_tab')],
            [State('results-tabs', 'active_tab')]
        )
        def activate_current_tab(current_main_tab, current_results_tab):
            # A kludge to force rendering of current plot tab when switching to plots tab.
            return [current_results_tab]

        @app.callback(
            [Output('progress-interval', 'interval')],
            [Input('plot-download-button', 'n_clicks')],
            [State('plot-file-format-select', 'value'),
             State('width-input', 'value'),
             State('height-input', 'value'),
             State('units-history', 'children'),
             State('dpi-history', 'children')]
        )
        def prepare_plots_file(n_clicks, file_format_values, width, height, units, dpi):
            opls_data = OPLSModel()
            OPLSDashboard.check_clicks(n_clicks)
            if not opls_data.results_file_ready:
                return 3600000
            job = opls_data.download_plots(file_format_values, width, height, units, dpi)
            print(f'Started ')
            rds.set_value(f'{OPLSModel.redis_prefix}_job_id', job.id)
            return [500]

        @app.callback(
            [Output('progress', 'value'),
             Output('progress', 'animated'),
             Output('progress-badge', 'children'),
             Output('progress-label', 'children'),
             Output('plot-download-link', 'href'),
             Output('plot-download-link', 'className'),
             Output('plot-download-message', 'children')],
            [Input('progress-interval', 'n_intervals')]
        )
        def update_progress(n_intervals):
            progress = rds.get_value(f'{OPLSModel.redis_prefix}_image_save_progress')
            progress_fraction = rds.get_value(f'{OPLSModel.redis_prefix}_image_save_progress_fraction')
            label_text = rds.get_value(f'{OPLSModel.redis_prefix}_image_save_label')
            job_id = rds.get_value(f'{OPLSModel.redis_prefix}_job_id').decode('utf-8')
            job = Job.fetch(job_id, rds.get_redis())
            job_status = job.get_status()
            if isinstance(label_text, bytes):
                label_text = label_text.decode('utf-8')
            if isinstance(progress, bytes):
                progress = int(float(progress))
            if isinstance(progress_fraction, bytes):
                progress_fraction = progress_fraction.decode('utf-8')

            if job_status == 'finished':
                message = dbc.Alert(f'Prepared plots file as {job.result}.', color='success', dismissable=True)
                class_name = 'btn btn-success'
                path = job.result
                progress_label = dbc.FormText(label_text, color='success')
                animated = False
            elif job.get_status() == 'failed':
                message = dbc.Alert([f'Error occurred.', html.Pre(job.exc_info)], color='danger', dismissable=True)
                class_name = 'btn btn-secondary disabled'
                path = ''
                progress_label = dbc.FormText(label_text, color='danger')
                animated = False
            else:
                message = []
                class_name = 'btn btn-secondary disabled'
                path = ''
                progress_label = dbc.FormText(label_text)
                animated = True
            return progress, animated, progress_fraction, progress_label, url_for('api.download_temporary_file', path=path), class_name, message

    @staticmethod
    def _register_layout(app):
        app.layout = get_layout

    @staticmethod
    def _register_dash_app(app):
        app.title = OPLSDashboard.name
        OPLSDashboard._register_layout(app)
        OPLSDashboard._register_callbacks(app)

    @staticmethod
    def create_dash_app(server):
        # no users are logged in when this is created so we can't set light/dark theme preference
        app = StyledDash(__name__,
                         server=server,
                         routes_pathname_prefix=OPLSDashboard.prefix,
                         requests_pathname_prefix='/omics' + OPLSDashboard.prefix,
                         external_stylesheets=['https://use.fontawesome.com/releases/v5.8.1/css/all.css'])
        # noinspection PyTypeChecker
        OPLSDashboard._register_dash_app(app)
        return app
