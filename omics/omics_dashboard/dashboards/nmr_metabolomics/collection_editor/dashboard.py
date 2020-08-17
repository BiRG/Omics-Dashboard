import traceback

from flask import url_for

from config.config import PATH_PREFIX
from dashboards import Dashboard
import itertools
import dash_bootstrap_components as dbc
import dash_html_components as html

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

from dashboards.dashboard import StyledDash
from dashboards.nmr_metabolomics.collection_editor.layouts import get_layout
from dashboards.nmr_metabolomics.collection_editor.model import CollectionEditorModel


class CollectionEditorDashboard(Dashboard):
    name = 'Merge/Join/Filter'
    prefix = '/dashboards/collection_editor/'
    description = 'Join, concatenate, and filter collections.'
    id = 'edit'

    @staticmethod
    def _on_label_key_select(label_keys, op='=='):
        if not label_keys or None in label_keys:
            raise PreventUpdate('Callback triggered without action!')
        label_keys = sorted(label_keys)
        editor_data = CollectionEditorModel()
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
            [Output('filter-by-value', 'options')],
            [Input('filter-by', 'value')]
        )
        def update_filter_by_options(label_keys):
            return CollectionEditorDashboard._on_label_key_select(label_keys)

        @app.callback(
            [Output('ignore-by-value', 'options')],
            [Input('ignore-by', 'value')]
        )
        def update_ignore_by_options(label_keys):
            return CollectionEditorDashboard._on_label_key_select(label_keys, op='!=')

        @app.callback(
            [Output('filter-by', 'options'),
             Output('ignore-by', 'options'),
             Output('join-on', 'options'),
             Output('join-on', 'disabled'),
             Output('positive-collection', 'disabled'),
             Output('positive-collection', 'options'),
             Output('name-input', 'value'),
             Output('analysis-select', 'value'),
             Output('loaded-collections', 'children'),
             Output('collections-label', 'children')],
            [Input('get-collection', 'n_clicks')],
            [State('collection-id', 'value')],
        )
        def get_collections(n_clicks, collection_id):
            if not collection_id or not n_clicks:
                raise PreventUpdate('Callback triggered without value')
            editor_data = CollectionEditorModel()
            editor_data.get_collections(collection_id)
            join_disabled = editor_data.collection_count != 2
            label_data = editor_data.get_label_data()
            name = editor_data.proposed_name(None, None)
            if not join_disabled:
                collection_id_options = [{'label': f'collection_id={i}', 'value': i}
                                         for i in editor_data.loaded_collection_ids]
            else:
                collection_id_options = []
            return (
                label_data,
                label_data,
                label_data,
                join_disabled,
                join_disabled,
                collection_id_options,
                name,
                editor_data.analysis_ids,
                editor_data.get_collection_badges(),
                editor_data.get_collection_load_info()
            )

        @app.callback([Output('name-input-wrapper', 'children')],
                      [Input('filter-by-value', 'value')],
                      [State('join-on', 'value')])
        def filter_by_changed(filter_by, join_on):
            editor_data = CollectionEditorModel()
            filter_by_query = ' | '.join([f'({condition})' for condition in filter_by])
            name = editor_data.proposed_name(filter_by_query, join_on)
            return [dbc.Input(value=name, id='name-input')]

        @app.callback([Output('name-input-wrapper-wrapper', 'children')],
                      [Input('join-on', 'value')],
                      [State('filter-by-value', 'value')])
        def filter_by_changed(join_on, filter_by):
            editor_data = CollectionEditorModel()
            filter_by_query = ' | '.join([f'({condition})' for condition in filter_by])
            name = editor_data.proposed_name(filter_by_query, join_on)
            return [
                html.Div(
                    html.Div(
                        dbc.Input(value=name, id='name-input'), id='name-input-wrapper'
                    ), id='name-input-wrapper-wrapper'
                )
            ]

        @app.callback([Output('post-message', 'children')],
                      [Input('post-button', 'n_clicks')],
                      [State('filter-by-value', 'value'),
                       State('ignore-by-value', 'value'),
                       State('join-on', 'value'),
                       State('positive-collection', 'value'),
                       State('name-input', 'value'),
                       State('analysis-select', 'value')])
        def post_collection(n_clicks, filter_by, ignore_by, join_on, left_collection_id, name, analysis_ids):
            CollectionEditorDashboard.check_clicks(n_clicks)
            filter_by_query = ' | '.join(filter_by) if filter_by is not None else None
            ignore_by_query = ' & '.join(ignore_by) if ignore_by is not None else None
            try:
                editor_data = CollectionEditorModel(True)
                new_collection = editor_data.post_collection(filter_by_query, ignore_by_query, join_on,
                                                             left_collection_id, name, analysis_ids)
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

    @staticmethod
    def _register_layout(app):
        app.layout = get_layout

    @staticmethod
    def _register_dash_app(app):
        app.title = CollectionEditorDashboard.name
        CollectionEditorDashboard._register_layout(app)
        CollectionEditorDashboard._register_callbacks(app)

    @staticmethod
    def create_dash_app(server):
        # no users are logged in when this is created so we can't set light/dark theme preference
        app = StyledDash(__name__,
                         server=server,
                         routes_pathname_prefix=CollectionEditorDashboard.prefix,
                         requests_pathname_prefix=PATH_PREFIX + CollectionEditorDashboard.prefix)
        # noinspection PyTypeChecker
        CollectionEditorDashboard._register_dash_app(app)
        return app
