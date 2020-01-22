#!/usr/bin/env python3
import argparse
import itertools
import os
import sys
import pandas as pd
import h5py
from sklearn.utils.multiclass import type_of_target

print(' '.join(sys.argv))


def serialize_targets(targets, filename):
    for target in targets:
        print(target['name'])
        with h5py.File(filename, 'a') as file:
            group = file.create_group(target['name'])
            group.attrs['description'] = target['description']
            if 'pos_label' in target:
                group.attrs['pos_label'] = target['pos_label']
            if 'neg_label' in target:
                group.attrs['neg_label'] = target['neg_label']
        target['X'].to_hdf(filename, f'/{target["name"]}/X')
        target['y'].to_hdf(filename, f'/{target["name"]}/y')


parser = argparse.ArgumentParser(description='Get One vs. One and/or One vs. All binary X/y splits from multiclass '
                                             'target. If neither option is chosen, data is simply copied.')
parser.add_argument('dataframe_file', type=str,
                    help='HDF5 file containing "numeric_df" and "label_df" dataframes.')
parser.add_argument('target_column', type=str, help='The column of label_df to use as a target.')
parser.add_argument('--one_v_all', action='store_true', help='Whether to perform One vs. One split.')
parser.add_argument('--one_v_one', action='store_true', help='Whether to perform One vs. All split.')

args = parser.parse_args()
numeric_df = pd.read_hdf(args.dataframe_file, 'numeric_df')
label_df = pd.read_hdf(args.dataframe_file, 'label_df')
targets_ = []
target_values = label_df[args.target_column]

unique_vals = pd.unique(target_values)
print(unique_vals)
if len(unique_vals) == 2:
    args.one_v_all = False

if len(unique_vals) == 1:
    raise ValueError('Target has only one unique value!')

if args.one_v_all:
    for unique_val in unique_vals:
        target_column = target_values.copy()
        neg_label = f'not_{unique_val}'
        target_column[target_column != unique_val] = neg_label
        targets_.append(
            {
                'name': f'{unique_val}_vs_all',
                'description': f'{unique_val} vs. All',
                'X': numeric_df,
                'y': target_column,
                'pos_label': unique_val,
                'neg_label': neg_label
            }
        )
if args.one_v_one:
    for first, second in itertools.combinations(pd.unique(target_values), 2):
        target_column = label_df.query(f'({args.target_column}=="{first}") | ({args.target_column}=="{second}")')[args.target_column]
        targets_.append(
            {
                'name': f'{first}_vs_{second}',
                'description': f'{first} vs. {second}',
                'X': numeric_df.loc[target_column.index],
                'y': target_column,
                'pos_label': first,
                'neg_label': second
            }
        )
if (not args.one_v_all) and (not args.one_v_one):
    if type_of_target(target_values).startswith('binary'):
        pos_label = pd.unique(target_values)[0]
        neg_label = pd.unique(target_values)[1]
        description = f'{pos_label} vs. {neg_label}'
        name = f'{pos_label} vs. {neg_label}'
    else:
        pos_label = ''
        neg_label = ''
        description = args.target_column
        name = args.target_column
    targets_.append(
        {
            'name': name,
            'description': description,
            'X': numeric_df,
            'y': target_values,
            'pos_label': pos_label,
            'neg_label': neg_label
        }
    )
out_filename = os.path.splitext(os.path.basename(args.dataframe_file))[0] + '_targets.h5'
h5py.File(out_filename, 'w')  # initialize file so pytables doesn't dump a bunch of bs on it
serialize_targets(targets_, out_filename)
with h5py.File(out_filename, 'r+') as out_file, h5py.File(args.dataframe_file, 'r') as in_file:
    out_file.attrs.update(in_file.attrs)
