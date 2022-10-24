import traceback

from flask import url_for

from config.config import PATH_PREFIX
from dashboards import Dashboard
import itertools
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

from dashboards.dashboard import StyledDash, get_plot_theme
from dashboards.nmr_metabolomics.processing.layouts import get_layout
from dashboards.nmr_metabolomics.processing.model import CollectionProcessingModel


class CollectionProcessingDashboard(Dashboard):
    name = 'Fix Spectra'
    prefix = '/dashboards/fix_spectra/'
    description = 'Collection processing.'
    id = 'proc'

    def __init__(self):
        model = CollectionProcessingModel()

    @staticmethod
    def _on_label_key_select(label_keys, op='=='):
        if not label_keys or None in label_keys:
            raise PreventUpdate('Callback triggered without action!')
        label_keys = sorted(label_keys)
        editor_data = CollectionProcessingModel(True)
        unique_values = [editor_data.unique_vals[val] for val in label_keys]
        option_pairs = list(itertools.product(*unique_values))
        queries = [' & '.join([f'{key}{op}"{value}"' for key, value in zip(label_keys, option_pair)])
                   for option_pair in option_pairs]
        query_labels = [','.join([f'{key}={value}' for key, value in zip(label_keys, option_pair)])
                        for option_pair in option_pairs]
        return [[{'label': query_label, 'value': query} for query_label, query in zip(query_labels, queries)]]

    @staticmethod
    def _register_callbacks(app):
        @app.callback(
            [Output('loaded-collections', 'children'),
             Output('collections-label', 'children'),
             Output('spectrum-index', 'value'),
             Output('spectrum-index', 'max'),
             Output('region-min', 'min'),
             Output('region-min', 'max'),
             Output('region-max', 'min'),
             Output('region-max', 'max'),
             Output('pqn-ref-label', 'options'),
             Output('hist-ref-label', 'options')],
            [Input('get-collection', 'n_clicks')],
            [State('collection-id', 'value'),
             State('normalization-apply-button', 'n_clicks'),
             State('baseline-apply-button', 'n_clicks'),
             State('region-apply-button', 'n_clicks'),
             State('finalize-button', 'n_clicks')],
        )
        def get_collections(n_clicks, value,
                            normalize_n_clicks,
                            baseline_n_clicks,
                            region_n_clicks,
                            finalize_n_clicks):
            CollectionProcessingDashboard.check_clicks(n_clicks)
            if not value:
                raise PreventUpdate('Nothing to load.')
            model = CollectionProcessingModel()
            model.get_collections(value)
            x_min, x_max = model.x_range
            model.normalize_n_clicks = normalize_n_clicks
            model.finalize_n_clicks = finalize_n_clicks
            model.region_n_clicks = region_n_clicks
            model.baseline_n_clicks = baseline_n_clicks
            model.processing_log = None
            label_data = model.get_label_data()

            return (
                model.get_collection_badges(),
                model.get_collection_load_info(),
                0,
                model.spectrum_count - 1,
                x_min,
                x_max,
                x_min,
                x_max,
                label_data,
                label_data
            )

        @app.callback(
            [Output('sum-normalization-form', 'style'),
             Output('region-normalization-form', 'style'),
             Output('hist-normalization-form', 'style'),
             Output('pqn-normalization-form', 'style'),
             Output('label-normalization-form', 'style')],
            [Input('normalization-method', 'value')]
        )
        def normalize_method_switched(value):
            if value == 'sum':
                return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
            elif value == 'region':
                return {'display': 'none'}, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
            elif value == 'label':
                return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'block'}
            elif value == 'histogram':
                return {'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}
            elif value == 'probability_quotient':
                return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'none'}
            else:
                return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}

        @app.callback(
            [Output('preview-graph', 'figure'),
             Output('preview-graph', 'config'),
             Output('processing-log', 'children')],
            [Input('spectrum-index', 'value'),
             Input('region-min', 'value'),
             Input('region-max', 'value'),
             Input('range-checklist', 'value')]
        )
        def update_plot(spectrum_index, region_min, region_max, show_box):
            show_box = 'show_range_box' in show_box
            spectrum_index = spectrum_index if spectrum_index is not None else 0
            model = CollectionProcessingModel(True)
            theme = get_plot_theme()
            return [model.get_plot(spectrum_index, show_box, region_min, region_max, theme),
                    {'editable': show_box},
                    [html.Strong('Processing log: '), f'{model.processing_log}']]

        @app.callback(
            [Output('preview-graph-wrapper', 'children'),
             Output('processing-log-wrapper', 'children')],
            [Input('finalize-button', 'n_clicks'),
             Input('normalization-apply-button', 'n_clicks'),
             Input('baseline-apply-button', 'n_clicks'),
             Input('region-apply-button', 'n_clicks')],
            [State('normalization-method', 'value'),
             State('norm-sum', 'value'),
             State('peak-intensity', 'value'),
             State('norm-label', 'value'),
             State('hist-ref-type', 'value'),
             State('hist-ref-query', 'value'),
             State('pqn-ref-type', 'value'),
             State('pqn-ref-query', 'value'),
             State('baseline-method', 'value'),
             State('rolling-ball-min-max', 'value'),
             State('rolling-ball-smoothing', 'value'),
             State('region-method', 'value'),
             State('spectrum-index', 'value'),
             State('region-min', 'value'),
             State('region-max', 'value'),
             State('range-checklist', 'value')]
        )
        def action_button(finalize_n_clicks, normalize_n_clicks, baseline_n_clicks, region_n_clicks,
                          normalization_method, norm_sum, region_peak_intensity, norm_label,
                          hist_ref_type, hist_ref_query, pqn_ref_type, pqn_ref_query,
                          baseline_method, rolling_ball_min_max, rolling_ball_smoothing,
                          region_method,
                          spectrum_index, region_min, region_max, show_box):
            try:
                model = CollectionProcessingModel(True)
                if not any([finalize_n_clicks, normalize_n_clicks, baseline_n_clicks, region_n_clicks]):
                    raise PreventUpdate('Callback triggered without action!')
                if normalize_n_clicks and (normalize_n_clicks != model.normalize_n_clicks):
                    print(f'normalize: ({normalize_n_clicks}, {model.normalize_n_clicks})')
                    pqn_ref_query = ' | '.join(pqn_ref_query) if pqn_ref_query and len(pqn_ref_query) else None
                    hist_ref_query = ' | '.join(hist_ref_query) if hist_ref_query and len(hist_ref_query) else None
                    model.normalize(normalization_method,
                                    norm_sum=norm_sum,
                                    region_peak_intensity=region_peak_intensity,
                                    norm_label=norm_label,
                                    region_min=region_min,
                                    region_max=region_max,
                                    hist_ref_type=hist_ref_type,
                                    hist_ref_query=hist_ref_query,
                                    pqn_ref_type=pqn_ref_type,
                                    pqn_ref_query=pqn_ref_query)
                    model.normalize_n_clicks = normalize_n_clicks
                if baseline_n_clicks and (baseline_n_clicks != model.baseline_n_clicks):
                    print(f'baseline: ({baseline_n_clicks}, {model.baseline_n_clicks})')
                    model.correct_baseline(baseline_method,
                                           rolling_ball_min_max=rolling_ball_min_max,
                                           rolling_ball_smoothing=rolling_ball_smoothing)
                    model.baseline_n_clicks = baseline_n_clicks
                if region_n_clicks and (region_n_clicks != model.region_n_clicks):
                    print(f'region: ({region_n_clicks}, {model.region_n_clicks})')
                    model.process_region(region_method, region_min, region_max)
                    model.region_n_clicks = region_n_clicks
                if finalize_n_clicks and (finalize_n_clicks != model.finalize_n_clicks):
                    print(f'finalize: ({finalize_n_clicks}, {model.finalize_n_clicks})')
                    model.finalize()
                    model.finalize_n_clicks = finalize_n_clicks

                show_box = 'show_range_box' in show_box
                theme = get_plot_theme()
                figure = model.get_plot(spectrum_index, show_box, region_min, region_max, theme)
            except Exception as e:
                print(e)
                traceback.print_exc()
                figure = None

            return [dcc.Graph(id='preview-graph', config={'editable': True}, figure=figure),
                    html.P([html.Strong('Processing log: '), f'{model.processing_log}'], id='processing-log')]

        @app.callback(
            [Output('region-min', 'value'),
             Output('region-max', 'value')],
            [Input('preview-graph', 'relayoutData')],
            [State('region-min', 'value'),
             State('region-max', 'value')]
        )
        def graph_relayout(relayout_data, region_min, region_max):
            print(relayout_data)
            if relayout_data is None:
                relayout_data = {}
            try:
                model = CollectionProcessingModel(True)
                if 'xaxis.range[0]' and 'xaxis.range[1]' in relayout_data:
                    model.x_axis_range = (relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]'])
                if 'yaxis.range[0]' and 'yaxis.range[1]' in relayout_data:
                    model.y_axis_range = (relayout_data['yaxis.range[0]'], relayout_data['yaxis.range[1]'])
                if 'shapes[0].x0' and 'shapes[0].x1' in relayout_data:
                    x0, x1 = relayout_data['shapes[0].x0'], relayout_data['shapes[0].x1']
                    return model.nearest_x(x0, x1)
                else:
                    return sorted([region_min, region_max])
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)
                return [0, 0.1]

        @app.callback([Output('post-message', 'children')],
                      [Input('post-button', 'n_clicks')],
                      [State('name-input', 'value'),
                       State('analysis-select', 'value')])
        def post_collection(n_clicks, name, analysis_ids):
            CollectionProcessingDashboard.check_clicks(n_clicks)
            try:
                editor_data = CollectionProcessingModel(True)
                new_collection = editor_data.post_collection(name, analysis_ids)
                return [
                    dbc.Alert(
                        [
                            'Posted results as ',
                            html.A(f'Collection {new_collection.id}.',
                                   href=url_for('collections.render_collection',
                                                collection_id=new_collection.id))
                        ],
                        dismissable=True, color='success')
                ]

            except Exception as e:
                return [dbc.Alert([html.P([html.Strong('Error: '), f'{e}']),
                                   html.Strong('Traceback:'),
                                   html.P(html.Pre(traceback.format_exc(), className='text-white'))],
                                  color='danger', dismissable=True)]

        @app.callback([Output('pqn-ref-query', 'options')],
                      [Input('pqn-ref-label', 'value')])
        def get_query_options(value):
            return CollectionProcessingDashboard._on_label_key_select(value)

        @app.callback([Output('hist-ref-query', 'options')],
                      [Input('hist-ref-label', 'value')])
        def get_query_options(value):
            return CollectionProcessingDashboard._on_label_key_select(value)

    @staticmethod
    def _register_layout(app):
        app.layout = get_layout

    @staticmethod
    def _register_dash_app(app):
        app.title = CollectionProcessingDashboard.name
        CollectionProcessingDashboard._register_layout(app)
        CollectionProcessingDashboard._register_callbacks(app)

    @staticmethod
    def create_dash_app(server):
        # no users are logged in when this is created so we can't set light/dark theme preference
        app = StyledDash(__name__,
                         server=server,
                         routes_pathname_prefix=CollectionProcessingDashboard.prefix,
                         requests_pathname_prefix=PATH_PREFIX + CollectionProcessingDashboard.prefix)
        # noinspection PyTypeChecker
        CollectionProcessingDashboard._register_dash_app(app)
        return app
