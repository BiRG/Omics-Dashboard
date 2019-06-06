import itertools
import os
import shutil
import time as tm
from typing import List, Dict, Any, Union, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import h5py
import msgpack
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
import scipy.stats as stats
from flask import url_for
from flask_login import current_user
from plotly.colors import DEFAULT_PLOTLY_COLORS
from sklearn.decomposition import PCA

import data_tools.redis as rds
from data_tools.access_wrappers.collections import get_collection_copy, upload_collection


def component_list(val):
    def _list_to_range(i):
        for a, b in itertools.groupby(enumerate(i), lambda x: x[1] - x[0]):
            b = list(b)
            yield b[0][1], b[-1][1]

    return ','.join([f'PC{r[0]+1}–PC{r[1]+1}' if r[0] != r[1] else f'PC{r[0]+1}' for r in _list_to_range(val)])


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
        self._x_min = None
        self._x_max = None
        self._loaded_collection_ids = []
        self._dataframe_filename = None
        self._results_filename = None
        self._good_x_inds = None
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

    def load_file_info(self):
        data_frame_filename = rds.get_value('pca_dataframe_filename')
        self._dataframe_filename = data_frame_filename.decode('utf-8') if data_frame_filename is not None else None
        results_filename = rds.get_value('pca_results_filename')
        self._results_filename = results_filename.decode('utf-8') if results_filename is not None else None
        if not self._dataframe_filename or not os.path.isfile(self._dataframe_filename):
            rds.delete_value('pca_dataframe_filename')
            rds.delete_value('pca_results_filename')
            self._dataframe_filename = None
            self._results_filename = None
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
        with h5py.File(self._dataframe_filename) as file:
            self._x = np.array(file['x']) if 'x' in file else None
            self._x_min = np.array(file['x_min']) if 'x_min' in file else None
            self._x_max = np.array(file['x_max']) if 'x_max' in file else None

    def save_dataframes(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._processed_label_df.to_hdf(self._dataframe_filename, 'processed_label_df', mode='a')
        self._numeric_df.to_hdf(self._dataframe_filename, 'numeric_df', mode='a')
        with h5py.File(self._dataframe_filename, 'r+') as file:
            if self._x is not None:
                if 'x' in file:
                    del file['x']
                file['x'] = self._x
            if self._x_min is not None:
                if 'x_min' in file:
                    del file['x_min']
                file['x_min'] = self._x_min
            if self._x_max is not None:
                if 'x_max' in file:
                    del file['x_max']
                file['x_max'] = self._x_max

    def load_labels(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._processed_label_df = pd.read_hdf(self._dataframe_filename, 'processed_label_df')

    def save_labels(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._processed_label_df.to_hdf(self._dataframe_filename, 'processed_label_df', mode='a')

    def load_results(self):
        with h5py.File(self._results_filename, 'r') as file:
            self._x = np.array(file['x'])
            self._x.reshape((1, max(self._x.shape)))
            self._x_min = np.array(file['x_min']) if 'x_min' in file else None
            self._x_max = np.array(file['x_max']) if 'x_max' in file else None
            if self._x_min is not None:
                self._x_min.reshape((1, -1))
            if self._x_max is not None:
                self._x_max.reshape((1, -1))
            self._loadings = np.array(file['loadings'])
            self._scores = np.array(file['scores'])
            self._explained_variance_ratio = np.array(file['explained_variance_ratio'])
        self.load_labels()

    def save_results(self, filename=None, file_format='hdf5'):
        if not filename:
            filename = self._results_filename
        with h5py.File(filename, 'w') as file:  # always create new because dimensions might change
            file['loadings'] = self._loadings
            file['scores'] = self._scores
            file['explained_variance_ratio'] = self._explained_variance_ratio
            file['x'] = self._x
            if self._x_min is not None:
                file['x_min'] = self._x_min
            if self._x_max is not None:
                file['x_max'] = self._x_max

    def load_data(self):
        self.load_results()
        self.load_dataframes()

    def set_file_metadata(self, attrs, filename=None):
        """
        Use to set things like description, name, parameters
        :param attrs:
        :param filename:
        :return:
        """
        filename = filename or self._results_filename
        with h5py.File(filename, 'r+') as file:
            for key, value in attrs.items():
                file.attrs[key] = value

    def post_results(self, name, analysis_ids):
        self.load_data()
        score_plot_data = get_plot_data()['score_plots']
        include_db_index = any([plot['include_db_index'] for plot in score_plot_data])
        filename = self.download_results(file_formats=['hdf5'], score_plot_data=get_plot_data()['score_plots'],
                                         include_db_index=include_db_index)
        description = name
        with h5py.File(filename, 'r') as file:
            if 'description' in file.attrs:
                description = file.attrs['description'] or name
        metadata = {
            'name': name,
            'description': description,
            'analysis_ids': analysis_ids,
            'kind': 'results',
            'parent_id': self._loaded_collection_ids[0]
        }
        collection = upload_collection(current_user, filename, metadata, False)
        return [dbc.Alert(['Posted results as ', html.A(f'Collection {collection.id}.',
                                                        href=url_for('collections.render_collection',
                                                                     collection_id=collection.id))],
                          dismissable=True,
                          color='success')]

    def _davies_bouldin(self, category_label, label_values, for_display=False) -> pd.DataFrame:
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
        results.rename_axis(category_label)
        results['S'] = [within_distances[cat] for cat in categories]
        for cat1 in categories:
            results[f'M_{cat1}'] = [between_distances[cat1][cat2] for cat2 in categories]
        for cat1 in categories:
            results[f'R_{cat1}'] = [r[cat1][cat2] for cat2 in categories]
        results['DB'] = [db_ind[cat] for cat in categories]

        if for_display:
            results = results.applymap('{:.5f}'.format)
        results[category_label] = categories
        columns = [category_label, 'DB'] + [column for column in results.columns if
                                            column not in {category_label, 'DB'}]
        return results[columns]

    def _get_db_index_dataframe(self, color_by_labels):
        color_by_labels = color_by_labels or []
        color_label = ','.join(color_by_labels) if color_by_labels else 'All'
        label_df = self._processed_label_df.reset_index()
        color_labels = label_df[color_by_labels].apply(lambda x: ','.join(x.apply(str)),
                                                       axis=1) if color_by_labels else pd.Series(
            ['All' for _ in range(0, len(label_df))])

        return self._davies_bouldin(color_label, color_labels, True)

    def _get_scores_dataframe(self):
        return pd.DataFrame(data=self._scores,
                            index=self._processed_label_df.index,
                            columns=[f'PC{i+1}' for i in range(0, len(self._scores))])

    def _get_variance_dataframe(self):
        return pd.DataFrame(data=self._explained_variance_ratio,
                            index=[f'PC{i+1}' for i in range(0, len(self._explained_variance_ratio))],
                            columns=['explained_variance_ratio'])

    def _get_loading_dataframe(self):
        return pd.DataFrame(data=self._loadings,
                            index=[f'PC{i+1}' for i in range(0, len(self._loadings))],
                            columns=self._x)

    def download_results(self,
                         include_scores=True,
                         include_loadings=True,
                         include_variance=True,
                         include_db_index=True,
                         file_formats=None,
                         score_plot_data=None):
        file_formats = file_formats or ['hdf5']
        if include_db_index and not score_plot_data:
            raise ValueError('No score plot data provided')
        self.load_data()
        multiple_results = [include_scores, include_loadings, include_variance, include_db_index].count(True) > 1 \
                           or include_db_index and len(score_plot_data) > 1
        create_archive = len(file_formats) > 1 or (multiple_results and 'csv' in file_formats)

        def _save_scores(name, file_format):
            if file_format == 'csv':
                scores_df = pd.DataFrame(data=self._scores,
                                         columns=[f'PC{i+1}' for i in range(0, len(self._scores))],
                                         index=self._numeric_df.index)
                scores_df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if 'pca_scores' in file:
                        del file['pca_scores']
                    file['pca_scores'] = self._scores

        def _save_loadings(name, file_format):
            if file_format == 'csv':
                loadings_df = pd.DataFrame(data=self._loadings,
                                           columns=np.ravel(self._x),
                                           index=[f'PC{i+1}' for i in range(0, len(self._loadings))])
                loadings_df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if 'pca_loadings' in file:
                        del file['pca_loadings']
                    if 'x' in file:
                        del file['x']
                    if 'x_min' in file:
                        del file['x_min']
                    if 'x_max' in file:
                        del file['x_max']

                    file['pca_loadings'] = self._loadings
                    file['x'] = self._x
                    if self._x_max is not None:
                        file['x_max'] = self._x_max
                    if self._x_min is not None:
                        file['x_min'] = self._x_min

        def _save_variance(name, file_format):
            if file_format == 'csv':
                variance_df = pd.DataFrame(data=self._explained_variance_ratio,
                                           columns=['explained_variance_ratio'],
                                           index=[f'PC{i+1}' for i in range(0, len(self._explained_variance_ratio))])
                variance_df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if 'pca_explained_variance_ratio' in file:
                        del file['pca_explained_variance_ratio']
                    file['pca_explained_variance_ratio'] = self._explained_variance_ratio

        def _save_davies_bouldin(path, file_format, score_plots):
            # calculate davis_bouldin for all active plots that use it.
            db_dfs = {}
            for plot in score_plots:
                if plot['include_db_index']:
                    color_by_labels = plot['color_by'] or []
                    color_label = ','.join(color_by_labels) if color_by_labels else 'All'
                    label_df = self._processed_label_df.reset_index()
                    color_labels = label_df[color_by_labels].apply(lambda x: ','.join(x.apply(str)),
                                                                   axis=1) if color_by_labels else pd.Series(
                        ['All' for _ in range(0, len(label_df))])
                    db_dfs[','.join(plot['color_by'])] = self._davies_bouldin(color_label, color_labels)
            if file_format == 'csv':
                for name, db_df in db_dfs.items():
                    db_df.to_csv(f'{path}_{name}_db_index.csv')
                return [f'{path}_{name}_db_index.csv' for name in db_dfs.keys()]
            else:
                with h5py.File(path, 'a') as file:
                    for name, db_df in db_dfs.items():
                        group_name = f'db_index_{name}'
                        if group_name in file:
                            del file[group_name]
                        group = file.create_group(group_name)
                        if name in group:
                            del group[name]
                        for column in db_df.columns:
                            arr_name = column
                            if arr_name in group:
                                del group[arr_name]
                            arr = db_df[column].to_numpy()
                            if len(arr.shape) == 1:
                                arr = np.reshape(arr, (arr.shape[0], 1))
                            if arr.dtype.type in {np.object_, np.string_}:
                                arr = arr.astype(h5py.special_dtype(vlen=bytes))
                            group[arr_name] = arr
                    return path

        if len(self._loaded_collection_ids) > 1:
            filename = 'pca_collections_' + '_'.join([str(collection_id)
                                                      for collection_id in self._loaded_collection_ids])
        else:
            filename = f'pca_collection_{self._loaded_collection_ids[0]}'
        root_dir = os.path.dirname(self._results_filename)
        results_dir = os.path.join(root_dir, filename)
        if os.path.isdir(results_dir):
            shutil.rmtree(results_dir)
        elif os.path.isfile(results_dir):
            os.remove(results_dir)
        os.mkdir(results_dir)
        if 'hdf5' in file_formats:
            os.mkdir(f'{results_dir}/hdf5')
            h5_filename = f'{results_dir}/hdf5/{filename}.h5'
            with h5py.File(h5_filename, 'a') as current_file, h5py.File(self._results_filename) as results_file:
                for key, value in results_file.attrs.items():
                    current_file.attrs[key] = value
            if include_scores:
                _save_scores(h5_filename, 'hdf5')
            if include_loadings:
                _save_loadings(h5_filename, 'hdf5')
            if include_variance:
                _save_variance(h5_filename, 'hdf5')
            if include_db_index:
                _save_davies_bouldin(h5_filename, 'hdf5', score_plot_data)
            if not create_archive:
                return h5_filename
        if 'csv' in file_formats:
            os.mkdir(f'{results_dir}/csv')
            csv_prefix = f'{results_dir}/csv'
            if include_scores:
                csv_filename = f'{csv_prefix}/{filename}_scores.csv'
                _save_scores(csv_filename, 'csv')
                if not create_archive:
                    return csv_filename
            if include_loadings:
                csv_filename = f'{csv_prefix}/{filename}_loadings.csv'
                _save_loadings(csv_filename, 'csv')
                if not create_archive:
                    return csv_filename
            if include_variance:
                csv_filename = f'{csv_prefix}/{filename}_variance.csv'
                _save_variance(csv_filename, 'csv')
                if not create_archive:
                    return csv_filename
            if include_db_index:
                get_plot_data()
                csv_filenames = _save_davies_bouldin(f'{csv_prefix}/{filename}', 'csv', score_plot_data)
                if not create_archive:
                    return csv_filenames[0]
        return shutil.make_archive(results_dir, 'zip', root_dir, filename)

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
            try:
                x_min = collection.get_dataset('x_min')[:, inds]
                collection.set_dataset('x_min', x_min)
                self._x_min = x_min
            except:
                self._x_min = None
            try:
                x_max = collection.get_dataset('x_max')[:, inds]
                collection.set_dataset('x_max', x_max)
                self._x_max = x_max
            except:
                self._x_max = None
            del y
            data_dir = os.path.dirname(collection.filename)
            self._results_filename = os.path.join(data_dir, 'results.h5')
            self._dataframe_filename = os.path.join(data_dir, 'dataframes.h5')
            self._loaded_collection_ids = collection_ids
            self._label_df = collection.get_dataframe(include_only_labels=True)
            self._numeric_df = collection.get_dataframe(numeric_columns=True, include_labels=False)
            self._good_x_inds = np.where(self._numeric_df.isnull().sum() == 0)[0]
            self._numeric_df = self._numeric_df[self._numeric_df.columns[self._good_x_inds]]
            self._x = x[:, self._good_x_inds]
            self._x_min = self._x_min[:, self._good_x_inds] if self._x_min is not None else None
            self._x_max = self._x_max[:, self._good_x_inds] if self._x_max is not None else None
            self._processed_label_df = self._label_df
            os.remove(collection.filename)
            self.set_file_info()
            self.save_dataframes()

    def perform_pca(self,
                    model_by: str = None,
                    ignore_by: str = None,
                    scale_by: str = None,
                    pair_on: List[str] = None,
                    pair_with: str = None) -> (str, str, str):
        data_load_start = tm.time()
        self.load_dataframes()
        label_df = self._label_df
        numeric_df = self._numeric_df
        data_load_end = tm.time()

        if scale_by:
            means = numeric_df.loc[label_df.query(scale_by).index].mean()
            std_devs = numeric_df.loc[label_df.query(scale_by).index].std()
            numeric_df = numeric_df.sub(means, axis=1).divide(std_devs, axis=1)  # do scaling before everything else

        if ignore_by:
            label_df = label_df.query(ignore_by)
            numeric_df = numeric_df.loc[label_df.index]

        warnings = []
        message_color = 'success'
        if pair_on and pair_with:
            good_queries = []
            for vals, idx, in label_df.groupby(pair_on).groups.items():
                # find the pair conditions in the sub dataframe
                if not isinstance(vals, list):
                    vals = [vals]
                try:
                    target_rows = label_df.loc[idx].query(pair_with)
                    numeric_df.loc[idx].sub(target_rows.mean(), axis=1)
                except KeyError:
                    target_rows = []
                if not len(target_rows):
                    warnings.append(f'No records matching {pair_with} for {pair_on}=={vals}! '
                                    f'{pair_on}=={vals} excluded from analysis.')
                    good_queries.append(
                        '&'.join([f'{pair_on_i}!={vals_i}' for pair_on_i, vals_i in zip(pair_on, vals)]))
                    message_color = 'warning'
            if len(good_queries):
                label_df = label_df.query('&'.join(good_queries))
                numeric_df = numeric_df.loc[label_df.index]

        if model_by:
            model_numeric_df = numeric_df.loc[label_df.index]
        else:
            model_numeric_df = numeric_df

        self._good_x_inds = np.where(model_numeric_df.isnull().sum() == 0)[0]
        good_columns = model_numeric_df.columns[self._good_x_inds]
        model_numeric_df = model_numeric_df[good_columns]
        numeric_df = numeric_df[good_columns]
        self._x = self._x[:, self._good_x_inds]
        self._x_min = self._x_min[:, self._good_x_inds] if self._x_min is not None else None
        self._x_max = self._x_max[:, self._good_x_inds] if self._x_max is not None else None
        metadata = {
            'model_by': model_by or '',
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
        if model_by:
            description += f' including {model_by}'
        if ignore_by:
            description += f' ignoring {ignore_by}'
        if pair_on and pair_with:
            description += f' paired on {pair_on} against {pair_with}'
        metadata['name'] = name
        metadata['description'] = description

        self._processed_label_df = label_df
        start_time = tm.time()
        pca = PCA()
        model_numeric_df.to_csv('/tmp/model_numeric_df.csv')
        pca.fit(model_numeric_df)
        self._scores = pca.transform(numeric_df)
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

    def _get_score_plot(self,
                        ordinate,
                        abscissa,
                        color_by_labels,
                        include_db_index,
                        label_by_labels,
                        encircle_by,
                        plot_centroid,
                        plot_medoid,
                        graph_only=False,
                        theme=None) -> Union[dcc.Graph, Tuple[dcc.Graph, Union[dash_table.DataTable, html.Div]]]:
        theme = theme or 'plotly_white'
        color_by_labels = color_by_labels or []
        encircle_by = encircle_by or []
        label_by_labels = label_by_labels or []
        color_label = ','.join(color_by_labels) if color_by_labels else 'All'
        label_df = self._processed_label_df.reset_index()
        color_labels = label_df[color_by_labels].apply(lambda x: ','.join(x.apply(str)), axis=1) if color_by_labels \
            else pd.Series(['All' for _ in range(0, len(label_df))])
        color_names = list(color_labels.unique())
        color_indices = [label_df.index[color_labels == color_name] for color_name in color_names]

        label_labels = label_df[label_by_labels].apply(lambda x: ','.join(x.apply(str)), axis=1) if label_by_labels \
            else None

        if len(color_names) > 1 and include_db_index:
            db_df = self._davies_bouldin(color_label, color_labels, True)
            style_header = {'backgroundColor': '#303030'} if theme == 'plotly_dark' else {}
            style_cell = {'backgroundColor': '#444444'} if theme == 'plotly_dark' else {}
            table = dash_table.DataTable(columns=[{'name': val, 'id': val} for val in db_df.columns],
                                         data=db_df.to_dict('rows'),
                                         style_as_list_view=True,
                                         style_header=style_header,
                                         style_cell=style_cell)
        else:
            table = html.Div()

        graph_data = [
            go.Scatter(  # dummy series to use as stand-in for legend title
                x=[0],
                y=[0],
                name=color_label,
                mode='markers',
                marker={
                    'opacity': 0
                }
            )
        ]
        shapes = []
        annotations = []

        if len(color_indices) > len(DEFAULT_PLOTLY_COLORS):  # repeat default color list
            colors = []
            while len(colors) < len(color_indices):
                colors += DEFAULT_PLOTLY_COLORS
        else:
            colors = DEFAULT_PLOTLY_COLORS
        colors = colors[:len(color_indices)]

        for inds, name, color in zip(color_indices, color_names, colors):
            graph_data.append(
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
                        'line': {'width': 0.5, 'color': 'white'},
                        'color': color
                    }
                )
            )
            if plot_centroid:
                graph_data.append(
                    go.Scatter(
                        x=[np.mean(self._scores[inds, abscissa])],
                        y=[np.mean(self._scores[inds, ordinate])],
                        text=f'{name} centroid',
                        name=f'{name} centroid',
                        mode='markers',
                        marker={
                            'size': 20,
                            'opacity': 0.85,
                            'line': {'width': 0.5, 'color': 'white'},
                            'color': color,
                            'symbol': 'x'
                        }
                    )
                )
            if plot_medoid:
                graph_data.append(
                    go.Scatter(
                        x=[np.median(self._scores[inds, abscissa])],
                        y=[np.median(self._scores[inds, ordinate])],
                        text=f'{name} medoid',
                        name=f'{name} medoid',
                        mode='markers',
                        marker={
                            'size': 20,
                            'opacity': 0.85,
                            'line': {'width': 0.5, 'color': 'white'},
                            'color': color,
                            'symbol': 'cross'
                        }
                    )
                )
            if label_labels is not None:
                annotations = annotations + [
                    {
                        'x': self._scores[ind, abscissa],
                        'y': self._scores[ind, ordinate],
                        'xref': 'x',
                        'yref': 'y',
                        'text': label_labels[ind],
                        'showarrow': False
                    } for ind in inds
                ]
            for metric in encircle_by:
                if metric[1:] == 'std':
                    x_std = np.std(self._scores[inds, abscissa])
                    y_std = np.std(self._scores[inds, ordinate])
                    x_mean = np.mean(self._scores[inds, abscissa])
                    y_mean = np.mean(self._scores[inds, ordinate])
                    x0 = x_mean - x_std * float(metric[0])
                    x1 = x_mean + x_std * float(metric[0])
                    y0 = y_mean - y_std * float(metric[0])
                    y1 = y_mean + y_std * float(metric[0])
                if metric[1:] == 'sem':
                    x_sem = stats.sem(self._scores[inds, abscissa])
                    y_sem = stats.sem(self._scores[inds, ordinate])
                    x_mean = np.mean(self._scores[inds, abscissa])
                    y_mean = np.mean(self._scores[inds, ordinate])
                    x0 = x_mean - x_sem * float(metric[0])
                    x1 = x_mean + x_sem * float(metric[0])
                    y0 = y_mean - y_sem * float(metric[0])
                    y1 = y_mean + y_sem * float(metric[0])
                elif metric == 'range':
                    x0 = np.min(self._scores[inds, abscissa])
                    x1 = np.max(self._scores[inds, abscissa])
                    y0 = np.min(self._scores[inds, ordinate])
                    y1 = np.max(self._scores[inds, ordinate])
                elif metric == '95percentile':
                    x_ptile = np.percentile(self._scores[inds, abscissa], 95)
                    y_ptile = np.percentile(self._scores[inds, ordinate], 95)
                    x_median = np.median(self._scores[inds, abscissa])
                    y_median = np.median(self._scores[inds, ordinate])
                    x0 = x_median - x_ptile
                    x1 = x_median + x_ptile
                    y0 = y_median - y_ptile
                    y1 = y_median + y_ptile
                elif metric[2:] == 'conf':
                    conf = float(metric[:2]) / 100.0
                    n = len(self._scores[inds, abscissa])
                    x_mean = np.mean(self._scores[inds, abscissa])
                    y_mean = np.mean(self._scores[inds, ordinate])
                    x_h = stats.sem(self._scores[inds, abscissa]) * stats.t.ppf((1 + conf) / 2, n - 1)
                    y_h = stats.sem(self._scores[inds, ordinate]) * stats.t.ppf((1 + conf) / 2, n - 1)
                    x0 = x_mean - x_h
                    x1 = x_mean + x_h
                    y0 = y_mean - y_h
                    y1 = y_mean + y_h
                else:
                    x0 = 0
                    x1 = 0
                    y0 = 0
                    y1 = 0

                shapes.append(
                    {
                        'type': 'circle',
                        'xref': 'x',
                        'yref': 'y',
                        'x0': x0,
                        'y0': y0,
                        'x1': x1,
                        'y1': y1,
                        'opacity': 0.25,
                        'fillcolor': color,
                        'line': {'color': color}
                    }
                )
        axis_line_style = {
            'zerolinecolor': '#9FA8B2',
            'gridcolor': '#444444',
        } if theme == 'plotly_dark' else {}
        graph = dcc.Graph(figure={
            'data': graph_data,
            'layout': go.Layout(
                shapes=shapes,
                annotations=annotations,
                height=700,
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis={
                    'title': f'PC{abscissa + 1}',
                    **axis_line_style
                },
                yaxis={
                    'title': f'PC{ordinate + 1}',
                    **axis_line_style
                }
            )
        })
        if graph_only:
            return graph
        return graph, table

    def _get_loading_plot(self, loadings, theme=None) -> dcc.Graph:
        theme = theme or 'plotly_white'

        axis_line_style = {
            'zerolinecolor': '#9FA8B2',
            'gridcolor': '#444444',
        } if theme == 'plotly_dark' else {}
        return dcc.Graph(figure={
            'data': [
                go.Scatter(
                    x=self._x[0, :],
                    y=self._loadings[ind, :],
                    text=f'PC {ind+1}<br>{100*self._explained_variance_ratio[ind]:.3f} % variance',
                    name=f'PC {ind+1}',
                    mode='lines'
                ) for ind in loadings
            ],
            'layout': go.Layout(
                xaxis={
                    'title': 'Chemical Shift (ppm)',
                    'autorange': 'reversed',
                    **axis_line_style
                },
                yaxis={
                    'title': 'PC Loading',
                    **axis_line_style
                },
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        })

    def _get_variance_plot(self, scale_y=False, indices=None, theme=None) -> dcc.Graph:
        theme = theme or 'plotly_white'
        all_indices = [i for i in range(0, len(self._explained_variance_ratio))]
        indices = list(set(all_indices).intersection(set(indices)))
        axis_line_style = {
            'zerolinecolor': '#9FA8B2',
            'gridcolor': '#444444',
        } if theme == 'plotly_dark' else {}
        xaxis = {'title': 'Principal Component', **axis_line_style}
        yaxis = {'title': '% Variance Explained', **axis_line_style}
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
                yaxis=yaxis,
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        })

    def _get_cumulative_variance_plot(self, threshold, theme=None) -> dcc.Graph:
        theme = theme or 'plotly_white'
        axis_line_style = {
            'zerolinecolor': '#9FA8B2',
            'gridcolor': '#444444',
        } if theme == 'plotly_dark' else {}
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
                xaxis={'title': 'Number of Principal Components', 'tickvals': x_ticks, **axis_line_style},
                yaxis={'title': '% Variance Explained', 'tickvals': y_ticks, **axis_line_style},
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
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
                  cumulative_variance_plot_data,
                  include_db_index_tables=True) -> (List[Union[dcc.Graph, dash_table.DataTable]],
                                                     List[dcc.Graph],
                                                     List[dcc.Graph],
                                                     List[dcc.Graph]):
        self.load_labels()
        self.load_results()
        from dashboards.dashboard import get_plot_theme
        theme = get_plot_theme()
        score_plots = [self._get_score_plot(plot['ordinate'],
                                            plot['abscissa'],
                                            plot['color_by'],
                                            include_db_index_tables and plot['include_db_index'],
                                            plot['label_by'],
                                            plot['encircle_by'],
                                            plot['include_centroid'],
                                            plot['include_medoid'],
                                            theme=theme)
                       for plot in score_plot_data]
        return (
            [
                item for pair in score_plots for item in pair
            ] if include_db_index_tables else [pair[0] for pair in score_plots],
            [
                self._get_loading_plot(plot['indices'], theme=theme) for plot in loading_plot_data
            ],
            [
                self._get_variance_plot(plot['scale_y'], plot['indices'], theme=theme) for plot in variance_plot_data
            ],
            [
                self._get_cumulative_variance_plot(plot['threshold'],
                                                   theme=theme) for plot in cumulative_variance_plot_data
            ]
        )

    def download_plots(self,
                       score_plot_data,
                       loading_plot_data,
                       variance_plot_data,
                       cumulative_variance_plot_data,
                       file_formats=None) -> str:
        file_formats = file_formats or []
        pio.orca.config.use_xvfb = True
        if len(self._loaded_collection_ids) > 1:
            base_filename = 'pca_collections_' + '_'.join([str(collection_id)
                                                           for collection_id in self._loaded_collection_ids])
        else:
            base_filename = f'pca_collection_{self._loaded_collection_ids[0]}'
        root_dir = os.path.dirname(self._results_filename)
        plot_dir = os.path.join(root_dir, f"{base_filename}_plots")
        if os.path.isdir(plot_dir):
            shutil.rmtree(plot_dir)
        elif os.path.isfile(plot_dir):
            os.remove(plot_dir)
        os.mkdir(plot_dir)
        for file_format in file_formats:
            format_dir = os.path.join(plot_dir, file_format)
            os.mkdir(format_dir)
            for plot_info in score_plot_data:
                plot = self._get_score_plot(plot_info['ordinate'],
                                            plot_info['abscissa'],
                                            plot_info['color_by'],
                                            False,
                                            plot_info['label_by'],
                                            plot_info['encircle_by'],
                                            plot_info['include_centroid'],
                                            plot_info['include_medoid'],
                                            True)
                filename = f'{base_filename}_scores_{plot_info["ordinate"]+1}_vs_{plot_info["abscissa"]+1}'
                if plot_info['color_by']:
                    filename += '_by_' + ','.join(plot_info['color_by'])
                filename = os.path.join(format_dir, f'{filename}.{file_format}')
                pio.write_image(plot.to_plotly_json()['props']['figure'], filename)
            for plot_info in loading_plot_data:
                plot = self._get_loading_plot(plot_info['indices'])
                components = component_list(plot_info['indices']).replace('–', '-')
                filename = f"{format_dir}/{base_filename}_loadings_{components}.{file_format}"
                pio.write_image(plot.to_plotly_json()['props']['figure'], filename)
            for plot_info in variance_plot_data:
                plot = self._get_variance_plot(plot_info['scale_y'], plot_info['indices'])
                components = component_list(plot_info['indices']).replace('–', '-')
                filename = f"{format_dir}/{base_filename}_variance_{components}.{file_format}"
                pio.write_image(plot.to_plotly_json()['props']['figure'], filename)
            for plot_info in cumulative_variance_plot_data:
                plot = self._get_cumulative_variance_plot(plot_info['threshold'])
                filename = f'{format_dir}/{base_filename}_cumulative_variance_{plot_info["threshold"]}.{file_format}'
                pio.write_image(plot.to_plotly_json()['props']['figure'], filename)
        return shutil.make_archive(plot_dir, 'zip', root_dir, f"{base_filename}_plots")

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


