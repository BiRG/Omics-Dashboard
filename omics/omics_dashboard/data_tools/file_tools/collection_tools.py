import h5py
import numpy as np
import pandas as pd
from io import StringIO


def get_dataframe(filename: str) -> str:
    """Get a string containing a CSV of a pandas dataframe of a collection"""
    """Note: this requires that there be datasets /Y and /x corresponding to an x-axis and y-values for that axis"""
    # TODO: make this not require datasets called /x and /Y
    buf = StringIO()
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
    df.to_csv(buf)
    return buf.getvalue()
