#!/usr/bin/env python3
import os
import sys
from omics_dashboard_client.hdf_tools import get_dataframe
import h5py


in_filename = sys.argv[1]
print(in_filename)
print([attr for attr in h5py.File(in_filename, 'r').attrs])
with h5py.File(in_filename, 'r') as file:
    collection_id = file.attrs['collection_id'] if 'collection_id' in file.attrs else None

out_filename = f'{collection_id}.h5' if collection_id is not None else f'{os.path.basename(in_filename)}_dataframes.h5'

with h5py.File(out_filename, 'w') as out_file:
    if collection_id is not None:
        out_file.attrs['collection_id'] = collection_id

numeric_df = get_dataframe(in_filename, include_labels=False, numeric_columns=True)
label_df = get_dataframe(in_filename, include_only_labels=True)
numeric_df.to_hdf(out_filename, 'numeric_df')
label_df.to_hdf(out_filename, 'label_df')
