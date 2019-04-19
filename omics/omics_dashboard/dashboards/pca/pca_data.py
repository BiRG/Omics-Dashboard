import os
import shutil
import time as tm
from typing import List, Dict, Any, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import h5py
import msgpack
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from flask_login import current_user
from sklearn.decomposition import PCA

import data_tools.redis as rds
from data_tools.access_wrappers.collections import get_collection_copy


def get_plot_data() -> Dict[str, List[Dict[str, Any]]]:
    try:
        plot_data = msgpack.loads(rds.get_value('pca_plot_data'), raw=False)
    except Exception as e:
        plot_data = None
    if plot_data is None:
        plot_data = {
            'score_plots': [],
            'loading_plots': [],
            'variance_plots': [],
            'cumulative_variance_plots': []
        }
    # warning: we don't validate any of this
    return plot_data


def set_plot_data(plot_data: Dict[str, List[Dict[str, Any]]]) -> None:
    rds.set_value('pca_plot_data', msgpack.dumps(plot_data))


def clear_plot_data():
    rds.delete_value('pca_plot_data')


class PCAData:
    def __init__(self, load_data=False):
        # any of these can be None
        self._label_df = None
        self._processed_label_df = None
        self._numeric_df = None
        self._loadings = None
        self._scores = None
        self._explained_variance_ratio = None
        self._x = None
        self._loaded_collection_ids = []
        self._dataframe_filename = None
        self._results_filename = None
        self.load_file_info()
        if load_data:
            try:
                self.load_dataframes()
            except Exception:
                self._label_df = self._processed_label_df = self._numeric_df = None
            try:
                self.load_results()
            except Exception:
                self._loadings = self._scores = self._explained_variance_ratio = self._x = None

    def load_file_info(self):
        data_frame_filename = rds.get_value('pca_dataframe_filename')
        self._dataframe_filename = data_frame_filename.decode('utf-8') if data_frame_filename is not None else None
        results_filename = rds.get_value('pca_results_filename')
        self._results_filename = results_filename.decode('utf-8') if results_filename is not None else None
        try:
            self._loaded_collection_ids = msgpack.loads(rds.get_value('pca_loaded_collection_ids'))
        except TypeError:
            self._loaded_collection_ids = []

    def set_file_info(self):
        rds.set_value('pca_dataframe_filename', self._dataframe_filename.encode('utf-8'))
        rds.set_value('pca_results_filename', self._results_filename.encode('utf-8'))
        rds.set_value('pca_loaded_collection_ids', msgpack.dumps(self._loaded_collection_ids))

    def load_dataframes(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._processed_label_df = pd.read_hdf(self._dataframe_filename, 'processed_label_df')
        self._numeric_df = pd.read_hdf(self._dataframe_filename, 'numeric_df')

    def save_dataframes(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._processed_label_df.to_hdf(self._dataframe_filename, 'processed_label_df', mode='a')
        self._numeric_df.to_hdf(self._dataframe_filename, 'numeric_df', mode='a')

    def load_labels(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._processed_label_df = pd.read_hdf(self._dataframe_filename, 'processed_label_df')

    def save_labels(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._processed_label_df.to_hdf(self._dataframe_filename, 'processed_label_df', mode='a')

    def load_results(self):
        with h5py.File(self._results_filename, 'r') as file:
            self._x = np.array(file['x'])
            self._loadings = np.array(file['loadings'])
            self._scores = np.array(file['scores'])
            self._explained_variance_ratio = np.array(file['explained_variance_ratio'])
        self.load_labels()

    def save_results(self):
        with h5py.File(self._results_filename, 'w') as file:  # always create new because dimensions might change
            file['loadings'] = self._loadings
            file['scores'] = self._scores
            file['explained_variance_ratio'] = self._explained_variance_ratio
            file['x'] = self._x

    def load_data(self):
        self.load_results()
        self.load_dataframes()

    def set_file_metadata(self, attrs):
        """
        Use to set things like description, name, parameters
        :param attrs:
        :return:
        """
        with h5py.File(self._results_filename, 'r+') as file:
            for key, value in attrs.items():
                file.attrs[key] = value

    @property
    def labels(self):
        self.load_labels()
        return [val for val in self._label_df.columns] if self._label_df is not None else []

    @property
    def unique_vals(self):
        self.load_labels()
        return {label: self._label_df[label].unique() for label in self._label_df.columns}

    @property
    def results_exist(self):
        try:
            self.load_results()
            return True
        except:
            return False

    def get_collections(self, collection_ids: List[int]):
        data_dir = os.path.dirname(self._dataframe_filename) if self._dataframe_filename is not None else None
        if data_dir is not None:
            shutil.rmtree(data_dir)
        clear_plot_data()
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
            del x
            del y
            data_dir = os.path.dirname(collection.filename)
            self._results_filename = os.path.join(data_dir, 'results.h5')
            self._dataframe_filename = os.path.join(data_dir, 'dataframes.h5')
            self._loaded_collection_ids = collection_ids
            self._label_df = collection.get_dataframe(include_only_labels=True)
            self._numeric_df = collection.get_dataframe(numeric_columns=True, include_labels=False)
            self._numeric_df.to_csv('/tmp/spam.csv')
            self._processed_label_df = pd.DataFrame()
            os.remove(collection.filename)
            self.set_file_info()
            self.save_dataframes()

    def perform_pca(self,
                    filter_by: str = None,
                    ignore_by: str = None,
                    scale_by: str = None,
                    pair_on: List[str] = None,
                    pair_with: str = None) -> (str, str, str):
        data_load_start = tm.time()
        self.load_dataframes()
        label_df = self._label_df
        numeric_df = self._numeric_df
        self._x = np.array([float(i) for i in numeric_df.columns])
        data_load_end = tm.time()

        if scale_by:
            means = numeric_df.loc[label_df.query(scale_by).index].mean()
            std_devs = numeric_df.loc[label_df.query(scale_by).index].std().apply(lambda x: x if x else 1.0)
        else:
            means = numeric_df.mean()
            std_devs = numeric_df.std().apply(lambda x: x if x else 1.0)

        if filter_by:
            print(filter_by)
            label_df = label_df.query(filter_by)
            print(label_df.index)
            print(numeric_df.index)
            numeric_df = numeric_df.loc[label_df.index]

        if ignore_by:
            label_df = label_df.query(ignore_by)
            numeric_df = numeric_df.loc[label_df.index]

        numeric_df = numeric_df.sub(means, axis=1).divide(std_devs,
                                                          axis=1)  # do scaling before pairing, after everything else

        warnings = []
        message_color = 'success'
        if pair_on and pair_with:
            for vals, idx, in label_df.groupby(pair_on).groups.items():
                # find the pair conditions in the sub dataframe
                try:
                    target_rows = label_df.loc[idx].query(pair_with)
                    numeric_df.loc[idx].sub(target_rows.mean(), axis=1)
                except KeyError:
                    target_rows = []
                if not len(target_rows):
                    warnings.append(f'No records matching {pair_with} for {pair_on}=={vals}! Data not subtracted!')
                    message_color = 'warning'

        metadata = {
            'filter_by': filter_by or '',
            'ignore_by': ignore_by or '',
            'scale_by': scale_by or '',
            'pair_on': ','.join(pair_on) if pair_on else '',
            'pair_with': pair_with or ''
        }
        name = f'PCA'
        if len(self._loaded_collection_ids) > 1:
            name += ' on collections ' + ','.join(str(collection_id) for collection_id in self._loaded_collection_ids)
        else:
            name += ' on collection ' + str(self._loaded_collection_ids[0])
        description = name
        if scale_by:
            description += f' scaled by {scale_by}'
        if filter_by:
            description += f' including {filter_by}'
        if ignore_by:
            description += f' ignoring {ignore_by}'
        if pair_on and pair_with:
            description += f' paired on {pair_on} against {pair_with}'
        metadata['name'] = name
        metadata['description'] = description

        self._processed_label_df = label_df
        numeric_df = numeric_df.dropna(axis=1)
        start_time = tm.time()
        pca = PCA()
        self._scores = pca.fit_transform(numeric_df)
        end_time = tm.time()
        self._loadings = pca.components_
        self._explained_variance_ratio = pca.explained_variance_ratio_
        self.save_dataframes()
        self.save_results()
        self.set_file_metadata(metadata)
        save_end_time = tm.time()

        if len(warnings):
            message_children = [html.Strong('Warning:'), html.Br()]
            for warning in warnings:
                message_children.append(warning)
                message_children.append(html.Br())
        else:
            message_children = []
        message_children = message_children + [
            html.Strong(f'Performed PCA in {(end_time-data_load_start):.3f} s.'),
            html.Br(),
            f'Loaded data in {(data_load_end-data_load_start):.3f} s.',
            html.Br(),
            f'Processed data in {(start_time-data_load_end):.3f} s.',
            html.Br(),
            f'Fitted PCA model in {(end_time - start_time):.3f} s.',
            html.Br(),
            f'Cached data in {(save_end_time - end_time):.3f} s.'
        ]
        return html.P(message_children), metadata['name'], message_color

    def _davies_bouldin(self, category_label, label_values) -> pd.DataFrame:
        # this is calculated as part of plotting scores.
        self.load_labels()
        self.load_results()
        scores_df = pd.DataFrame(data=self._scores,
                                 index=self._processed_label_df.index,
                                 columns=[f'PC {i+1}' for i in range(0, len(self._scores))])
        label_df = pd.DataFrame(data=label_values, columns=[category_label], index=self._processed_label_df.index)

        scores_df.reset_index()
        label_df.reset_index()
        categories = pd.unique(label_df[category_label].dropna())

        def _calculate_intercluster_distance():
            distances = {}
            for cat1 in categories:
                distances[cat1] = {}
                for cat2 in categories:
                    centroid1 = scores_df[label_df[category_label] == cat1].mean()
                    centroid2 = scores_df[label_df[category_label] == cat2].mean()
                    distances[cat1][cat2] = np.linalg.norm(centroid1 - centroid2)
            return distances

        def _calculate_intracluster_distance():
            distances = {}
            for category in categories:
                centroid = scores_df[label_df[category_label] == category].mean()
                point_distances = scores_df[label_df[category_label] == category].apply(
                    lambda row: np.linalg.norm(row - centroid), axis=1)
                distances[category] = pow(sum(point_distances), 0.5) / len(point_distances)
            return distances

        def _calculate_r(within, between):
            r_val = {}
            for cat1 in within.keys():
                r_val[cat1] = {}
                for cat2 in within.keys():
                    r_val[cat1][cat2] = (within[cat1] + within[cat2]) / between[cat1][cat2] \
                        if between[cat1][cat2] else None
            return r_val

        between_distances = _calculate_intercluster_distance()
        within_distances = _calculate_intracluster_distance()
        r = _calculate_r(within_distances, between_distances)
        d = {cat1: max([r[cat1][cat2] for cat2 in categories if cat1 != cat2]) for cat1 in categories}
        db_ind = {cat: d[cat] / len(categories) for cat in categories}

        results = pd.DataFrame(index=[f'{category_label}={cat}' for cat in categories])
        results['S'] = [within_distances[cat] for cat in categories]
        for cat1 in categories:
            results[f'M_{cat1}'] = [between_distances[cat1][cat2] for cat2 in categories]
        for cat1 in categories:
            results[f'R_{cat1}'] = [r[cat1][cat2] for cat2 in categories]
        results['DB'] = [db_ind[cat] for cat in categories]
        return results

    def _get_score_plot(self, ordinate, abscissa, color_by_labels) -> (
    dcc.Graph, Union[dash_table.DataTable, html.Div]):
        color_by_labels = color_by_labels or []
        color_label = ','.join(color_by_labels) if color_by_labels else 'All'
        label_df = self._processed_label_df.reset_index()
        color_labels = label_df[color_by_labels].apply(lambda x: ','.join(x.apply(str)),
                                                       axis=1) if color_by_labels else pd.Series(
            ['All' for _ in range(0, len(label_df))])
        color_names = list(color_labels.unique())
        color_indices = [label_df.index[color_labels == color_name] for color_name in color_names]
        if len(color_names) > 1:
            db_df = self._davies_bouldin(color_label, color_labels)
            db_df = db_df.applymap('{:.5f}'.format)
            db_df[color_label] = db_df.index
            columns = [color_label, 'DB'] + [column for column in db_df.columns if column not in {color_label, 'DB'}]
            db_df = db_df[columns]
            table = dash_table.DataTable(columns=[{'name': val, 'id': val} for val in db_df.columns],
                                         data=db_df.to_dict('rows'))
        else:
            table = html.Div()
        return dcc.Graph(figure={
            'data': [
                        go.Scatter(  # dummy series to use as stand-in for legend title
                            x=[0],
                            y=[0],
                            name=color_label,
                            mode='markers',
                            marker={
                                'opacity': 0
                            }
                        )
                    ] + [
                        go.Scatter(
                            x=self._scores[inds, abscissa],
                            y=self._scores[inds, ordinate],
                            text=['<br>'.join([f'{label}: {label_df[label][ind]}' for label in
                                               label_df.columns]) for ind in inds],
                            name=name,
                            mode='markers',
                            marker={
                                'size': 15,
                                'opacity': 0.5,
                                'line': {'width': 0.5, 'color': 'white'}
                            }
                        ) for inds, name in zip(color_indices, color_names)
                    ],
            'layout': go.Layout(
                height=700,
                xaxis={
                    'title': f'PC{abscissa + 1}'
                },
                yaxis={
                    'title': f'PC{ordinate + 1}'
                }
            )
        }), table

    def _get_loading_plot(self, loadings) -> dcc.Graph:
        return dcc.Graph(figure={
            'data': [
                go.Scatter(
                    x=self._x,
                    y=self._loadings[ind, :],
                    text=f'PC {ind+1}<br>{100*self._explained_variance_ratio[ind]:.3f} % variance',
                    name=f'PC {ind+1}',
                    mode='lines'
                ) for ind in loadings
            ],
            'layout': go.Layout(
                xaxis={
                    'title': 'Chemical Shift (ppm)',
                    'autorange': 'reversed'
                },
                yaxis={
                    'title': 'PC Loading'
                }
            )
        })

    def _get_variance_plot(self, scale_y=False, indices=None) -> dcc.Graph:
        all_indices = [i for i in range(0, len(self._explained_variance_ratio))]
        indices = list(set(all_indices).intersection(set(indices)))
        xaxis = {'title': 'Principal Component'}
        yaxis = {'title': '% Variance Explained'}
        if not scale_y:
            yaxis['range'] = [0, 100]
        return dcc.Graph(figure={
            'data': [
                go.Bar(
                    x=[f'PC {ind+1}'],
                    y=[100 * self._explained_variance_ratio[ind]]
                ) for ind in indices
            ],
            'layout': go.Layout(
                showlegend=False,
                xaxis=xaxis,
                yaxis=yaxis
            )
        })

    def _get_cumulative_variance_plot(self, threshold) -> dcc.Graph:
        cumulative = 100 * np.cumsum(self._explained_variance_ratio)
        first_index = np.argwhere(cumulative > threshold).flatten()[0]
        line_x = first_index + 1
        y_ticks = sorted([i for i in range(0, 110, 10)] + [threshold])
        x_ticks = sorted([i for i in range(0, len(self._explained_variance_ratio), 5)] + [line_x])
        return dcc.Graph(figure={
            'data': [
                go.Scatter(
                    x=[x + 1 for x in range(0, len(self._explained_variance_ratio))],
                    y=cumulative.tolist()
                )
            ],
            'layout': go.Layout(
                xaxis={'title': 'Number of Principal Components', 'tickvals': x_ticks},
                yaxis={'title': '% Variance Explained', 'tickvals': y_ticks},
                shapes=[
                    {
                        'type': 'line',
                        'x0': line_x,
                        'x1': line_x,
                        'y0': 0,
                        'y1': 1,
                        'yref': 'paper',
                        'opacity': 0.7,
                        'line': {
                            'color': 'gray',
                            'width': 2,
                            'dash': 'dash'
                        }
                    },
                    {
                        'type': 'line',
                        'x0': 0,
                        'x1': 1,
                        'xref': 'paper',
                        'y0': threshold,
                        'y1': threshold,
                        'opacity': 0.7,
                        'line': {
                            'color': 'gray',
                            'width': 2,
                            'dash': 'dash'
                        }
                    }
                ]
            )
        })

    def get_plots(self,
                  score_plot_data,
                  loading_plot_data,
                  variance_plot_data,
                  cumulative_variance_plot_data) -> (List[Union[dcc.Graph, dash_table.DataTable]],
                                                     List[dcc.Graph],
                                                     List[dcc.Graph],
                                                     List[dcc.Graph]):
        self.load_labels()
        self.load_results()
        score_plots = [self._get_score_plot(plot['ordinate'], plot['abscissa'], plot['color_by'])
                       for plot in score_plot_data]
        return (
            [
                item for pair in score_plots for item in pair
            ],
            [
                self._get_loading_plot(plot['indices']) for plot in loading_plot_data
            ],
            [
                self._get_variance_plot(plot['scale_y'], plot['indices']) for plot in variance_plot_data
            ],
            [
                self._get_cumulative_variance_plot(plot['threshold']) for plot in cumulative_variance_plot_data
            ]
        )

    def get_collection_badges(self) -> List[html.Span]:
        return [
            html.Span([dbc.Badge(f'{collection_id}', className='badge-pill', color='primary'), ' '])
            for collection_id in self._loaded_collection_ids
        ] if self._loaded_collection_ids else [html.Span([dbc.Badge('None', className='badge-pill')])]

    def get_collection_load_info(self) -> str:
        return f'Collections loaded in {os.path.dirname(self._dataframe_filename)}'

    def get_label_data(self) -> List[Dict[str, str]]:
        self.load_dataframes()
        return [{'label': label, 'value': label} for label in self.labels]

    def get_pc_options(self) -> List[Dict[str, Union[str, int]]]:
        self.load_results()
        return [{'label': f'PC {i+1}', 'value': i} for i in range(0, len(self._explained_variance_ratio))]


