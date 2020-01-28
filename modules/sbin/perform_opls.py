#!/usr/bin/env python3
import argparse
import h5py
import pandas as pd
from pyopls import OPLSValidator
import os
import sys
import numpy as np

from joblib import parallel_backend

print(' '.join(sys.argv))


def load_data(filename, group_key):
    with h5py.File(filename, 'r') as file:
        description_ = file[group_key].attrs['description']
        try:
            pos_label_ = file[group_key].attrs['pos_label']
        except:
            pos_label_ = None
        try:
            neg_label_ = file[group_key].attrs['neg_label']
        except:
            neg_label_ = None
    return (pd.read_hdf(filename, f'{group_key}/X'), pd.read_hdf(filename, f'{group_key}/y'),
            description_, pos_label_, neg_label_)


def serialize_opls(filename, validator_: OPLSValidator, name, description_, pos_label_, neg_label_, target, feature_labels):
    significant_features = feature_labels[validator_.feature_significance_]
    with h5py.File(filename, 'a') as file:
        group = file.create_group(name)
        group.attrs['description'] = description_
        group.attrs['pos_label'] = pos_label_ if pos_label_ is not None else ''
        group.attrs['neg_label'] = neg_label_ if neg_label_ is not None else ''
        group.attrs['k'] = validator_.k
        group.attrs['n_permutations'] = validator_.n_permutations
        group.attrs['n_inner_permutations'] = validator_.n_inner_permutations
        group.attrs['n_outer_permutations'] = validator_.n_outer_permutations
        group.attrs['inner_alpha'] = validator_.inner_alpha
        group.attrs['outer_alpha'] = validator_.outer_alpha
        group.attrs['n_components'] = validator_.n_components_
        group.attrs['q_squared'] = validator_.q_squared_
        group.attrs['q_squared_p_value'] = validator_.q_squared_p_value_
        group.attrs['r_squared_Y'] = validator_.r_squared_Y_
        group.attrs['r_squared_Y_p_value'] = validator_.r_squared_Y_p_value_
        group.attrs['r_squared_X'] = validator_.r_squared_X_
        group.attrs['r_squared_X_p_value'] = validator_.r_squared_X_p_value_

        group.create_dataset('permutation_q_squared', data=validator_.permutation_q_squared_)
        group.create_dataset('permutation_r_squared_Y', data=validator_.permutation_r_squared_Y_)
        group.create_dataset('permutation_r_squared_X', data=validator_.permutation_r_squared_X_)
        group.create_dataset('permutation_loadings', data=validator_.permutation_loadings_)
        group.create_dataset('feature_p_values', data=validator_.feature_p_values_)

        target_dtype = h5py.special_dtype(vlen=bytes) if target.dtype.type is np.object_ else target.dtype
        group.create_dataset('target', data=target.to_numpy(), dtype=target_dtype)
        group.create_dataset('index', data=target.index.to_numpy())
        group.create_dataset('feature_labels', data=feature_labels)
        group.create_dataset('significant_features', data=significant_features)

        regressor_group = group.create_group('opls')
        regressor_group.attrs['r_squared_X_'] = validator_.estimator_.r_squared_X_
        regressor_group.attrs['r_squared_Y_'] = validator_.estimator_.r_squared_Y_
        regressor_group.attrs['y_weight'] = validator_.estimator_.y_weights_
        regressor_group.create_dataset('orthogonal_x_weights', data=validator_.estimator_.orthogonal_x_weights_)
        regressor_group.create_dataset('x_weights', data=validator_.estimator_.x_weights_)
        regressor_group.create_dataset('orthogonal_x_loadings', data=validator_.estimator_.orthogonal_x_loadings_)
        regressor_group.create_dataset('x_loadings', data=validator_.estimator_.x_loadings_)
        regressor_group.create_dataset('orthogonal_x_scores', data=validator_.estimator_.orthogonal_x_scores_)
        regressor_group.create_dataset('x_scores', data=validator_.estimator_.x_scores_)
        regressor_group.create_dataset('y_scores', data=validator_.estimator_.y_scores_)
        regressor_group.create_dataset('coef', data=validator_.estimator_.coef_)
        if validator_.accuracy_ is not None:
            group['transformed_target'] = validator_.binarizer_.transform(target)
            group.attrs['accuracy'] = validator_.accuracy_
            group.attrs['accuracy_p_value'] = validator_.accuracy_p_value_
            group.attrs['roc_auc'] = validator_.roc_auc_
            group.attrs['roc_auc_p_value'] = validator_.roc_auc_p_value_
            group.attrs['discriminant_q_squared'] = validator_.discriminant_q_squared_
            group.attrs['discriminant_q_squared_p_value'] = validator_.discriminant_q_squared_p_value_
            group.attrs['discriminant_r_squared'] = validator_.discriminant_r_squared_
            group.attrs['discriminant_r_squared_p_value'] = validator_.discriminant_r_squared_p_value_

            group.create_dataset('permutation_accuracy', data=validator_.permutation_accuracy_)
            group.create_dataset('permutation_roc_auc', data=validator_.permutation_roc_auc_)
            group.create_dataset('permutation_discriminant_q_squared',
                                 data=validator_.permutation_discriminant_q_squared_)
            group.create_dataset('permutation_discriminant_r_squared',
                                 data=validator_.permutation_discriminant_r_squared_)


parser = argparse.ArgumentParser(description='Perform Orthogonal Projection to Latent Structures')
parser.add_argument('dataframe_filename', type=str,
                    help='HDF5 file containing two pandas DataFrames, "numeric_df" and "label_df".')
parser.add_argument('k', type=int, help='Number of cross-validation folds, -1 for leave-one-out.')
parser.add_argument('min_n_components', type=int, help='Minimum number of orthogonal components to remove.')
parser.add_argument('inner_test_alpha', type=float,
                    help='First significance threshold, values outside of this will be '
                         'tested for outer_test_permutations')
parser.add_argument('outer_test_alpha', type=float,
                    help='Second significance threshold, applied to values tested with outer_test_permutations.')
parser.add_argument('metric_test_permutations', type=int,
                    help='Number of permutations to perform to determine significance of metrics (like R-squared).')
parser.add_argument('inner_test_permutations', type=int,
                    help='Number of permutations to perform for all features.')
parser.add_argument('outer_test_permutations', type=int,
                    help='Number of permutations to perform for features deemed significant with inner_test_alpha.')
parser.add_argument('--force_regression', type=bool, default=False,
                    help='If True, treat numeric multiclass or binary variables as continuous variables.')
args = parser.parse_args()

group_keys = [key for key in h5py.File(args.dataframe_filename).keys()]
output_filename = os.path.splitext(os.path.basename(args.dataframe_filename))[0] + '_results.h5'

with h5py.File(output_filename, 'w') as out_file, h5py.File(args.dataframe_filename, 'r') as in_file:
    if 'collection_id' in in_file.attrs:
        out_file.attrs['input_collection_id'] = in_file.attrs['collection_id']
    out_file.attrs.update({key: value for key, value in in_file.attrs.items() if key != 'collection_id'})
    out_file.attrs['analysis_type'] = 'opls'

for key in group_keys:
    X, y, description, pos_label, neg_label = load_data(args.dataframe_filename, key)
    feature_labels = np.array([float(c) for c in X.columns])
    print(description)
    validator = OPLSValidator(args.min_n_components, args.k, False, args.force_regression,
                              args.metric_test_permutations, args.inner_test_permutations, args.outer_test_permutations,
                              args.inner_test_alpha, args.outer_test_alpha)
    print(f'======  Fitting {key}  ======')
    with parallel_backend('threading'):
        validator.fit(X, y, pos_label=pos_label, verbose=1)
    serialize_opls(output_filename, validator, key, description, pos_label, neg_label, y, feature_labels)
