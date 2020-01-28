#!/usr/bin/env python3
import argparse
import os
import h5py
import numpy as np
import pandas as pd


def load_dataframes(filename):
    return pd.read_hdf(filename, 'numeric_df'), pd.read_hdf(filename, 'label_df')


def process_data(dataframe_filename=None, scale_by=None, model_by=None, ignore_by=None, pair_on=None, pair_with=None):
    print(f'dataframe_filename: {dataframe_filename}')
    numeric_df, label_df = load_dataframes(dataframe_filename)

    if dataframe_filename is None:
        raise ValueError('No filename specified!')

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
        if len(good_queries):
            query = ' & '.join(good_queries)
            label_df = label_df.query(query)
            numeric_df = numeric_df.loc[label_df.index]

    if model_by:
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

    good_x_inds = np.where(model_numeric_df.isnull().sum() == 0)[0]
    good_columns = model_numeric_df.columns[good_x_inds]
    model_numeric_df = model_numeric_df[good_columns]
    metadata = {
        'model_by': model_by or '',
        'ignore_by': ignore_by or '',
        'scale_by': scale_by or '',
        'pair_on': ','.join(pair_on) if pair_on else '',
        'pair_with': pair_with or '',
    }
    description = ''
    if scale_by:
        description += f' scaled by {scale_by}'
    if model_by:
        description += f' including {model_by}'
    if ignore_by:
        description += f' ignoring {ignore_by}'
    if pair_on and pair_with:
        description += f' paired on {pair_on} against {pair_with}'
    metadata['description'] = description
    if len(warnings):
        print('\n' + '\n'.join(warnings) + '\n')
    return model_numeric_df, model_label_df, metadata


parser = argparse.ArgumentParser(description='Pre-processing for multivariate methods like PCA.')
parser.add_argument('dataframe_filename', metavar='input_dfs_file', type=str,
                    help='HDF5 file containing two pandas DataFrames, "numeric_df" and "label_df"')
parser.add_argument('--scale_by', type=str, help='Pandas query for scaling.')
parser.add_argument('--model_by', type=str, help='Pandas query for model selection.')
parser.add_argument('--ignore_by', type=str, help='Pandas query for model filtering.')
parser.add_argument('--pair_on', type=str, help='Name of column to pair on.')
parser.add_argument('--pair_with', type=str, help='Pandas query describing points to subtract.')

args = parser.parse_args()

with h5py.File(args.dataframe_filename, 'r') as file:
    collection_id = file.attrs['collection_id'] if 'collection_id' in file.attrs else None

numeric_df_, label_df_, metadata_ = process_data(**vars(args))
if collection_id is not None:
    metadata_['collection_id'] = collection_id
    out_filename = f'{collection_id}_processed.h5'
else:
    out_filename = f'{os.path.basename(args.dataframe_filename)}_processed.h5'
with h5py.File(out_filename, 'w') as out_file:
    out_file.attrs.update(metadata_)
numeric_df_.to_hdf(out_filename, 'numeric_df')
label_df_.to_hdf(out_filename, 'label_df')
