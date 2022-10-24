import json
from io import StringIO
from typing import Dict, Union, Any, List

import h5py
import numpy as np
import pandas as pd


def convert_strings(arr):
    # type: (np.array) -> np.array
    """
    If we have an object array full of bytes, convert to str (depends on python version)
    :param arr:
    :return:
    """
    if arr.dtype == np.string_ or arr.dtype == np.object and str is not bytes:
        try:
            return np.vectorize(lambda x: x.decode('utf-8'))(arr)
        except Exception as e:
            print('Could not convert np.object or np.string_ to string:\n{}'.format(e))
    return arr


def create_collection_file(datasets: Dict[str, Any], attrs: Dict[str, Any], filename: str):
    with h5py.File(filename, 'w') as file:
        for name, value in datasets.items():
            if value.dtype != np.number:
                if isinstance(value, np.ndarray):
                    value = np.array([','.join([str(v) for v in val]) for val in value]).reshape(-1, 1)
                file.create_dataset(str(name), data=value.astype(np.string_), dtype=h5py.special_dtype(vlen=bytes))
            else:
                file.create_dataset(str(name), data=value)
        file.attrs.update(attrs)


def get_dataframe(filename: str,
                  row_index_key: str = 'base_sample_id',
                  keys: List[str] = None,
                  include_labels: bool = True,
                  numeric_columns: bool = False,
                  include_only_labels: bool = False):
    """
    Get a Pandas DataFrame from an hdf5 file
    :param filename:
    :param row_index_key: Key of a label row to use as the row index
    :param keys: Keys to construct dataframe from. Should all have the same number of rows. If none, will use columns of
    '/Y' and all "labels" (arrays with the same number of rows as 'Y') if include_labels is true
    :param include_labels: Whether or not to include those datasets with the same number of rows as Y (row labels).
    :param numeric_columns: Whether the column names for Y should take the form x_i as opposed to Y_{x_i}.
    :param include_only_labels: Whether to exclude 'Y' entirely and only include those datasets with the same number of rows as Y, but not Y.
    :return:
    """
    include_labels = include_only_labels or include_labels
    with h5py.File(filename, 'r') as fp:
        if 'Y' not in fp and not keys:
            raise ValueError('No \'Y\' dataset in file and no other keys specified.')
        if keys:
            row_count = fp[keys[0]].shape[0]
        else:
            row_count = fp['Y'].shape[0]
            keys = [key for key in fp.keys() if (isinstance(fp[key], h5py.Dataset) and fp[key].shape[0] == row_count)] if include_labels else ['Y']
        index = np.asarray(fp[row_index_key]).flatten() if row_index_key in fp else [i for i in range(0, row_count)]
        df = pd.DataFrame(index=index)
        if include_only_labels and 'Y' in keys:
            keys.remove('Y')
        for key in keys:
            if key in {'Y', '/Y'}:
                columns = [str(x_i) if numeric_columns else 'Y_{}'.format(x_i)
                           for x_i in np.asarray(fp['x']).flatten().tolist()] \
                    if 'x' in fp else [str(i + 1) if numeric_columns else 'Y_{}'.format(i + 1)
                                       for i in range(0, fp['Y'].shape[1])]
            else:
                column_count = fp[key].shape[1] if len(fp[key].shape) > 1 else 1
                columns = ['{}_{}'.format(key, i + 1) for i in range(0, column_count)] if column_count > 1 else [key]
            data = convert_strings(np.asarray(fp[key]))
            new_df = pd.DataFrame(columns=columns, data=data, index=index)
            df = pd.concat((df, new_df), axis=1)
        df.index.name = row_index_key if row_index_key is not None else 'id'
        return df


def get_serialized_dataframe(filename: str, single_column: bool = False, data_format='csv', json_orient='records') \
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
        val = file[path].dtype.type(val)
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


def delete(filename: str, path: str, obj, axis=None):
    with h5py.File(filename, 'r+') as file:
        arr = np.array(file[path])
        arr = np.delete(arr, obj, axis)
        del file[path]
        file[path] = arr
