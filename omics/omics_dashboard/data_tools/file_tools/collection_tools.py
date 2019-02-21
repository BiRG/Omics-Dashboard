import h5py
import numpy as np
import pandas as pd
import json
from io import StringIO
from typing import Dict, Union, Any


def get_dataframe(filename: str, single_column: bool = False, data_format='csv', json_orient='records') \
        -> Union[str, Dict[str, any]]:
    """Get a string containing a CSV of a pandas dataframe of a collection"""
    """Note: this requires that there be datasets /Y and /x corresponding to an x-axis and y-values for that axis"""
    # TODO: make this not require datasets called /x and /Y
    buf = StringIO()
    with h5py.File(filename, 'r') as file:
        index = np.asarray(file['base_sample_id']).flatten() if 'base_sample_id' in file else [i for i in range(0, file['Y'].shape[0])]
        additional_columns = [key for key in file.keys() if key != 'base_sample_id'
            and (file[key].shape[0] == file['Y'].shape[0] if 'Y' in file else False)
                              and (len(file[key].shape) == 1 or len(file[key].shape) == 2 and file[key].shape[1] == 1)]
        df = pd.DataFrame(index=index) if single_column else pd.DataFrame(data=np.asarray(file['/Y']),
                                                                          columns=np.asarray(file['/x']).flatten().tolist(),
                                                                          index=index)
        df.index.name = 'base_sample_id' if 'base_sample_id' in file else 'id'
        # collect additional columns
        for key in additional_columns:
            if file[key].dtype.type is np.string_ or file[key].dtype.type is np.object_:
                try:
                    df[key] = [row.decode('utf-8') for row in np.asarray(file[key]).flatten()]
                except Exception:
                    pass
            else:
                df[key] = np.asarray(file[key])
    if data_format == 'json':
        df.to_json(buf, orient=json_orient)
    else:
        df.to_csv(buf)
    return json.loads(buf.getvalue()) if data_format == 'json' else buf.getvalue()


def update_array(filename: str, path: str, i: int, j: int, val):
    i = 0 if i is None else i
    j = 0 if j is None else j
    with h5py.File(filename, 'r+') as file:
        print('file opened')
        val = file[path].dtype.type(val)
        print(val)
        if len(file[path].shape) == 1:
            file[path][int(i)] = val
        else:
            file[path][int(i), int(j)] = val


def validate_update(filename: str, path: str, i: int, j: int, val: Any):
    """Throw an exception if anything doesn't work"""
    """If this throws an exception, update_array will throw same exception"""
    i = 0 if i is None else i
    j = 0 if j is None else j
    with h5py.File(filename, 'r') as file:
        file[path].dtype.type(val)  # throw ValueError if can't convert to dtype, KeyError if path not in file
        if len(file[path].shape) == 1:
            current_val = file[path][int(i)]  # throw ValueError if i out of range
        else:
            current_val = file[path][int(i), int(j)]  # throw ValueError if i or j out of range
    return current_val


def get_dataset(filename: str, path: str, convert_strings=False):
    with h5py.File(filename, 'r') as file:
        # get shape and try to flatten if 1 row or 1 column
        if max(file[path].shape) + 1 >= sum(file[path].shape):
            val = np.asarray(file[path]).flatten()
        else:
            val = np.asarray(file[path])
        if convert_strings:
            return np.asarray([row.decode('ascii') if isinstance(row, bytes) else row for row in val])
        return val
