import os
import shutil
from typing import Union, List, Dict

import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table
import msgpack
import numpy as np
import pandas as pd
import plotly.io as pio
from flask_login import current_user
from plotly import graph_objs as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
from sklearn.utils.multiclass import type_of_target

import data_tools.redis as rds
from data_tools.access_wrappers.collections import get_collection_copy, get_collection


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

    def get_plot(self, queries, labels, theme, bin_collection_id, legend_style='full'):
        labels = labels or []
        print(legend_style)
        self.load_dataframes()
        if bin_collection_id is not None:
            print(bin_collection_id)
            bin_collection = get_collection(current_user, bin_collection_id)
            x_mins = bin_collection.get_dataset('x_min').ravel().tolist()
            x_maxes = bin_collection.get_dataset('x_max').ravel().tolist()
            colors = [DEFAULT_PLOTLY_COLORS[i % 2] for i in range(len(x_mins))]
            shapes = [
                go.layout.Shape(
                    type='rect',
                    xref='x',
                    yref='paper',
                    x0=x_min,
                    y0=0,
                    x1=x_max,
                    y1=1,
                    fillcolor=color,
                    opacity=0.2,
                    layer='below',
                    line_width=0
                )
                for x_min, x_max, color in zip(x_mins, x_maxes, colors)
            ]
        else:
            shapes = []

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
            },
            shapes=shapes
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

        if legend_style == 'full' or legend_style == 'groups':
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

        if legend_style == 'full':
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
                text = '<br>'.join([f'{label}=={self._label_df.loc[i][label]}' for label in self._label_df.columns])
                if len(labels):
                    name = f"({', '.join([f'{self._label_df.loc[i][label]}' for label in labels])})"
                else:
                    name = f'({i})'
                figure.add_trace(
                    go.Scatter(
                        x=x,
                        y=row,
                        text=text,
                        name=name,
                        mode='lines',
                        marker={'color': color},
                        showlegend=(legend_style == 'full')
                    )
                )

        if legend_style == 'none':
            figure.update_layout(showlegend=False)

        return figure

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

    def get_summary(self, queries, labels, x_min, x_max, theme):
        labels = labels or []
        self.load_dataframes()
        in_range_columns = [column for column in self._numeric_df.columns if x_min <= float(column) <= x_max]
        # find sum of points in range
        # average and median sum
        results_dfs = []
        label_column = f'({", ".join(labels)})'
        for query in queries:
            results_df = pd.DataFrame()
            sub_label_df = self._label_df.query(query)
            sub_numeric_df = self._numeric_df.loc[sub_label_df.index]
            sums = sub_numeric_df[in_range_columns].sum(axis=1)
            results_df[label_column] = sub_label_df.apply(
                lambda row: f'({",".join([str(row[label]) for label in labels])})', axis=1)
            results_df['Sum'] = sums
            summary_df = pd.DataFrame()
            summary_df[label_column] = [f'Average({query})', f'Median({query})']
            summary_df['Sum'] = [sums.mean(), sums.median()]
            results_df = summary_df.append(results_df)
            results_dfs.append(results_df)
        style_header = {'backgroundColor': '#303030'} if theme == 'plotly_dark' else {}
        style_cell = {'backgroundColor': '#444444'} if theme == 'plotly_dark' else {}

        return [item for pair in [
            (html.H5(query),
             dash_table.DataTable(columns=[{'name': val, 'id': val} for val in df.columns],
                                  data=df.to_dict('rows'),
                                  style_header=style_header,
                                  style_cell=style_cell,
                                  style_data_conditional=[
                                      {
                                          'if': {'row_index': 0},
                                          'fontStyle': 'italic'
                                      },
                                      {
                                          'if': {'row_index': 1},
                                          'fontStyle': 'italic'
                                      }
                                  ]),
             html.Br()
             )
            for query, df in zip(queries, results_dfs)
        ] for item in pair]

    def save_figure(self, figure, file_format):
        pio.orca.config.use_xvfb = True
        root_dir = os.path.dirname(self._dataframe_filename)
        basename = f'{",".join([str(col_id) for col_id in self._loaded_collection_ids])}.{file_format}'
        filename = os.path.join(root_dir, basename)
        pio.write_image(figure, filename)
        return filename
