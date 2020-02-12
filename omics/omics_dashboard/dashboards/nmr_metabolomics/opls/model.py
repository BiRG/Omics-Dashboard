import os
import re
import shutil
import tempfile
from typing import List, Union

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
from flask_login import current_user
from plotly.colors import DEFAULT_PLOTLY_COLORS
from pyopls import OPLSValidator, OPLS
from scipy.stats import gaussian_kde
from sklearn.cross_decomposition import PLSRegression
from sklearn.utils.multiclass import type_of_target

import config.redis_config as rds
from dashboards.dashboard_model import save_figures
from data_tools.wrappers.collections import get_collection, create_collection
from data_tools.wrappers.jobserver_control import start_job
from config.config import TMPDIR
from helpers import get_item_link
from .workflow import workflow
from ..multivariate_analysis_model import MultivariateAnalysisModel


class OPLSModel(MultivariateAnalysisModel):
    _empty_plot_data = {
        'score_plots': [],
    }
    redis_prefix = 'opls'

    def __init__(self, load_data=False):
        # any of these can be None
        super().__init__(load_data)
        self.validators_ = []

    @property
    def results_filename(self):
        if self.results_collection_id is not None:
            try:
                return get_collection(current_user, self.results_collection_id).filename
            except:
                return None
        return None

    @property
    def results_collection_id(self):
        try:
            return msgpack.loads(rds.get_value(f'{self.redis_prefix}_results_collection_id'))
        except:
            return None

    @results_collection_id.setter
    def results_collection_id(self, value):
        rds.set_value(f'{self.redis_prefix}_results_collection_id', msgpack.dumps(value))

    @property
    def job_id(self):
        try:
            return rds.get_value(f'{self.redis_prefix}_job_id')
        except:
            return None

    @job_id.setter
    def job_id(self, value):
        rds.set_value(f'{self.redis_prefix}_job_id', value)

    @property
    def root_dir(self):
        try:
            return os.path.dirname(self.results_filename)
        except:
            return TMPDIR

    @property
    def results_file_ready(self):
        if self.results_collection_id is not None:
            try:
                return len(h5py.File(self.results_filename).keys()) > 0
            except:
                return False

    def get_collections(self, collection_ids: Union[List[int], int]):
        super().get_collections(collection_ids)
        self.job_id = None
        self.results_collection_id = None

    def get_results_collection(self, collection_id):
        self.results_collection_id = collection_id

    @staticmethod
    def _deserialize_opls(filename, name, root_path='/'):
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
            validator.r_squared_X_ = group.attrs['r_squared_X']

            validator.permutation_q_squared_ = np.array(group['permutation_q_squared'])

            opls_group = group['opls']
            validator.opls_ = OPLS(validator.n_components_, False)
            validator.opls_.P_ortho_ = np.array(opls_group['P_ortho'])
            validator.opls_.T_ortho_ = np.array(opls_group['T_ortho'])
            validator.opls_.W_ortho_ = np.array(opls_group['W_ortho'])

            pls_group = group['pls']

            validator.pls_ = PLSRegression(1)
            validator.pls_.coef_ = np.array(pls_group['coef'])
            validator.pls_.n_iter_ = np.array(pls_group['n_iter'])
            validator.pls_.x_loadings_ = np.array(pls_group['x_loadings'])
            validator.pls_.x_rotations_ = np.array(pls_group['x_rotations'])
            validator.pls_.x_scores_ = np.array(pls_group['x_scores'])
            validator.pls_.x_weights_ = np.array(pls_group['x_weights'])
            validator.pls_.y_rotations_ = np.array(pls_group['y_rotations'])
            validator.pls_.y_scores_ = np.array(pls_group['y_scores'])
            validator.pls_.y_weights_ = np.array(pls_group['y_weights'])

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
            description = group.description

        return {
            'validator': validator,
            'name': name,
            'description': description,
            'target': pd.read_hdf(filename, f'/{root_path}/{name}/target'),
            'pos_label': pos_label,
            'neg_label': neg_label
        }

    def load_results(self):
        if self.results_file_ready:
            super().load_results()
            with h5py.File(self.results_filename, 'r') as file:
                validator_names = [name for name in file.keys()]
            self.validators_ = [self._deserialize_opls(self.results_filename, name)
                                for name in validator_names] if validator_names else []
            self.load_labels()

    def save_results(self, filename=None, file_format='h5'):
        raise NotImplementedError()  # this whole inheritance thing is a kluge that an undergrad can fix later :)

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
                df = pd.DataFrame(data=np.hstack([validator['validator'].pls_.coef_ for validator in self.validators_]),
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
                        validator_group.create_dataset('coef', data=validator['validator'].pls_.coef_)

        def _save_scores(name, file_format):
            if file_format == 'csv':
                columns = [(f'{validator["name"]}_X_score', f'{validator["name"]}_Y_score')
                           for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([np.hstack([validator.pls_.x_scores_, validator.pls_.y_scores_])
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
                        validator_group.create_dataset('y_scores', data=validator['validator'].pls_.y_scores_)
                        validator_group.create_dataset('x_scores', data=validator['validator'].pls_.x_scores_)

        def _save_orthogonal_scores(name, file_format):
            if file_format == 'csv':
                columns = [[f'{validator["name"]}_{i}'
                            for i in range(validator['validator'].opls_.T_ortho_.shape[1])]
                           for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([validator.opls_.T_ortho_ for validator in self.validators_]),
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
                                                       data=validator['validator'].opls_.T_ortho_)

        def _save_r_squared(name, file_format):
            if file_format == 'csv':
                columns = ['r_squared_Y', 'r_squared_X', 'q_squared', 'q_squared_p_value']
                values = [[validator.r_squared_Y_, np.nan,
                           validator.r_squared_X_, np.nan,
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
                df = pd.DataFrame(data=np.column_stack([validator['validator'].pls_.x_loadings_
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
                        validator_group.create_dataset('x_loadings', data=validator['validator'].pls_.x_loadings_)

        def _save_orthogonal_loadings(name, file_format):
            if file_format == 'csv':
                index = [[f'{validator["name"]}_{i + 1}' for i in range(validator['validator'].n_components)]
                         for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([validator['validator'].opls_.P_ortho_
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
                                                       data=validator['validator'].opls_.P_ortho_)

        def _save_weights(name, file_format):
            if file_format == 'csv':
                df = pd.DataFrame(data=np.hstack([validator['validator'].pls_.x_weights_
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
                                                       data=validator['validator'].pls_.x_weights_)

        def _save_orthogonal_weights(name, file_format):
            if file_format == 'csv':
                index = [[f'{validator["name"]}_{i + 1}' for i in range(validator['validator'].n_components)]
                         for validator in self.validators_]
                df = pd.DataFrame(data=np.hstack([validator['validator'].opls_.W_ortho_
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
                                                       data=validator['validator'].opls_.W_ortho_)

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
        root_dir = os.path.dirname(self.results_filename)
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
        raise NotImplementedError()

    def perform_analysis(self, **kwargs):
        raise NotImplementedError()

    def fit(self, **kwargs):
        raise NotImplementedError()

    def submit_job(self,
                   model_by: str = None,
                   ignore_by: str = None,
                   scale_by: str = None,
                   pair_on: List[str] = None,
                   pair_with: str = None,
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
        multiclass_behavior = multiclass_behavior or []
        force_regression = regression_type and regression_type.startswith('regression')
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

        collection_metadata = {
            'name': name,
            'description': description,
            'owner': current_user,
            'user_group': current_user.primary_user_group,
            'group_can_read': True,
            'group_can_write': False,
            'all_can_read': False,
            'all_can_write': False,
            'parent_id': self._loaded_collection_ids[0],
            'kind': 'results'
        }

        results_collection = create_collection(current_user, [], collection_metadata)
        self.results_collection_id = results_collection.id
        job_params = {
            'collection_id': self._loaded_collection_ids[0],
            'ignore_by_query': ignore_by,
            'model_by_query': model_by,
            'pair_on_label': pair_on,
            'pair_with_query': pair_with,
            'scale_by_query': scale_by,
            'metric_test_permutations': permutations,
            'min_n_components': min_n_components,
            'outer_test_alpha': outer_alpha,
            'outer_test_permutations': outer_permutations,
            'target': target,
            'k': k,
            'inner_test_permutations': inner_permutations,
            'inner_test_alpha': inner_alpha,
            'one_v_one': 'one_v_one' in multiclass_behavior,
            'one_v_all': 'one_v_all' in multiclass_behavior,
            'results_collection_id': self.results_collection_id,
            'force_regression': force_regression
        }
        job = start_job(workflow, job_params, current_user, 'analysis')
        self.job_id = job.id
        message_children = [
            html.Strong('Job submitted.'),
            html.Br(),
            html.Strong('Job: '), html.A(f'{job.id}', href=get_item_link(job), target='_blank'),
            html.Br(),
            html.Strong('Results collection: '), html.A(f'Collection {results_collection.id}',
                                                        href=get_item_link(results_collection),
                                                        target='_blank')
        ]
        return html.P(message_children), name, 'success'

    def type_of_target_(self, target):
        self.load_dataframes()
        return type_of_target(self._label_df[target])

    def get_summary_table(self, group_key, theme=None):
        is_discrimination = 'accuracy' in h5py.File(self.results_filename)[group_key].attrs
        description = h5py.File(self.results_filename)[group_key].attrs['description']
        theme, style_header, style_cell = self._get_table_styles(theme)

        index = [
            'Components',
            'R\u00B2Y',
            'R\u00B2X',
            'Q\u00B2Y',
        ]
        if is_discrimination:
            index += [
                'DR\u00B2Y',
                'DQ\u00B2Y',
                'Accuracy',
                'ROC Area Under Curve',
                'Positive Value',
                'Negative Value'
            ]

        with h5py.File(self.results_filename, 'r') as file:
            metric_values = [
                file[group_key].attrs['n_components'],
                f"{file[group_key].attrs['r_squared_Y']:.7f}",
                f"{file[group_key].attrs['r_squared_X']:.7f}",
                f"{file[group_key].attrs['q_squared']:.7f}"
            ]
            metric_p_values = [
                None,
                None,
                None,
                f"{file[group_key].attrs['q_squared_p_value']:.7f}"
            ]
            if is_discrimination:
                metric_values += [
                    f"{file[group_key].attrs['discriminant_r_squared']:.7f}",
                    f"{file[group_key].attrs['discriminant_q_squared']:.7f}",
                    f"{file[group_key].attrs['accuracy']:.7f}",
                    f"{file[group_key].attrs['roc_auc']:.7f}",
                    file[group_key].attrs['pos_label'],
                    file[group_key].attrs['neg_label']
                ]
                metric_p_values += [
                    None,
                    f"{file[group_key].attrs['discriminant_q_squared_p_value']:.7f}",
                    f"{file[group_key].attrs['accuracy_p_value']:.7f}",
                    f"{file[group_key].attrs['roc_auc_p_value']:.7f}",
                    None,
                    None
                ]

        df = pd.DataFrame(index=index)
        df['Metric'] = index
        df['Value'] = metric_values
        df['p Value'] = metric_p_values
        tag_id = re.sub(r'[^a-zA-Z\d]', '', group_key.lower()) + '-summary'
        return html.Div([
            dbc.Row(html.H5(description)),
            dbc.Row(
                dash_table.DataTable(id=tag_id,
                                     columns=[{'name': i, 'id': i} for i in df.columns],
                                     data=df.to_dict('records'),
                                     style_header=style_header,
                                     style_cell=style_cell,
                                     style_cell_conditional=[
                                         {
                                             'if': {'column_id': c},
                                             'textAlign': 'left',
                                             'font-family': 'sans'
                                         } for c in ['Metric']
                                     ]),
                className='container text-center',
                id=group_key
            ),
            html.Br()
        ])

    def get_summary_tables(self, theme=None):
        if self.results_file_ready:
            return [self.get_summary_table(key, theme) for key in h5py.File(self.results_filename).keys()]
        else:
            return html.H6('Analysis results not ready.')

    def get_quality_plot(self, group_key, theme=None, wrap=True):
        """ This gets the bar plot and the scores plot"""
        is_discrimination = 'accuracy' in h5py.File(self.results_filename)[group_key].attrs
        description = h5py.File(self.results_filename)[group_key].attrs['description']
        theme = theme or 'plotly_white'

        labels = [
            'R\u00B2Y',
            'R\u00B2X',
            'Q\u00B2Y',
        ]
        colors = [
            DEFAULT_PLOTLY_COLORS[0],
            DEFAULT_PLOTLY_COLORS[0],
            DEFAULT_PLOTLY_COLORS[1]
        ]
        if is_discrimination:
            labels += [
                'DR\u00B2Y',
                'DQ\u00B2Y',
                'Accuracy',
                'ROC AUC'
            ]
            colors += [
                DEFAULT_PLOTLY_COLORS[0],
                DEFAULT_PLOTLY_COLORS[1],
                DEFAULT_PLOTLY_COLORS[1],
                DEFAULT_PLOTLY_COLORS[1]
            ]
        with h5py.File(self.results_filename, 'r') as file:
            values = [
                file[group_key].attrs['r_squared_Y'],
                file[group_key].attrs['r_squared_X'],
                file[group_key].attrs['q_squared']
            ]
            if is_discrimination:
                values += [
                    file[group_key].attrs['discriminant_r_squared'],
                    file[group_key].attrs['discriminant_q_squared'],
                    file[group_key].attrs['accuracy'],
                    file[group_key].attrs['roc_auc']
                ]

        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }

        metric_plot = go.Figure(
            data=go.Bar(x=labels, y=values, marker_color=colors),
            layout=go.Layout(
                height=700,
                template=theme,
                font={'size': 16},
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title=f'Quality Metrics ({description})',
                xaxis={
                    'title': 'Metric',
                    **axis_line_style
                },
                yaxis={
                    'title': 'Value',
                    'range': [0, 1],
                    **axis_line_style
                }
            )
        )

        with h5py.File(self.results_filename, 'r') as file:
            t = np.array(file[group_key]['pls']['x_scores'])
            t_ortho = np.array(file[group_key]['opls']['T_ortho'][:, 0])
            target = np.ravel(np.array(file[group_key]['target']))
            if np.issubdtype(target.dtype, np.object_):
                target = target.astype(str)
            if type_of_target(np.ravel(target)).startswith('binary'):
                target = target.astype(str)

        if type_of_target(target).startswith('binary'):
            score_plot_data = [
                go.Scatter(x=np.ravel(t[np.where(target == val)]),
                           y=np.ravel(t_ortho[np.where(target == val)]),
                           mode='markers',
                           name=val,
                           marker={
                               'size': 15,
                               'opacity': 0.5,
                               'line': {'width': 0.5, 'color': 'white'},
                               'color': color
                           }) for val, color in zip(np.unique(target).tolist(), DEFAULT_PLOTLY_COLORS[:target.size])
            ]
        else:
            score_plot_data = go.Scatter(x=t.tolist(),
                                         y=t_ortho.tolist(),
                                         mode='markers',
                                         name=description,
                                         marker={
                                             'size': 15,
                                             'opacity': 0.5,
                                             'line': {'width': 0.5, 'color': 'white'},
                                             'color': target.tolist()
                                         })
        scores_plot = go.Figure(
            data=score_plot_data,
            layout=go.Layout(
                height=700,
                template=theme,
                font={'size': 16},
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title=f'Scores ({description})',
                xaxis={
                    'title': 't',
                    **axis_line_style
                },
                yaxis={
                    'title': 't_ortho',
                    **axis_line_style
                }
            )
        )
        if wrap:
            return html.Div([
                dbc.Row(dcc.Graph(figure=metric_plot)),
                dbc.Row(dcc.Graph(figure=scores_plot)),
                html.Br()
            ])
        else:
            return [
                dcc.Graph(figure=metric_plot),
                dcc.Graph(figure=scores_plot)
            ]

    def get_quality_plots(self, theme=None, wrap=True):
        if self.results_file_ready:
            return [self.get_quality_plot(key, theme, wrap) for key in h5py.File(self.results_filename).keys()]
        else:
            return html.H6('Analysis results not ready.')

    def get_metric_kde_plot(self, group_key, theme=None, wrap=True):
        is_discrimination = 'accuracy' in h5py.File(self.results_filename)[group_key].attrs
        description = h5py.File(self.results_filename)[group_key].attrs['description']

        labels = [
            'Q\u00B2Y',
        ]

        if is_discrimination:
            labels += [
                'DR\u00B2Y',
                'DQ\u00B2Y',
                'Accuracy',
                'ROC AUC'
            ]

        with h5py.File(self.results_filename, 'r') as file:
            true_values = [
                file[group_key].attrs['q_squared']
            ]
            p_values = [
                file[group_key].attrs['q_squared_p_value']
            ]
            permutation_values = [
                np.array(file[group_key]['permutation_q_squared'])
            ]
            if is_discrimination:
                true_values += [
                    file[group_key].attrs['discriminant_q_squared'],
                    file[group_key].attrs['accuracy'],
                    file[group_key].attrs['roc_auc']
                ]
                p_values += [
                    file[group_key].attrs['discriminant_q_squared_p_value'],
                    file[group_key].attrs['accuracy_p_value'],
                    file[group_key].attrs['roc_auc_p_value']
                ]
                permutation_values += [
                    np.array(file[group_key]['permutation_discriminant_q_squared']),
                    np.array(file[group_key]['permutation_accuracy']),
                    np.array(file[group_key]['permutation_roc_auc'])
                ]
        graphs = []
        theme = theme or 'plotly_white'
        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }
        for label, true_value, permutation_value, p_value in zip(labels, true_values, permutation_values, p_values):
            try:    
                x, y, true_kde = self._get_kde(permutation_value, true_value)
            except np.linalg.LinAlgError:
                x = y = true_kde = None
            point_plot = go.Scatter(
                x=np.ravel(permutation_value),
                y=[0 for _ in range(permutation_value.size)],
                text=f'{label} Values',
                name=f'{label} Values',
                mode='markers',
                marker={
                    'size': 7,
                    'opacity': 0.85,
                    'line': {'width': 0.5, 'color': 'white'},
                    'color': 'black',
                    'symbol': 'cross'
                }
            )
            
            if true_kde is not None:
                kde_plot = go.Scatter(
                    x=x,
                    y=y,
                    mode='lines',
                    name='KDE'
                )

                annotations = [
                    {
                        'x': true_value,
                        'y': true_kde,
                        'xref': 'x',
                        'yref': 'y',
                        'text': f'{true_value:.4f}',
                        'showarrow': True,
                        'arrowhead': 5,
                        'arrowsize': 2,
                        'arrowwidth': 1,
                        'arrowcolor': 'red',
                        'textangle': 0,
                        'font': {'size': 16}
                    }
                ]
            else:
                kde_plot = go.Scatter()
                annotations = []

            layout = go.Layout(
                height=700,
                template=theme,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title=f'{label} (p={p_value:.7f})',
                xaxis={
                    'title': label,
                    **axis_line_style
                },
                yaxis={
                    'title': 'Estimated Density',
                    **axis_line_style
                },
                annotations=annotations
            )
            graphs.append(dcc.Graph(figure=go.Figure(data=[point_plot, kde_plot], layout=layout)))
        if wrap:
            return html.Div([html.H4(description)] + graphs)
        else:
            return graphs

    def get_metric_kde_plots(self, theme, wrap=True):
        if self.results_file_ready:
            return [self.get_metric_kde_plot(key, theme, wrap) for key in h5py.File(self.results_filename).keys()]
        else:
            return html.H6('Analysis results not ready.')

    def get_group_options(self):
        try:
            with h5py.File(self.results_filename, 'r') as file:
                return [{'label': file[key].attrs['description'], 'value': key} for key in file.keys()]
        except:
            return []

    def get_bin_options(self, group_key):
        try:
            with h5py.File(self.results_filename, 'r') as file:
                feature_labels = np.array(file[group_key]['feature_labels'])
                p_values = np.array(file[group_key]['feature_p_values'])
                alpha = file[group_key].attrs['outer_alpha']
            is_significant = p_values < alpha
            df = pd.DataFrame()
            df['Bin'] = feature_labels
            df['p Value'] = p_values
            df['Significant'] = ['*' if s else '' for s in is_significant]
            df = df.sort_values(['Significant', 'Bin'], ascending=[False, True])
            return [{'label': f"{row['Bin']} (p={row['p Value']})", 'value': i} for i, row in df.iterrows()]
        except:
            return []

    @staticmethod
    def _get_kde(arr, true_value):
        arr_range = arr.max() - arr.min()
        x = np.linspace(arr.min() - 0.5 * arr_range, arr.max() + 0.5 * arr_range, 2 * arr.size)
        kernel = gaussian_kde(np.ravel(arr))
        # noinspection PyArgumentList
        return x, kernel(x), kernel(true_value).item()

    def _get_loading_kde(self, group_key, feature_ind):
        with h5py.File(self.results_filename, 'r') as file:
            loadings = np.array(file[group_key]['permutation_loadings'][:, feature_ind])
            true_loading = np.ravel(file[group_key]['opls']['x_loadings'])[feature_ind]
        return self._get_kde(loadings, true_loading)

    def get_loading_significance_plot(self, group_key, feature_ind, theme=None):
        try:
            x, y, true_kde = self._get_loading_kde(group_key, feature_ind)
        except np.linalg.LinAlgError:
            x = y = true_kde = None
        with h5py.File(self.results_filename, 'r') as file:
            true_value = np.ravel(file[group_key]['opls']['x_loadings'])[feature_ind]
            p_value = np.ravel(file[group_key]['feature_p_values'])[feature_ind]
            permutation_loadings = np.array(file[group_key]['permutation_loadings'])
            feature_labels = np.array(file[group_key]['feature_labels'])
        title = f'{feature_labels[feature_ind]} Loading={true_value} (p={p_value})'
        point_graph = go.Scatter(
            x=np.ravel(permutation_loadings),
            y=[0 for _ in range(permutation_loadings.shape[0])],
            text='Values',
            name='Values',
            mode='markers',
            marker={
                'size': 7,
                'opacity': 0.85,
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
                'x': true_value,
                'y': true_kde,
                'xref': 'x',
                'yref': 'y',
                'text': f'{true_value:.4f}',
                'showarrow': True,
                'arrowhead': 5,
                'arrowsize': 2,
                'arrowwidth': 1,
                'arrowcolor': 'red',
                'textangle': 0,
                'font': {'size': 16}
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
            height=500,
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

    def get_loading_significance_table(self, group_key, theme=None, wrap=True):
        description = h5py.File(self.results_filename)[group_key].attrs['description']
        if self.results_file_ready:
            theme, style_header, style_cell = self._get_table_styles(theme)
            with h5py.File(self.results_filename, 'r') as file:
                feature_labels = np.array(file[group_key]['feature_labels'])
                loadings = np.array(file[group_key]['pls']['x_loadings']).ravel()
                p_values = np.array(file[group_key]['feature_p_values'])
                alpha = file[group_key].attrs['outer_alpha']
                base_collection_id = file.attrs['input_collection_id'] if 'input_collection_id' in file.attrs else None
            x_min = x_max = None
            if base_collection_id is not None:
                try:
                    base_collection = get_collection(current_user, int(base_collection_id))
                    x = base_collection.get_dataset('/x').ravel()
                    x_min = base_collection.get_dataset('/x_min').ravel()
                    x_max = base_collection.get_dataset('/x_max').ravel()
                    x_min = x_min[np.in1d(x, feature_labels)]
                    x_max = x_max[np.in1d(x, feature_labels)]
                except Exception as e:
                    x_min = x_max = None
            valid_bin_boundaries = (x_min is not None
                                    and x_max is not None
                                    and x_max.shape[0] == x_min.shape[0] == feature_labels.shape[0])
            is_significant = p_values < alpha
            df = pd.DataFrame()
            df['Bin'] = feature_labels
            df['Loading'] = loadings
            if valid_bin_boundaries:
                df['Bin Max'] = x_max
                df['Bin Min'] = x_min
            df['p Value'] = p_values
            df['Significant'] = ['*' if s else '' for s in is_significant]
            df = df.sort_values(['Significant', 'Bin'], ascending=[False, True])

            # format table for better display in browser
            df['p Value'] = df['p Value'].round(7).apply(lambda val: f'{val:.7f}')
            df['Bin'] = df['Bin'].round(4).apply(lambda val: f'{val:.4f}')
            df['Loading'] = df['Loading'].round(5).apply(lambda val: f'{val:.5f}')
            if valid_bin_boundaries:
                df['Bin Max'] = df['Bin Max'].round(4).apply(lambda val: f'{val:.4f}')
                df['Bin Min'] = df['Bin Min'].round(4).apply(lambda val: f'{val:.4f}')
            del df['Significant']
            df['Index'] = [str(i) for i in df.index]
            if valid_bin_boundaries:
                df = df[['Index', 'Bin Max', 'Bin', 'Bin Min', 'Loading', 'p Value']]
            else:
                df = df[['Index', 'Bin', 'Loading', 'p Value']]
            style_data_conditional = [
                {
                    'if': {'filter_query': f'{{p Value}} < {alpha}'},
                    'backgroundColor': '#D2F9F1'
                },
                {
                    'if': {'filter_query': f'{{p Value}} > {alpha}'},
                    'backgroundColor': '#F9D9D2'
                }
            ]
            table = dash_table.DataTable(id=f'feature-table',
                                         columns=[{'name': i, 'id': i} for i in df.columns],
                                         data=df.to_dict('records'),
                                         style_table={
                                             'height': '500px',
                                             'overflowY': 'scroll'
                                         },
                                         fixed_rows={
                                             'headers': True,
                                             'data': 0
                                         },
                                         is_focused=True,
                                         style_data_conditional=style_data_conditional,
                                         style_header=style_header,
                                         style_cell=style_cell,
                                         style_cell_conditional=[
                                             {'if': {'column_id': 'Index'},
                                              'width': f'{max(df.Index.str.len().max(), 5) + 2}ch'},
                                             {'if': {'column_id': 'Bin'},
                                              'width': f'{df.Bin.str.len().max() + 2}ch'},
                                             {'if': {'column_id': 'Bin Max'},
                                              'width': f'{df.Bin.str.len().max() + 2}ch'},
                                             {'if': {'column_id': 'Bin Min'},
                                              'width': f'{df.Bin.str.len().max() + 2}ch'},
                                             {'if': {'column_id': 'p Value'},
                                              'width': '12ch'},
                                         ])
            if wrap:
                return html.Div(
                    [
                        dbc.Row(html.H4(description)),
                        dbc.Row(table)
                    ]
                )
            else:
                return table
        return [dash_table.DataTable(id='feature-table')]

    def get_loading_significance_tables(self, theme, wrap=True):
        if self.results_file_ready:
            return [self.get_loading_significance_table(key, theme, wrap)
                    for key in h5py.File(self.results_filename).keys()]
        else:
            return html.H6('Analysis results not ready.')

    def download_plots(self, file_formats, width, height, units, dpi):
        rds.set_value(f'{self.redis_prefix}_image_save_progress', 0)
        rds.set_value(f'{self.redis_prefix}_image_save_label', 'Starting job')
        rds.set_value(f'{self.redis_prefix}_image_save_progress_fraction', f'0/0')
        if self.results_file_ready:
            base_filename = f'opls_results_{self.results_collection_id}'
            root_dir = tempfile.mkdtemp()
            plot_dir = os.path.join(root_dir, f'{base_filename}_plots')
            os.mkdir(plot_dir)
            file_formats = file_formats or []
            if self.results_file_ready:
                groups = h5py.File(self.results_filename).keys()
                figure_data = {}
                for group in groups:
                    is_discrimination = 'accuracy' in h5py.File(self.results_filename)[group].attrs
                    quality_graph, score_graph = self.get_quality_plot(group, 'plotly_white', False)
                    if is_discrimination:
                        (
                            q_squared_graph,
                            discriminant_q_squared_graph,
                            accuracy_graph, roc_auc_graph) = self.get_metric_kde_plot(group, 'plotly_white', False)
                    else:
                        q_squared_graph = self.get_metric_kde_plot(group, 'plotly_white', False)
                        discriminant_q_squared_graph = accuracy_graph = roc_auc_graph = None
                    figure_data.update({
                        f'{group}_quality_metrics': quality_graph.to_plotly_json()['props']['figure'],
                        f'{group}_scores': score_graph.to_plotly_json()['props']['figure'],
                        f'{group}_q_squared_kde': q_squared_graph.to_plotly_json()['props']['figure']
                    })
                    if is_discrimination:
                        figure_data.update({
                            f'{group}_discriminant_q_squared_kde': discriminant_q_squared_graph.to_plotly_json()['props']['figure'],
                            f'{group}_accuracy_kde': accuracy_graph.to_plotly_json()['props']['figure'],
                            f'{group}_roc_auc_kde': roc_auc_graph.to_plotly_json()['props']['figure']
                        })
                    return save_figures.queue(figure_data, file_formats, width, height, units, dpi, plot_dir,
                                              f'user{current_user.id}', self.redis_prefix)
        raise RuntimeError('Plots not ready!')

    def get_results_collection_badges(self) -> List[html.Span]:
        if self.results_collection_id:
            if self.results_file_ready:
                if self.job_id:
                    color = 'success'
                else:
                    color = 'primary'
            else:
                if self.job_id:
                    color = 'warning'
                else:
                    color = 'danger'
            return [html.Span([dbc.Badge(f'{self.results_collection_id}', className='badge-pill', color=color), ' '])]
        else:
            return [html.Span([dbc.Badge('None', className='badge-pill')])]

    @staticmethod
    def _get_table_styles(theme):
        theme = theme or 'plotly_white'
        style_header = {
            'font-family': 'sans',
            'font-weight': 'bold',
            'backgroundColor': '#375A7F',
            'color': 'white'
        } if theme == 'plotly_dark' else {
            'font-family': 'sans',
            'font-weight': 'bold',
            'backgroundColor': '#2C3E50',
            'color': 'white'
        }
        style_cell = {
            'backgroundColor': '#303030',
            'color': 'white'
        } if theme == 'plotly_dark' else {
            'backgroundColor': 'white',
            'color': '#212529'
        }
        return theme, style_header, style_cell

    @staticmethod
    def _save_plot(plot, filename):

        pio.write_image(plot.to_plotly_json()['props']['figure'], filename)
