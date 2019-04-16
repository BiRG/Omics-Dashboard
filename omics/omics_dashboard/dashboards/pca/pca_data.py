import os
import time as tm
from typing import List, Dict, Any, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import h5py
import msgpack
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from flask_login import current_user
from sklearn.decomposition import PCA

import data_tools.redis as rds
from data_tools.access_wrappers.collections import get_collection_copy


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
        pass

    def save_dataframes(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._processed_label_df.to_hdf(self._dataframe_filename, 'processed_label_df', mode='a')
        self._numeric_df.to_hdf(self._dataframe_filename, 'numeric_df', mode='a')

    def load_results(self):
        with h5py.File(self._results_filename, 'r') as file:
            self._x = np.array(file['x'])
            self._loadings = np.array(file['loadings'])
            self._scores = np.array(file['scores'])
            self._explained_variance_ratio = np.array(file['explained_variance_ratio'])

    def save_results(self):
        with h5py.File(self._results_filename, 'w') as file:  # always create new because dimensions might change
            file['loadings'] = self._loadings
            file['scores'] = self._scores
            file['explained_variance_ratio'] = self._explained_variance_ratio
            file['x'] = self._x

    def load_data(self):
        self.load_results()
        self.load_dataframes()

    @property
    def labels(self):
        return [val for val in self._label_df.columns] if self._label_df is not None else []

    @property
    def unique_vals(self):
        return [self._label_df[label].unique() for label in self._label_df.columns]

    def get_collections(self, collection_ids: List[int]):
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
            self._processed_label_df = pd.DataFrame()
            os.remove(collection.filename)
            self.set_file_info()
            self.save_dataframes()

    def perform_pca(self, params) -> str:
        data_load_start = tm.time()
        self.load_dataframes()
        label_df = self._label_df
        numeric_df = self._numeric_df
        self._x = np.array([float(i) for i in numeric_df.columns])
        data_load_end = tm.time()
        # it is possible to scale by something that isn't in your final df
        scale_label_df = label_df
        scale_numeric_df = numeric_df
        if 'scale_by' in params:
            for pair in params['scale_by']:
                scale_label_df = scale_label_df[scale_label_df[pair[0]] == pair[1]]
                scale_numeric_df = scale_numeric_df[scale_label_df[pair[0]] == pair[1]]

        mean_start = tm.time()
        means = scale_numeric_df.mean()
        mean_end = tm.time()
        std_devs = scale_numeric_df.std().apply(lambda x: x if x != 0 else 1.0)
        std_end = tm.time()
        print(f'Calculated means in {mean_end-mean_start}, stdevs in {std_end-mean_end}')
        print(f'copying dfs took {mean_start - data_load_end}')
        for column, mean, std_dev in zip(numeric_df.columns, means, std_devs):
            numeric_df[column] = (numeric_df[column] - mean) / std_dev
        scale_end = tm.time()
        print(f'scaled in {scale_end - std_end}')
        if 'filter_by' in params:
            for pair in params['filter_by']:
                label_df = label_df[label_df[pair[0]] == pair[1]]
                numeric_df = numeric_df[label_df[pair[0]] == pair[1]]

        if 'ignore_by' in params:
            for pair in params['ignore_by']:
                label_df = label_df[label_df[pair[0]] != pair[1]]
                numeric_df = numeric_df[label_df[pair[0]] != pair[1]]

        if 'merge_by' in params:
            combined_df = pd.concat([numeric_df, label_df], axis=1)
            if params['merge_by']['method'] == 'median':
                combined_df = combined_df.groupby(params['merge_by']['labels']).median().reset_index()
            else:
                combined_df = combined_df.groupby(params['merge_by']['labels']).mean().reset_index()
            numeric_df = combined_df[numeric_df.columns]
            label_df = combined_df[list(set.intersection(set(label_df.columns), set(combined_df.columns)))]

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
        save_end_time = tm.time()
        return (
            f'Performed PCA in {(end_time - start_time):.3f} s. '
            f'Cached data in {(save_end_time - end_time):.3f} s. '
            f'Loaded data in {(data_load_end-data_load_start):.3f} s. '
            f'Processed data in {(start_time-data_load_end):.3f} s.'
        )

    def _get_score_plot(self, ordinate, abscissa, color_by_labels) -> List[dcc.Graph]:
        color_label = ','.join(color_by_labels)
        color_labels = self._processed_label_df[color_by_labels].apply(lambda x: ','.join(x.apply(str)), axis=1)
        color_names = list(color_labels.unique())
        color_indices = [self._processed_label_df.index[color_labels == color_name] for color_name in color_names]
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
                            text=['<br>'.join([f'{label}: {self._processed_label_df[label][ind]}' for label in
                                               self._processed_label_df.columns]) for ind in inds],
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
                xaxis={
                    'title': f'PC{abscissa + 1}'
                },
                yaxis={
                    'title': f'PC{ordinate + 1}'
                }
            )
        })

    def _get_loading_plot(self, loadings) -> List[dcc.Graph]:
        return dcc.Graph(figure={
            'data': [
                go.Scatter(
                    x=self._numeric_df.columns,
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

    def _get_variance_plot(self, scale_y=False, indices=None) -> List[dcc.Graph]:
        indices = [i for i in range(0, self._explained_variance_ratio)] if indices is None else indices
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
                xaxis=xaxis,
                yaxis=yaxis
            )
        })

    def get_plots(self,
                  score_plot_data,
                  loading_plot_data,
                  variance_plot_data) -> (List[dcc.Graph], List[dcc.Graph], List[dcc.Graph]):
        self.load_data()
        return (
            [
                self._get_score_plot(plot['ordinate'], plot['abscissa'], plot['color_by'])
                for plot in score_plot_data
            ],
            [
                self._get_loading_plot(plot['indices']) for plot in loading_plot_data
            ],
            [
                self._get_variance_plot(plot['scale_y'], plot['indices']) for plot in variance_plot_data
            ]
        )

    def get_collection_badges(self) -> List[html.Span]:
        return [
            html.Span([dbc.Badge(f'{collection_id}', className='badge-pill', color='primary'), ' '])
            for collection_id in self._loaded_collection_ids
        ]

    def get_collection_load_info(self) -> str:
        return f'Collections loaded in {os.path.dirname(self._dataframe_filename)}'

    def get_label_data(self) -> List[Dict[str, str]]:
        self.load_dataframes()
        return [{'label': label, 'value': label} for label in self.labels]

    def get_pc_options(self) -> List[Dict[str, Union[str, int]]]:
        self.load_results()
        return [{'label': f'PC {i+1}', 'value': i} for i in range(0, len(self._explained_variance_ratio))]

    def davies_bouldin(self, labels=None) -> pd.DataFrame:
        self.load_data()
        labels = labels or self._processed_label_df.columns
        scores_df = pd.DataFrame(data=self._scores,
                                 index=self._processed_label_df.index,
                                 columns=[f'PC {i+1}' for i in range(0, len(self._scores))])
        results = []
        for category_label in labels:
            categories = pd.unique(self._label_df[category_label])

            def _calculate_intercluster_distance():
                distances = {}
                for cat1 in categories:
                    distances[cat1] = {}
                    for cat2 in categories:
                        centroid1 = scores_df[self._processed_label_df[category_label] == cat1].mean()
                        centroid2 = scores_df[self._processed_label_df[category_label] == cat2].mean()
                        distances[cat1][cat2] = np.linalg.norm(centroid1 - centroid2)
                return distances

            def _calculate_intracluster_distance():
                distances = {}
                for category in categories:
                    centroid = scores_df[self._processed_label_df[category_label] == category].mean()
                    point_distances = scores_df[self._processed_label_df[category_label] == category].apply(
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
            r = _calculate_r(between_distances, within_distances)
            d = {cat1: max([r[cat1][cat2] for cat2 in categories if cat1 != cat2]) for cat1 in categories}
            db_ind = {cat: d[cat] / len(categories) for cat in categories}

            results.append(pd.DataFrame(index=[f'{category_label}={cat}' for cat in categories],
                                        data=[db_ind[cat] for cat in categories]))
        return pd.concat(results, axis=0)


def get_plot_data() -> Dict[str, List[Dict[str, Any]]]:
    try:
        plot_data = msgpack.loads(rds.get_value('pca_plot_data'), raw=False)
    except Exception as e:
        plot_data = None
    if plot_data is None:
        plot_data = {'score_plots': [], 'loading_plots': [], 'variance_plots': []}
    # warning: we don't validate any of this
    return plot_data


def set_plot_data(plot_data: Dict[str, List[Dict[str, Any]]]) -> None:
    rds.set_value('pca_plot_data', msgpack.dumps(plot_data))
