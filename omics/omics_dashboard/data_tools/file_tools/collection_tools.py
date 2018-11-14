import h5py
import numpy as np
import pandas as pd
from io import StringIO


def get_dataframe(filename: str, single_column: bool = False) -> str:
    """Get a string containing a CSV of a pandas dataframe of a collection"""
    """Note: this requires that there be datasets /Y and /x corresponding to an x-axis and y-values for that axis"""
    # TODO: make this not require datasets called /x and /Y
    buf = StringIO()
    with h5py.File(filename, 'r') as file:
        index = np.asarray(file['baseSampleId']).flatten() if 'baseSampleId' in file else [i for i in range(0, file['Y'].shape[0])]
        additional_columns = [key for key in file.keys() if key != 'baseSampleId'
                              and file[key].shape[0] == file['Y'].shape[0]
                              and (len(file[key].shape) == 1 or len(file[key].shape) == 2 and file[key].shape[1] == 1)]
        df = pd.DataFrame(index=index) if single_column else pd.DataFrame(data=np.asarray(file['/Y']),
                                                                          columns=np.asarray(file['/x']).flatten().tolist(),
                                                                          index=index)
        df.index.name = 'baseSampleId' if 'baseSampleId' in file else 'sampleId'
        # collect additional columns
        for key in additional_columns:
            if file[key].dtype.type is np.string_ or file[key].dtype.type is np.object_:
                try:
                    df[key] = [row.decode('utf-8') for row in np.asarray(file[key]).flatten()]
                except:
                    pass
            else:
                df[key] = np.asarray(file[key])

    df.to_csv(buf)
    return buf.getvalue()


def update_array(filename: str, path: str, i: int, j: int, val):
    with h5py.File(filename, 'r+') as file:
        print(f'update_array i={i},j={j},val={val}')
        if len(file[path].shape) == 1:
            file[path][int(i)] = val
        else:
            print('shape of path not 1')
            file[path][int(i), int(j)] = val

