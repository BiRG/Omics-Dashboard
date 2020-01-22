import itertools
import os
import time as tm
from typing import List, Dict, Any, Union

import dash_bootstrap_components as dbc
import dash_html_components as html
import h5py
import msgpack
import numpy as np
import pandas as pd

import config.redis_config as rds

from dashboards.dashboard_model import DashboardModel


class MultivariateAnalysisModel(DashboardModel):
    redis_prefix = ''
    _empty_plot_data = {}

    def __init__(self, load_data=False):
        super().__init__(load_data)
        if load_data:
            try:
                self.load_results()
            except Exception:
                self._loadings = self._scores = self._explained_variance_ratio = self._x = None

    @property
    def results_exist(self):
        try:
            self.load_results()
            return True
        except:
            return False

    @staticmethod
    def component_list(val):
        def _list_to_range(i):
            for a, b in itertools.groupby(enumerate(i), lambda x: x[1] - x[0]):
                b = list(b)
                yield b[0][1], b[-1][1]

        return ','.join([f'PC{r[0]+1}–PC{r[1]+1}' if r[0] != r[1] else f'PC{r[0]+1}' for r in _list_to_range(val)])

    @classmethod
    def get_plot_data(cls) -> Dict[str, List[Dict[str, Any]]]:
        try:
            plot_data = msgpack.loads(rds.get_value(f'{cls.redis_prefix}_plot_data'), raw=False)
        except Exception as e:
            plot_data = None
        if plot_data is None:
            plot_data = cls._empty_plot_data
        # warning: we don't validate any of this
        return plot_data

    @classmethod
    def set_plot_data(cls, plot_data: Dict[str, List[Dict[str, Any]]]) -> None:
        rds.set_value(f'{cls.redis_prefix}_plot_data', msgpack.dumps(plot_data))

    @classmethod
    def clear_plot_data(cls):
        rds.delete_value(f'{cls.redis_prefix}_plot_data')

    def load_file_info(self):
        data_frame_filename = rds.get_value(f'{self.redis_prefix}_dataframe_filename')
        self._dataframe_filename = data_frame_filename.decode('utf-8') if data_frame_filename is not None else None
        results_filename = rds.get_value(f'{self.redis_prefix}_results_filename')
        self._results_filename = results_filename.decode('utf-8') if results_filename is not None else None
        if not self._dataframe_filename or not os.path.isfile(self._dataframe_filename):
            rds.delete_value(f'{self.redis_prefix}_dataframe_filename')
            rds.delete_value(f'{self.redis_prefix}_results_filename')
            self._dataframe_filename = None
            self._results_filename = None
        try:
            self._loaded_collection_ids = msgpack.loads(rds.get_value(f'{self.redis_prefix}_loaded_collection_ids'))
        except TypeError:
            self._loaded_collection_ids = []

    def set_file_info(self):
        rds.set_value(f'{self.redis_prefix}_dataframe_filename', self._dataframe_filename.encode('utf-8'))
        rds.set_value(f'{self.redis_prefix}_results_filename', self._results_filename.encode('utf-8'))
        rds.set_value(f'{self.redis_prefix}_loaded_collection_ids', msgpack.dumps(self._loaded_collection_ids))

    def load_dataframes(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._processed_label_df = pd.read_hdf(self._dataframe_filename, 'processed_label_df')
        self._numeric_df = pd.read_hdf(self._dataframe_filename, 'numeric_df')
        with h5py.File(self._dataframe_filename, 'r') as file:
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
        self.load_labels()

    def save_results(self, filename=None, file_format='h5'):
        if not filename:
            filename = self._results_filename
        with h5py.File(filename, 'w') as file:  # always create new because dimensions might change
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
            file.attrs.update(attrs)

    def download_results(self, **kwargs):
        raise NotImplementedError()

    def post_results(self, name, analysis_ids):
        raise NotImplementedError()

    def get_collections(self, collection_ids: Union[List[int], int]):
        super().get_collections(collection_ids)
        self.clear_plot_data()

    def fit(self, numeric_df, model_numeric_df, model_label_df, **kwargs):
        raise NotImplementedError()

    def perform_analysis(self,
                         model_by: str = None,
                         ignore_by: str = None,
                         scale_by: str = None,
                         pair_on: List[str] = None,
                         pair_with: str = None,
                         project_by: str = None,
                         **kwargs) -> (str, str, str):
        data_load_start = tm.time()
        self.load_dataframes()
        label_df = self._label_df
        numeric_df = self._numeric_df
        data_load_end = tm.time()

        if model_by == 'index':
            model_by = None

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
                    numeric_df.loc[idx] = numeric_df.loc[idx].sub(numeric_df.loc[target_rows.index].mean())
                except KeyError:
                    target_rows = []
                if not len(target_rows):
                    warnings.append('\n'.join([f'No records matching {pair_with} for {pair_on_i}=="{vals_i}!". '
                                               f'{pair_on_i}=="{vals_i}" excluded from analysis.'
                                               for pair_on_i, vals_i in zip(pair_on, vals)]))
                    good_queries.append(
                        ' & '.join([f'{pair_on_i}!="{vals_i}"' for pair_on_i, vals_i in zip(pair_on, vals)]))
                    message_color = 'warning'
            if len(good_queries):
                query = ' & '.join(good_queries)
                label_df = label_df.query(query)
                numeric_df = numeric_df.loc[label_df.index]

        if model_by:
            if project_by:
                label_df = label_df.query(f'({model_by}) | ({project_by})')
            else:
                label_df = label_df.query(model_by)
            if pair_on and pair_with:
                label_df = label_df.query(f'not {pair_with}')
            numeric_df = numeric_df.loc[label_df.index]
            model_label_df = label_df.query(model_by)
            model_numeric_df = numeric_df.loc[model_label_df.index]
        else:
            if pair_on and pair_with:
                label_df = label_df.query(f'not {pair_with}')
            numeric_df = numeric_df.loc[label_df.index]
            model_label_df = label_df
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
            'pair_with': pair_with or '',
            'project_by': project_by or ''
        }
        name = self.redis_prefix.upper()
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
        self.fit(numeric_df, model_numeric_df, model_label_df, **kwargs)
        end_time = tm.time()
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
            html.Strong(f'Performed analysis in {(end_time-data_load_start):.3f} s.'),
            html.Br(),
            f'Loaded data in {(data_load_end-data_load_start):.3f} s.',
            html.Br(),
            f'Processed data in {(start_time-data_load_end):.3f} s.',
            html.Br(),
            f'Fit model in {(end_time - start_time):.3f} s.',
            html.Br(),
            f'Cached data in {(save_end_time - end_time):.3f} s.'
        ]
        return html.P(message_children), metadata['name'], message_color

    def get_collection_badges(self) -> List[html.Span]:
        return [
            html.Span([dbc.Badge(f'{collection_id}', className='badge-pill', color='primary'), ' '])
            for collection_id in self._loaded_collection_ids
        ] if self._loaded_collection_ids else [html.Span([dbc.Badge('None', className='badge-pill')])]

    def get_collection_load_info(self) -> str:
        return f'Collections loaded in {os.path.dirname(self._dataframe_filename)}'

