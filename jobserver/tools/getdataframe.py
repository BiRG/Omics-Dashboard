#!/usr/bin/env python3
import sys
import h5py
import pandas as pd
filename = sys.argv[1]
with h5py.File(filename, 'r') as file:
    df = pd.DataFrame(data=np.asarray(file['/Y']).T,
                      columns=np.asarray(file['/x']).T,
                      index=np.asarray(file['/baseSampleId']).T)
    for key in file.keys():
        if isinstance(file[key], h5py.Dataset) and file[key].shape[1] == file['/Y'].shape[1]:
            df[key] = np.asarray(file[key]).T
df.to_csv(f'{filename}.csv') 		