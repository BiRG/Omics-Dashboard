#!/usr/bin/env python3
import sys
import h5py
import pandas as pd
filename = sys.argv[1]
with h5py.File(filename, 'r') as file:
    df = pd.DataFrame(data=np.asarray(file['/Y']).T,
                      columns=np.asarray(file['/x']).flatten(),
                      index=np.asarray(file['/baseSampleId']).flatten())
    for key in file.keys():
        if isinstance(file[key], h5py.Dataset) and file[key].shape[0] == 1 and file[key].shape[1] == len(df):
            if file[key].dtype.type is np.string_:
                df[key] = [row.decode('utf-8') for row in file[key][0]]
            else:
                df[key] = file[key][0]
df.to_csv(f'{filename}.csv')