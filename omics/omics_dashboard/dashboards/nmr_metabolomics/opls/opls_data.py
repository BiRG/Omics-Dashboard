import itertools
import os
import shutil
import traceback

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import h5py
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import scipy.stats as stats
from flask import url_for
from flask_login import current_user
from plotly.colors import DEFAULT_PLOTLY_COLORS
from pyopls import OPLSValidator, OPLS
from scipy.stats import gaussian_kde
from sklearn.metrics import auc
from sklearn.preprocessing import LabelBinarizer
from sklearn.utils import parallel_backend
from sklearn.utils.multiclass import type_of_target

from data_tools.access_wrappers.collections import upload_collection
from ..multivariate_analysis_data import MultivariateAnalysisData


class OPLSData(MultivariateAnalysisData):
    _empty_plot_data = {
        'score_plots': [],
    }
    _redis_prefix = 'opls'

    def __init__(self, load_data=False):
        super().__init__(load_data)
        # any of these can be None
        self.validators_ = []

    @staticmethod
    def _serialize_opls(filename, validator: OPLSValidator, name, description, pos_label, neg_label, target,
                        roc_curve=None, root_path='results'):
        with h5py.File(filename, 'r+') as file:
            if root_path not in file:
                file.create_group(root_path)
            if name in file[root_path]:
                del file[root_path][name]
            group = file[root_path].create_group(name)
            group.attrs['description'] = description
            group.attrs['pos_label'] = pos_label if pos_label is not None else ''
            group.attrs['neg_label'] = neg_label if neg_label is not None else ''
            group.attrs['k'] = validator.k
            group.attrs['n_permutations'] = validator.n_permutations
            group.attrs['n_inner_permutations'] = validator.n_inner_permutations
            group.attrs['n_outer_permutations'] = validator.n_outer_permutations
            group.attrs['inner_alpha'] = validator.inner_alpha
            group.attrs['outer_alpha'] = validator.outer_alpha
            group.attrs['n_components'] = validator.n_components_
            group.attrs['q_squared'] = validator.q_squared_
            group.attrs['q_squared_p_value'] = validator.q_squared_p_value_
            group.attrs['r_squared_Y'] = validator.r_squared_Y_
            group.attrs['r_squared_Y_p_value'] = validator.r_squared_Y_p_value_
            group.attrs['r_squared_X'] = validator.r_squared_X_
            group.attrs['r_squared_X_p_value'] = validator.r_squared_X_p_value_

            group.create_dataset('permutation_q_squared', data=validator.permutation_q_squared_)
            group.create_dataset('permutation_r_squared_Y', data=validator.permutation_r_squared_Y_)
            group.create_dataset('permutation_r_squared_X', data=validator.permutation_r_squared_X_)

            regressor_group = group.create_group('opls')
            regressor_group.attrs['r_squared_X_'] = validator.estimator_.r_squared_X_
            regressor_group.attrs['r_squared_Y_'] = validator.estimator_.r_squared_Y_
            regressor_group.attrs['y_weight'] = validator.estimator_.y_weights_
            regressor_group.create_dataset('orthogonal_x_weights', data=validator.estimator_.orthogonal_x_weights_)
            regressor_group.create_dataset('x_weights', data=validator.estimator_.x_weights_)
            regressor_group.create_dataset('orthogonal_x_loadings', data=validator.estimator_.orthogonal_x_loadings_)
            regressor_group.create_dataset('x_loadings_', data=validator.estimator_.x_loadings_)
            regressor_group.create_dataset('orthogonal_x_scores', data=validator.estimator_.orthogonal_x_scores_)
            regressor_group.create_dataset('x_scores', data=validator.estimator_.x_scores_)
            regressor_group.create_dataset('y_scores', data=validator.estimator_.y_scores_)
            regressor_group.create_dataset('coef', data=validator.estimator_.coef_)

            if validator.accuracy_ is not None:
                group.attrs['accuracy'] = validator.accuracy_
                group.attrs['accuracy_p_value'] = validator.accuracy_p_value_
                group.attrs['roc_auc'] = validator.roc_auc_
                group.attrs['roc_auc_p_value'] = validator.roc_auc_p_value_
                group.attrs['discriminator_q_squared'] = validator.discriminator_q_squared_
                group.attrs['discriminator_q_squared_p_value'] = validator.discriminator_q_squared_p_value_

                group.create_dataset('permutation_accuracy', data=validator.permutation_accuracy_)
                group.create_dataset('permutation_roc_auc', data=validator.permutation_roc_auc_)
                group.create_dataset('permutation_discriminator_q_squared',
                                     data=validator.permutation_discriminator_q_squared_)

                roc_group = group.create_group('roc_curve')
                fpr_group = roc_group.create_group('fpr')
                tpr_group = roc_group.create_group('tpr')
                threshold_group = roc_group.create_group('threshold')
                fprs, tprs, thresholds = roc_curve
                for i, fpr in enumerate(fprs):
                    fpr_group.create_dataset(str(i), fpr)
                for i, tpr in enumerate(tprs):
                    tpr_group.create_dataset(str(i), tpr)
                for i, threshold in enumerate(thresholds):
                    threshold_group.create_dataset(str(i), threshold)

        target.to_hdf(filename, f'/{root_path}/{name}/target')

    @staticmethod
    def _deserialize_opls(filename, name, root_path='results'):
        with h5py.File(filename, 'r') as file:
            group = file[root_path][name]
            validator = OPLSValidator(group.attrs['n_components'],
                                      group.attrs['k'],
                                      False,
                                      False,
                                      group.attrs['n_permutations'],
                                      group.attrs['n_inner_permutations'],
                                      group.attrs['n_outer_permutations'],
                                      group.attrs['inner_alpha'],
                                      group.attrs['outer_alpha'])

            validator.q_squared_ = group.attrs['q_squared']
            validator.q_squared_p_value_ = group.attrs['q_squared_p_value']
            validator.r_squared_Y_ = group.attrs['r_squared_Y']
            validator.r_squared_Y_p_value_ = group.attrs['r_squared_Y_p_value']
            validator.r_squared_X_ = group.attrs['r_squared_X']
            validator.r_squared_X_p_value_ = group.attrs['r_squared_X_p_value']

            validator.permutation_q_squared_ = np.array(group['permutation_q_squared'])
            validator.permutation_r_squared_Y_ = np.array(group['permutation_r_squared_Y'])
            validator.permutation_r_squared_X_ = np.array(group['permutation_r_squared_X'])

            regressor_group = group['opls']
            validator.estimator_ = OPLS(validator.n_components_, False)
            validator.estimator_.r_squared_X_ = np.array(regressor_group.attrs['r_squared_X_'])
            validator.estimator_.r_squared_Y_ = np.array(regressor_group.attrs['r_squared_Y_'])
            validator.estimator_.y_weights_ = np.array(regressor_group.attrs['y_weight'])
            validator.estimator_.orthogonal_x_weights_ = np.array(regressor_group['orthogonal_x_weights'])
            validator.estimator_.x_weights_ = np.array(regressor_group['x_weights'])
            validator.estimator_.orthogonal_x_loadings_ = np.array(regressor_group['orthogonal_x_loadings'])
            validator.estimator_.x_loadings_ = np.array(regressor_group['x_loadings_'])
            validator.estimator_.orthogonal_x_scores_ = np.array(regressor_group['orthogonal_x_scores'])
            validator.estimator_.x_scores_ = np.array(regressor_group['x_scores'])
            validator.estimator_.y_scores_ = np.array(regressor_group['y_scores'])
            validator.estimator_.coef_ = np.array(regressor_group['coef'])

            if validator.accuracy_ is not None:
                pos_label = group.attrs['pos_label']
                neg_label = group.attrs['neg_label']
                validator.accuracy_ = group.attrs['accuracy']
                validator.accuracy_p_value_ = group.attrs['accuracy_p_value']
                validator.roc_auc_ = group.attrs['roc_auc']
                validator.roc_auc_p_value_ = group.attrs['roc_auc_p_value']
                validator.discriminator_q_squared_ = group.attrs['discriminator_q_squared']
                validator.discriminator_q_squared_p_value_ = group.attrs['discriminator_q_squared_p_value']

                group.attrs['negative_label'] = validator.binarizer_.classes_[0]
                group.attrs['positive_label'] = validator.binarizer_.classes_[1]

                validator.permutation_accuracy_ = np.array(group['permutation_accuracy'])
                validator.permutation_roc_auc_ = np.array(group['permutation_roc_auc'])
                validator.permutation_discriminator_q_squared_ = np.array(group['permutation_discriminator_q_squared'])

                roc_group = group['roc_curve']
                fpr_group = roc_group['fpr']
                tpr_group = roc_group['tpr']
                threshold_group = roc_group['threshold']
                fprs = [np.array(dset) for dset in fpr_group.values()]
                tprs = [np.array(dset) for dset in tpr_group.values()]
                thresholds = [np.array(dset) for dset in threshold_group.values()]
                roc_curve = fprs, tprs, thresholds
            else:
                roc_curve = None
                pos_label = None
            description = group.description

        return {
            'validator': validator,
            'name': name,
            'description': description,
            'target': pd.read_hdf(filename, f'/{root_path}/{name}/target'),
            'pos_label': pos_label,
            'neg_label': neg_label,
            'roc_curve': roc_curve
        }

    def load_results(self):
        super().load_results()
        with h5py.File(self._results_filename, 'r') as file:
            validator_names = [name for name in file['results']] if 'results' in file else None
        self.validators_ = [self._deserialize_opls(self._results_filename, name)
                            for name in file['results']] if validator_names else []
        self.load_labels()

    def save_results(self, filename=None, file_format='h5'):
        if not filename:
            filename = self._results_filename
        root_path = '/results' if filename == self._results_filename else '/'
        super().save_results(filename, file_format)
        for validator in self.validators_:
            self._serialize_opls(filename, root_path=root_path, **validator)

    def load_data(self):
        self.load_results()
        self.load_dataframes()

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
                df = pd.DataFrame(data=np.column_stack([validator['validator'].feature_p_values_
                                                        for validator in self.validators_]),
                                  columns=[validator['name'] for validator in self.validators_],
                                  index=self._x)
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        if 'feature_p_values' in validator_group:
                            del validator_group['feature_p_values']
                        validator_group.create_dataset('feature_p_values',
                                                       data=validator['validator'].feature_p_values_)

        def _save_coef(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=np.hstack([validator['validator'].coef_ for validator in self.validators_]),
                                  index=self._x,
                                  columns=[f'coef_{validator["name"]}' for validator in self.validators_])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        if 'coef' in validator_group:
                            del validator_group['coef']
                        validator_group.create_dataset('coef', data=validator['validator'].coef_)

        def _save_scores(name, file_format):
            if file_format == 'csv':
                columns = [(f'{validator["name"]}_X_score', f'{validator["name"]}_Y_score')
                           for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([np.hstack([validator.x_scores_, validator.y_scores_])
                                                  for validator in self.validators_]),
                                  columns=[item for sublist in columns for item in sublist])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        if 'y_scores' in validator_group:
                            del validator_group['y_scores']
                        if 'x_scores' in validator_group:
                            del validator_group['x_scores']
                        validator_group.create_dataset('y_scores', data=validator['validator'].y_scores_)
                        validator_group.create_dataset('x_scores', data=validator['validator'].x_scores_)

        def _save_orthogonal_scores(name, file_format):
            if file_format == 'csv':
                columns = [[f'{validator["name"]}_{i}'
                            for i in range(validator['validator'].orthogonal_x_scores_.shape[1])]
                           for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([validator.orthogonal_x_scores_ for validator in self.validators_]),
                                  columns=[item for sublist in columns for item in sublist])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        if 'orthogonal_x_scores' in validator_group:
                            del validator_group['orthogonal_x_scores']
                        validator_group.create_dataset('orthogonal_x_scores',
                                                       data=validator['validator'].orthogonal_x_scores_)

        def _save_r_squared(name, file_format):
            if file_format == 'csv':
                columns = ['r_squared_Y', 'r_squared_Y_p_value', 'r_squared_X', 'r_squared_X_p_value',
                           'q_squared', 'q_squared_p_value']
                values = [[validator.r_squared_Y_, validator.r_squared_Y_p_value_,
                           validator.r_squared_X_, validator.r_squared_X_p_value_,
                           validator.q_squared_, validator.q_squared_p_value_]
                          for validator in self.validators_]
                if len(self.validators_) > 1:
                    columns += ['accuracy', 'accuracy_p_value',
                                'roc_auc', 'roc_auc_p_value',
                                'dq_squared', 'dq_squared_p_value']
                    values = [row + [validator['validator'].accuracy_, validator['validator'].accuracy_p_value_,
                                     validator['validator'].roc_auc_, validator['validator'].roc_auc_p_value_,
                                     validator['validator'].discriminator_q_squared_,
                                     validator['validator'].discriminator_q_squared_p_value_]
                              for row, validator in zip(values, self.validators_)]
                df = pd.DataFrame(data=values,
                                  index=[validator['name'] for validator in self.validators_],
                                  columns=['value', 'p_value'])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        validator_group.attrs['r_squared_Y'] = validator['validator'].r_squared_Y_
                        validator_group.attrs['r_squared_X'] = validator['validator'].r_squared_X_
                        validator_group.attrs['r_squared_Y_p_value'] = validator['validator'].r_squared_Y_p_value_
                        validator_group.attrs['r_squared_X_p_value'] = validator['validator'].r_squared_X_p_value_
                        validator_group.attrs['q_squared'] = validator['validator'].q_squared_
                        validator_group.attrs['q_squared_p_value'] = validator['validator'].q_squared_p_value_
                        if len(self.validators_) > 1:
                            validator_group.attrs['accuracy'] = validator['validator'].accuracy_
                            validator_group.attrs['accuracy_p_value'] = validator['validator'].accuracy_p_value_
                            validator_group.attrs['roc_auc'] = validator['validator'].roc_auc_
                            validator_group.attrs['roc_auc_p_value'] = validator['validator'].roc_auc_p_value_
                            validator_group.attrs['discriminator_q_squared'] = validator[
                                'validator'].discriminator_q_squared_
                            validator_group.attrs['discriminator_q_squared_p_value'] = validator[
                                'validator'].discriminator_q_squared_p_value_

        def _save_loadings(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=np.column_stack([validator['validator'].x_loadings_
                                                        for validator in self.validators_]),
                                  index=[validator['name'] for validator in self.validators_],
                                  columns=self._x)
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        validator_group.create_dataset('x_loadings', data=validator['validator'].x_loadings_)

        def _save_orthogonal_loadings(name, file_format):
            if file_format == 'csv':
                index = [[f'{validator["name"]}_{i + 1}' for i in range(validator['validator'].n_components)]
                         for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([validator['validator'].orthogonal_x_loadings_
                                                  for validator in self.validators_]).T,
                                  index=[item for sublist in index for item in sublist],
                                  columns=self._x)
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        validator_group.create_dataset('orthogonal_x_loadings',
                                                       data=validator['validator'].orthogonal_x_loadings_)

        def _save_weights(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=np.hstack([validator['validator'].x_weights_
                                                  for validator in self.validators_]).T,
                                  columns=self._x,
                                  index=[validator['name'] for validator in self.validators_])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        validator_group.create_dataset('x_weights',
                                                       data=validator['validator'].x_weights_)

        def _save_orthogonal_weights(name, file_format):
            if file_format == 'csv':
                index = [[f'{validator["name"]}_{i + 1}' for i in range(validator['validator'].n_components)]
                         for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([validator['validator'].orthogonal_x_weights_
                                                  for validator in self.validators_]).T,
                                  columns=self._x,
                                  index=[item for sublist in index for item in sublist])
                df.to_csv(name)
            else:
                with h5py.File(name, 'a') as file:
                    for validator in self.validators_:
                        if validator['name'] not in file:
                            validator_group = file.create_group(validator['name'])
                        else:
                            validator_group = file[validator['name']]
                        validator_group.create_dataset('orthogonal_x_weights',
                                                       data=validator['validator'].orthogonal_x_weights_)

        file_formats = file_formats or ['h5']
        self.load_data()
        multiple_results = [
                               include_feature_p_values,
                               include_coef,
                               include_scores,
                               include_orthogonal_scores,
                               include_r_squared,
                               include_loadings,
                               include_orthogonal_loadings,
                               include_weights,
                               include_orthogonal_weights,
                           ].count(True) > 1
        create_archive = len(file_formats) > 1 or (multiple_results and 'csv' in file_formats)
        if len(self._loaded_collection_ids) > 1:
            root_filename = f'opls_collections_{"_".join([str(i) for i in self._loaded_collection_ids])}'
        else:
            root_filename = f'opls_collections_{self._loaded_collection_ids[0]}'
        root_dir = os.path.dirname(self._results_filename)
        results_dir = os.path.join(root_dir, root_filename)
        if os.path.isdir(results_dir):
            shutil.rmtree(results_dir)
        elif os.path.isfile(results_dir):
            os.remove(results_dir)
        os.mkdir(results_dir)
        filenames = [os.path.join(results_dir, f'{root_filename}.{file_format}') for file_format in file_formats]
        for filename, file_format in zip(filenames, file_formats):
            if include_feature_p_values:
                _save_feature_p_values(filename, file_format)
                if not create_archive:
                    return filename
            if include_coef:
                _save_coef(filename, file_format)
                if not create_archive:
                    return filename
            if include_scores:
                _save_scores(filename, file_format)
                if not create_archive:
                    return filename
            if include_orthogonal_scores:
                _save_orthogonal_scores(filename, file_format)
                if not create_archive:
                    return filename
            if include_r_squared:
                _save_r_squared(filename, file_format)
                if not create_archive:
                    return filename
            if include_loadings:
                _save_loadings(filename, file_format)
                if not create_archive:
                    return filename
            if include_orthogonal_loadings:
                _save_orthogonal_loadings(filename, file_format)
                if not create_archive:
                    return filename
            if include_weights:
                _save_weights(filename, file_format)
                if not create_archive:
                    return filename
            if include_orthogonal_weights:
                _save_orthogonal_weights(filename, file_format)
                if not create_archive:
                    return filename
        return shutil.make_archive(results_dir, 'zip', root_dir, root_filename)

    def post_results(self, name, analysis_ids):
        self.load_data()
        if len(self._loaded_collection_ids) > 1:
            filename = f'/tmp/opls_collections_{"_".join([str(i) for i in self._loaded_collection_ids])}.h5'
        else:
            filename = f'/tmp/opls_collections_{self._loaded_collection_ids[0]}.h5'
        with h5py.File(self._results_filename) as file, h5py.File(filename, 'w') as new_file:
            results_group = file['results']
            for child in results_group:
                results_group.copy(child, new_file)
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
            min_n_components=None,
            k=None,
            inner_alpha=0.2,
            outer_alpha=0.01,
            permutations=None,
            inner_permutations=None,
            outer_permutations=None):
        print('fit()')
        force_regression = regression_type and regression_type.startswith('regression')
        print(f'force_regression: {force_regression}')
        targets = []
        is_discrimination = type_of_target(model_label_df[target]).startswith('multiclass') and not force_regression
        if is_discrimination:
            print('is_discrimination')
            if 'one_v_all' in multiclass_behavior:
                print('one-v-alls')
                for unique_val in pd.unique(model_label_df[target]):
                    target_column = model_label_df[target].copy()
                    target_column[target_column != unique_val] = f'not_{unique_val}'
                    targets.append(
                        {
                            'name': f'{unique_val}_vs_all',
                            'description': f'{unique_val} vs. All',
                            'target': target_column,
                            'pos_label': unique_val
                        }
                    )
            if 'one_v_one' in multiclass_behavior:
                for first, second in itertools.combinations(pd.unique(model_label_df[target]), 2):
                    target_column = model_label_df.query(f'({target}=="{first}") | ({target}=="{second}")')[target]
                    targets.append(
                        {
                            'name': f'{first}_vs_{second}',
                            'description': f'{first} vs. {second}',
                            'target': target_column,
                            'pos_label': first,
                            'neg_label': second
                        }
                    )
        else:
            targets = [
                {
                    'name': target,
                    'description': target,
                    'target': model_label_df[target].copy(),
                    'pos_label': None,
                    'neg_label': None
                }
            ]
        for target_ in targets:
            print('create validator')
            validator = OPLSValidator(min_n_components, k, False, force_regression,
                                      permutations, inner_permutations, outer_permutations,
                                      inner_alpha, outer_alpha)
            print('append validator')
            try:
                with parallel_backend('threading', n_jobs=-1):
                    validator.fit(model_numeric_df.loc[target_['target'].index],
                                  target_['target'], pos_label=target_['pos_label']),

                    roc_curve = validator.cross_val_roc_curve(model_numeric_df.loc[target_['target'].index],
                                                              target_['target']) if is_discrimination else None
            except Exception as e:
                traceback.print_exc()
            self.validators_.append(
                {
                    'validator': validator,
                    'roc_curve': roc_curve,
                    **target_
                }
            )
        self.save_results()

    def type_of_target_(self, target):
        self.load_data()
        return type_of_target(self._label_df[target])

    @staticmethod
    def _get_kde(arr):
        x = np.linspace(-1.25 * arr.min(), 1.25 * arr.max(), 2 * arr.size)
        y = gaussian_kde(np.ravel(arr))(x)
        return x, y

    def _get_loading_kde(self, validator_ind, feature_ind):
        loadings = self.validators_[validator_ind]['validator'].permutation_loadings_[:, feature_ind]
        return self._get_kde(loadings)

    def get_loading_significance_plot(self, validator_ind, feature_ind, theme):
        x, y = self._get_loading_kde(validator_ind, feature_ind)
        validator: OPLSValidator = self.validators_[validator_ind]['validator']
        title = f'{self._x[feature_ind]} (p={validator.feature_p_values_[feature_ind]})'
        point_graph = go.Scatter(
            x=np.ravel(validator.permutation_loadings_[:, feature_ind]),
            y=[0 for _ in range(validator.permutation_loadings_.shape[0])],
            text=f'Values',
            name=f'Values',
            mode='markers',
            marker={
                'size': 5,
                'opacity': 1,
                'line': {'width': 0.5, 'color': 'white'},
                'color': 'black',
                'symbol': 'cross'
            }
        )
        kde_graph = go.Scatter(
            x=x,
            y=y,
            mode='lines',
            name='KDE'
        )

        annotations = [
            {
                'x': validator.estimator_.x_loadings_[feature_ind, 0],
                'xref': 'x',
                'text': f'{validator.estimator_.x_loadings_[feature_ind, 0]}',
                'showarrow': True
            }
        ]
        theme = theme or 'plotly_white'
        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }
        layout = go.Layout(
            height=700,
            template=theme,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title=title,
            xaxis={
                'title': f'Loading values',
                **axis_line_style
            },
            yaxis={
                'title': 'Estimated Density',
                **axis_line_style
            },
            annotations=annotations
        )
        return dcc.Graph(figure={'data': [point_graph, kde_graph], 'layout': layout})

    def get_summary_table(self):
        tables = []
        for validator in self.validators_:
            tables.append(html.H5(validator['description']))
            index = [
                'Components',
                'R\u00B2Y',
                'R\u00B2X',
                'Q\u00B2Y',
            ]
            if len(self.validators_) > 1:
                index += [
                    'DQ\u00B2Y',
                    'Accuracy',
                    'ROC Area Under Curve'
                ]
            df = pd.DataFrame(index=index)
            metric_values = [validator.n_components_, validator.r_squared_Y_,
                             validator.r_squared_X_, validator.q_squared_]
            if len(self.validators_) > 1:
                index += [
                    validator.discriminator_q_squared_,
                    validator.accuracy_,
                    validator.roc_auc_
                ]
            df['Metric'] = metric_values
            p_values = [None, validator.r_squared_Y_p_value_,
                        validator.r_squared_X_p_value_, validator.q_squared_p_value_]
            if len(self.validators_) > 1:
                index += [
                    validator.discriminator_q_squared_p_value_,
                    validator.accuracy_p_value_,
                    validator.roc_auc_p_value_
                ]
            df['p Values'] = p_values
            tables.append(dash_table.DataTable(id=f'{validator["name"]}-summary',
                                               columns=[{'name': i, 'id': i} for i in df.columns],
                                               data=df.to_dict('records')))
        return tables

    def get_plots(self, theme):
        print('OPLSData.get_plots()')
        theme = theme or 'plotly_white'
        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }

        def _get_scores_plot(validator: OPLSValidator, target, name):
            print('get_scores_plot')
            color = [DEFAULT_PLOTLY_COLORS[val[0]] for val in LabelBinarizer(0, 1).fit_transform(target)]
            graph_data = go.Scatter(
                x=validator.estimator_.x_scores_,
                y=validator.estimator_.orthogonal_x_scores_[:, 0],
                mode='markers',
                marker={
                    'size': 15,
                    'opacity': 0.5,
                    'line': {'width': 0.5, 'color': 'white'},
                    'color': color
                }
            )
            layout = go.Layout(
                height=700,
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title=f'Scores ({name})',
                xaxis={
                    'title': f't',
                    **axis_line_style
                },
                yaxis={
                    'title': f't_ortho',
                    **axis_line_style
                }
            )
            return dcc.Graph(figure={
                'data': graph_data,
                'layout': layout
            })

        def _get_loadings_plot(validator: OPLSValidator, name):
            print('get_loadings_plot')
            graph_data = go.Scatter(
                x=self._x,
                y=validator.estimator_.x_loadings_,
                mode='markers',
                marker={
                    'size': 15,
                    'opacity': 0.5,
                    'line': {'width': 0.5, 'color': 'white'}
                }
            )

            layout = go.Layout(
                height=700,
                template=theme,
                title=f'Loadings ({name})',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis={
                    'title': f'Loading',
                    **axis_line_style
                },
                yaxis={
                    'title': f'Chemical Shift (ppm)',
                    **axis_line_style
                }
            )
            return dcc.Graph(figure={
                'data': graph_data,
                'layout': layout
            })

        def _get_metric_plot(true_metric, perm_metric, metric_name, p_value, name):
            print('get_metric_plot')
            title = f'{metric_name} ({name}, p={p_value})'
            x, y = self._get_kde(perm_metric)
            point_graph = go.Scatter(
                x=np.ravel(perm_metric),
                y=[0 for _ in range(perm_metric.size)],
                text=metric_name,
                name=metric_name,
                mode='markers',
                marker={
                    'size': 5,
                    'opacity': 1,
                    'line': {'width': 0.5, 'color': 'white'},
                    'color': 'black',
                    'symbol': 'cross'
                }
            )
            density_graph = go.Scatter(
                x=x,
                y=y,
                text='Density',
                name='Density',
                mode='line'
            )
            annotations = [
                {
                    'x': true_metric,
                    'xref': 'x',
                    'text': f'{true_metric}',
                    'showarrow': True
                }
            ]

            layout = go.Layout(
                height=700,
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title=title,
                xaxis={
                    'title': f'Loading values',
                    **axis_line_style
                },
                yaxis={
                    'title': 'Estimated Density',
                    **axis_line_style
                },
                annotations=annotations
            )

            return dcc.Graph(figure={'data': [point_graph, density_graph], 'layout': layout})

        def _get_q_squared_plot(validator: OPLSValidator, name):
            print('get_q_squared_plot')
            return _get_metric_plot(validator.q_squared_, validator.permutation_q_squared_,
                                    'Q\u00B2', validator.q_squared_p_value_, name)

        def _get_r_squared_Y_plot(validator: OPLSValidator, name):
            print('get_r_squared_Y_plot')
            return _get_metric_plot(validator.r_squared_Y_, validator.permutation_r_squared_Y_,
                                    'R\u00B2Y', validator.r_squared_Y_p_value_, name)

        def _get_r_squared_X_plot(validator: OPLSValidator, name):
            print('get_r_squared_X_plot')
            return _get_metric_plot(validator.r_squared_X_, validator.permutation_r_squared_X_,
                                    'R\u00B2X', validator.r_squared_X_p_value_, name)

        def _get_dq_squared_plot(validator: OPLSValidator, name):
            print('get_dq_squared_plot')
            return _get_metric_plot(validator.discriminator_q_squared_, validator.permutation_discriminator_q_squared_,
                                    'DQ\u00B2Y', validator.discriminator_q_squared_p_value_, name)

        def _get_accuracy_plot(validator: OPLSValidator, name):
            print('get_accuracy_plot')
            return _get_metric_plot(validator.accuracy_, validator.permutation_accuracy_,
                                    'Accuracy', validator.accuracy_p_value_, name)

        def _get_roc_auc_plot(validator: OPLSValidator, name):
            print('get_roc_auc_plot')
            return _get_metric_plot(validator.roc_auc_, validator.permutation_roc_auc_,
                                    'ROC Area Under Curve', validator.roc_auc_p_value_, name)

        def _get_roc_plot(roc_curve, name):
            print('get_roc_plot')

            def _impute_values(val, n_rows):
                imputed = np.resize(val, (n_rows,))
                imputed[val.size:] = val[val.size - 1]
                return imputed

            title = f'Receiver operating characteristic ({name})'
            fprs, tprs, thresholds = roc_curve
            max_size = max([fpr.size for fpr in fprs])

            imputed_fprs = []
            imputed_tprs = []
            imputed_thresholds = []
            aucs = []

            layout = go.Layout(
                height=700,
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title=title,
                xaxis={
                    'title': f'Loading values',
                    **axis_line_style
                },
                yaxis={
                    'title': 'Estimated Density',
                    **axis_line_style
                },
            )
            figure = go.Figure(layout=layout)

            for i, (fpr, tpr, threshold) in enumerate(zip(roc_curve)):
                imputed_fprs.append(_impute_values(fpr, max_size))
                imputed_tprs.append(_impute_values(tpr, max_size))
                imputed_thresholds.append(_impute_values(threshold, max_size))
                area_under_curve = auc(fpr, tpr)
                aucs.append(area_under_curve)
                figure.add_trace(
                    go.Scatter(x=fpr, y=tpr, mode='lines+markers', name=f'ROC fold {i} (AUC={area_under_curve})',
                               opacity=0.35)
                )
            figure.add_trace(
                go.Scatter(x=[0, 1], y=[0, 1], mode='lines', line={'dash': 'dashdot'}, name='Chance')
            )
            mean_fpr = np.mean(np.row_stack(imputed_fprs), axis=0)
            mean_tpr = np.mean(np.row_stack(imputed_tprs), axis=0)
            sem_tpr = stats.sem(np.row_stack(imputed_tprs), axis=0)
            mean_auc = auc(mean_fpr, mean_tpr)
            sem_auc = stats.sem(aucs)

            figure.add_trace(
                go.Scatter(x=mean_fpr, y=mean_tpr,
                           mode='lines+markers', name=f'Mean ROC (AUC={mean_auc} \u00B1 {sem_auc}', opacity=0.95)
            )

            figure.add_trace(
                go.Scatter(x=mean_fpr, y=mean_tpr - sem_tpr,
                           mode='lines', marker={'color': '#444'}, line={'width': 0}, stackgroup='error',
                           name='Std. Err.')

            )
            figure.add_trace(
                go.Scatter(x=mean_fpr, y=mean_tpr + sem_tpr,
                           mode='lines', marker={'color': '#444'}, line={'width': 0},
                           fillcolor='rgba(68, 68, 68, 0.25)', fill='tonexty', stackgroup='error', showlegend=False)
            )

            return dcc.Graph(figure=figure)

        print('load_results()')
        self.load_results()
        print('results loaded')
        graphs = []
        print(self.validators_)
        for val in self.validators_:
            graphs += [
                _get_scores_plot(val['validator'], val['name'], val['target']),
                _get_loadings_plot(val['validator'], val['name']),
                _get_q_squared_plot(val['validator'], val['name']),
                _get_r_squared_Y_plot(val['validator'], val['name']),
                _get_r_squared_X_plot(val['validator'], val['name']),
            ]
            if len(self.validators_) > 1:
                graphs += [
                    _get_dq_squared_plot(val['validator'], val['name']),
                    _get_accuracy_plot(val['validator'], val['name']),
                    _get_roc_auc_plot(val['validator'], val['name']),
                    _get_roc_plot(val['roc_curve'], val['name'])
                ]
        return graphs
