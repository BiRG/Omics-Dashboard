from ..multivariate_analysis_data import MultivariateAnalysisData
import itertools
import os
import shutil
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
from pyopls import OPLSValidator

import data_tools.redis as rds
from data_tools.access_wrappers.collections import get_collection_copy, upload_collection


class OPLSData(MultivariateAnalysisData):
    _redis_prefix = 'opls'

    def __init__(self, load_data=False):
        super().__init__(load_data)
        # any of these can be None
        self._x_weights = None
        self._y_weights = None
        self._orthogonal_x_loadings = None
        self._x_loadings = None
        self._orthogonal_x_scores = None
        self._x_scores = None
        self._y_scores = None
        self._filtered_X = None
        self._coef = None
        self._r_squared_X = None
        self._r_squared_Y = None
        self._feature_p_values = None
        self._permuted_loadings = None
        self._q_squared_p_value = None
        self._permutation_q_squared = None
        self._q_squared = None

        self._accuracy = None
        self._permutation_accuracy = None
        self._accuracy_p_value = None
        self._roc_auc = None
        self._permutation_roc_auc = None
        self._roc_auc_p_value = None

    def load_results(self):
        super().load_results()
        with h5py.File(self._results_filename, 'r') as file:
            self._x_weights = file['/opls/x_weights']
            self._y_weights = file['/opls'].attrs['y_weights']
            self._orthogonal_x_loadings = file['/opls/orthogonal_x_loadings']
            self._x_loadings = file['/opls/x_loadings']
            self._orthogonal_x_scores = file['/opls/orthogonal_x_scores']
            self._x_scores = file['/opls/x_scores']
            self._y_scores = file['/opls/y_scores']
            self._filtered_X = file['/opls/filtered_X']
            self._coef = file['/opls/coef']
            self._r_squared_X = file['/opls'].attrs['r_squared_X']
            self._r_squared_Y = file['/opls'].attrs['r_squared_Y']
            self._feature_p_values = file['/opls_cv/feature_p_values']
            self._permuted_loadings = file['/opls_cv/permuted_loadings']
            self._q_squared_p_value = file['/opls_cv'].attrs['q_squared_p_value']
            self._permutation_q_squared = file['/opls_cv/permutation_q_squared']
            self._q_squared = file['/opls_cv'].attrs['q_squared']
        self.load_labels()

    def save_results(self, filename=None, file_format='hdf5'):
        super().save_results(filename, file_format)
        with h5py.File(filename, 'w') as file:  # always create new because dimensions might change
            file['/opls/x_weights'] = self._x_weights
            file['/opls/y_weights'] = self._y_weights
            file['/opls/orthogonal_x_loadings'] = self._orthogonal_x_loadings
            file['/opls/x_loadings'] = self._x_loadings
            file['/opls/orthogonal_x_scores'] = self._orthogonal_x_scores
            file['/opls/x_scores'] = self._x_scores
            file['/opls/y_scores'] = self._y_scores
            file['/opls/coef'] = self._coef
            file['/opls/filtered_X'] = self._filtered_X
            file['/opls'].attrs['r_squared_X'] = self._r_squared_X
            file['/opls'].attrs['r_squared_Y'] = self._r_squared_Y
            file['/opls'].attrs['y_weights'] = self._y_weights
            file['/opls_cv/feature_p_values'] = self._feature_p_values
            file['/opls_cv/permuted_loadings'] = self._permuted_loadings
            file['/opls_cv'].attrs['q_squared_p_value'] = self._q_squared_p_value
            file['/opls_cv/permutation_q_squared'] = self._permutation_q_squared
            file['/opls_cv'].attrs['q_squared'] = self._q_squared

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

    def download_results(self,
                         include_feature_p_values=True,
                         include_coef=True,
                         include_scores=True,
                         include_orthogonal_scores=True,
                         include_r_squared=True,
                         include_loadings=True,
                         include_orthogonal_loadings=True,
                         include_weights=True,
                         include_orthogonal_weights=True,
                         file_formats=None):

        def _save_feature_p_values(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=self._feature_p_values,
                                  index=self._x,
                                  columns=['p_value'])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if '/opls/feature_p_value' in file:
                        del file['/opls/feature_p_value']
                    file['/opls/feature_p_value'] = self._feature_p_values

        def _save_coef(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=self._coef, index=self._x, columns=['coef'])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if '/opls/coef' in file:
                        del file['/opls/coef']
                    file['/opls/coef'] = self._coef

        def _save_scores(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame()
                df['x_scores'] = self._x_scores
                df['y_scores'] = self._y_scores
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if '/opls/x_scores' in file:
                        del file['/opls/x_scores']
                    if '/opls/y_scores' in file:
                        del file['/opls/y_scores']
                    file['x_scores'] = self._x_scores
                    file['y_scores'] = self._y_scores

        def _save_orthogonal_scores(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=self._orthogonal_x_scores,
                                  columns=[f'PC{i+1}' for i in range(0, self._orthogonal_x_scores.shape[0])])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    if '/opls/orthogonal_scores' in file:
                        del file['/opls/orthogonal_x_scores']
                    file['/opls/orthogonal_x_scores'] = self._orthogonal_x_scores

        def _save_r_squared(name, file_format):
            if file_format == 'csv':
                index = ['r_squared_Y', 'r_squared_X', 'q_squared', 'q_squared_p_value']
                values = [[self._r_squared_Y, None], [self._r_squared_X, None], [self._q_squared, self._q_squared_p_value]]
                if self._accuracy is not None:
                    index += ['accuracy', 'accuracy_p_value', 'roc_auc', 'roc_auc_p_value']
                    values += [[self._accuracy, self._accuracy_p_value], [self._roc_auc, self._roc_auc_p_value]]
                df = pd.DataFrame(data=values, index=index, columns=['value', 'p_value'])
                df.to_csv(name)
            else:
                with h5py.File(name) as file:
                    if '/opls' not in file:
                        file.create_group('/opls')
                    if '/opls_cv' not in file:
                        file.create_group('/opls_cv')
                    file['/opls'].attrs['r_squared_Y'] = self._r_squared_Y
                    file['/opls'].attrs['r_squared_X'] = self._r_squared_X
                    file['/opls_cv'].attrs['q_squared'] = self._q_squared
                    file['/opls_cv'].attrs['q_squared_p_value'] = self._q_squared_p_value
                    if self._accuracy is not None:
                        file['/opls_cv'].attrs['accuracy'] = self._accuracy
                        file['/opls_cv'].attrs['accuracy_p_value'] = self._accuracy_p_value
                        file['/opls_cv'].attrs['roc_auc'] = self._roc_auc
                        file['/opls_cv'].attrs['roc_auc_p_value'] = self._roc_auc_p_value

        self._accuracy = None
        self._permutation_accuracy = None
        self._accuracy_p_value = None
        self._roc_auc = None
        self._permutation_roc_auc = None
        self._roc_auc_p_value = None

        file_formats = file_formats or ['hdf5']


    def post_results(self, name, analysis_ids):
        self.load_data()
        filename = self.download_results(file_formats=['hdf5'])
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

    def fit(self,
            numeric_df,
            model_numeric_df,
            model_label_df,
            target=None,
            regression_type=None,
            multiclass_behavior=None,
            k=None,
            inner_alpha=0.2,
            outer_alpha=0.01,
            permutations=None,
            inner_permutations=None,
            outer_permutations=None):
        force_regression = regression_type.startswith('regression')
        opls_cv = OPLSValidator(k=k,
                                scale=False,
                                force_regression=force_regression,
                                n_permutations=permutations,
                                n_inner_permutations=inner_permutations,
                                n_outer_permutations=outer_permutations,
                                inner_alpha=inner_alpha,
                                outer_alpha=outer_alpha)

