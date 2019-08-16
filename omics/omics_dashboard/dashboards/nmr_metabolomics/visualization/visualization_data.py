import os
import shutil
from typing import Union, List, Dict

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import msgpack
import numpy as np
import pandas as pd
from flask_login import current_user
from plotly import graph_objs as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
from sklearn.utils.multiclass import type_of_target

import data_tools.redis as rds
from data_tools.access_wrappers.collections import get_collection_copy


class VisualizationData:
    _redis_prefix = 'viz'
    _empty_plot_data = {}

    def __init__(self, load_data=False):
        self._label_df = None
        self._numeric_df = None
        self._dataframe_filename = None
        self._loaded_collection_ids = []
        self.load_file_info()
        if load_data:
            try:
                self.load_dataframes()
            except Exception:
                self._label_df = self._processed_label_df = self._numeric_df = None

    @property
    def labels(self):
        self.load_labels()
        return [val for val in self._label_df.columns] if self._label_df is not None else []

    @property
    def unique_vals(self):
        self.load_labels()
        return {label: self._label_df[label].unique() for label in self._label_df.columns}

    def load_file_info(self):
        data_frame_filename = rds.get_value(f'{self._redis_prefix}_dataframe_filename')
        self._dataframe_filename = data_frame_filename.decode('utf-8') if data_frame_filename is not None else None
        if not self._dataframe_filename or not os.path.isfile(self._dataframe_filename):
            rds.delete_value(f'{self._redis_prefix}_dataframe_filename')
            self._dataframe_filename = None
        try:
            self._loaded_collection_ids = msgpack.loads(rds.get_value(f'{self._redis_prefix}_loaded_collection_ids'))
        except TypeError:
            self._loaded_collection_ids = []

    def set_file_info(self):
        rds.set_value(f'{self._redis_prefix}_dataframe_filename', self._dataframe_filename.encode('utf-8'))
        rds.set_value(f'{self._redis_prefix}_loaded_collection_ids', msgpack.dumps(self._loaded_collection_ids))

    def load_dataframes(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._numeric_df = pd.read_hdf(self._dataframe_filename, 'numeric_df')

    def save_dataframes(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._numeric_df.to_hdf(self._dataframe_filename, 'numeric_df', mode='a')

    def load_labels(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')

    def save_labels(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')

    def get_collections(self, collection_ids: Union[List[int], int]):
        data_dir = os.path.dirname(self._dataframe_filename) if self._dataframe_filename is not None else None
        if data_dir is not None:
            shutil.rmtree(data_dir)
        if not isinstance(collection_ids, list):
            collection_ids = [collection_ids]
        collections = [get_collection_copy(current_user, collection_id) for collection_id in collection_ids]
        if len(collections) > 1:
            collections[0].merge(collections[1:])
            collection = collections[0]
        elif len(collections) == 1:
            collection = collections[0]
        else:
            collection = None
        if collection is not None:
            x = collection.get_dataset('x')
            inds = np.argsort([float(val) for val in x.flatten()])
            y = collection.get_dataset('Y')
            collection.set_dataset('x', x[:, inds])
            collection.set_dataset('Y', y[:, inds])
            del y
            del x
            data_dir = os.path.dirname(collection.filename)
            self._dataframe_filename = os.path.join(data_dir, 'dataframes.h5')
            self._loaded_collection_ids = collection_ids
            self._label_df = collection.get_dataframe(include_only_labels=True)
            self._numeric_df = collection.get_dataframe(numeric_columns=True, include_labels=False)
            os.remove(collection.filename)
            self.set_file_info()
            self.save_dataframes()

    def get_collection_badges(self) -> List[html.Span]:
        return [
            html.Span([dbc.Badge(f'{collection_id}', className='badge-pill', color='primary'), ' '])
            for collection_id in self._loaded_collection_ids
        ] if self._loaded_collection_ids else [html.Span([dbc.Badge('None', className='badge-pill')])]

    def get_collection_load_info(self) -> str:
        return f'Collections loaded in {os.path.dirname(self._dataframe_filename)}'

    def get_plot(self, queries, labels, theme):
        labels = labels or []
        self.load_dataframes()
        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }
        layout = go.Layout(
            height=700,
            font={'size': 16},
            template=theme,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis={
                'title': 'Chemical Shift (ppm)',
                'autorange': 'reversed',
                **axis_line_style
            },
            yaxis={
                'title': 'Intensity',
                **axis_line_style
            }
        )
        color_indices = [self._label_df.query(query).index for query in queries]
        if len(color_indices) > len(DEFAULT_PLOTLY_COLORS):  # repeat default color list
            colors = []
            while len(colors) < len(color_indices):
                colors += DEFAULT_PLOTLY_COLORS
        else:
            colors = DEFAULT_PLOTLY_COLORS
        colors = colors[:len(color_indices)]
        x = self._numeric_df.columns.values.astype(float)
        figure = go.Figure(layout=layout)

        for query, color in zip(queries, colors):
            figure.add_trace(
                go.Scatter(  # dummy series to label colors
                    x=[0],
                    y=[0],
                    name=query,
                    mode='lines',
                    marker={'color': color}
                )
            )

        figure.add_trace(
            go.Scatter(  # dummy series to provide space between color key and "heading"
                x=[0],
                y=[0],
                name='',
                mode='markers',
                marker={
                    'opacity': 0,
                    'size': 0,
                    'color': 'rgba(0,0,0,0)'
                }
            )
        )

        figure.add_trace(
            go.Scatter(  # dummy series to use as stand-in for legend title
                x=[0],
                y=[0],
                name=f"({', '.join(labels)})" if len(labels) else 'Spectrum #',
                mode='markers',
                marker={
                    'opacity': 0,
                    'size': 0,
                    'color': 'rgba(0,0,0,0)'
                }
            )
        )

        for query, color in zip(queries, colors):
            y_values = self._numeric_df.loc[self._label_df.query(query).index]
            for i, row in y_values.iterrows():
                if len(labels):
                    name = f"({', '.join([f'{self._label_df.loc[i][label]}' for label in labels])})"
                    text = ', '.join([f'{label}=={self._label_df.loc[i][label]}' for label in labels])
                else:
                    name = f'({i})'
                    text = f'Spectrum #{i}'
                figure.add_trace(
                    go.Scatter(
                        x=x,
                        y=row,
                        text=text,
                        name=name,
                        mode='lines',
                        marker={'color': color}
                    )
                )
        return dcc.Graph(figure=figure)

    def get_label_data(self, with_type=False) -> List[Dict[str, str]]:
        self.load_dataframes()
        types = {
            label: f' ({type_of_target(self._label_df[label])})'
            for label in self.labels
        } if with_type else {
            label: ''
            for label in self.labels
        }
        return [{'label': f'{label}{types[label]}', 'value': label} for label in self.labels]
