import os
from io import StringIO
from typing import List, Dict, Any, Union

import h5py
import numpy as np


def get_file_attributes(filename: str) -> Dict[str, Any]:
    with h5py.File(filename, 'r') as infile:
        return {key: (value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else value)
                for key, value in infile.attrs.items()}


def get_all_group_attributes(filename: str) -> Dict[str, Any]:
    """All attributes of all groups of the file"""
    with h5py.File(filename, 'r') as infile:
        attrs = [get_group_attrs(infile[key]) for key in infile.keys() if isinstance(infile[key], h5py.Group)]
    all_attrs = {}
    for attr in attrs:
        all_attrs.update(attr)
    return all_attrs


def get_file_attribute_dtypes(filename: str) -> Dict[str, str]:
    with h5py.File(filename, 'r') as infile:
        return {key: type(value).__name__ for key, value in infile.attrs.items()}


def get_collection_metadata(filename: str) -> Dict[str, Any]:
    """Get attributes of a hdf5 file, its last modified date, and the sizes of its largest datasets"""
    with h5py.File(filename, 'r') as infile:
        attrs = {key: (value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else value)
                 for key, value in infile.attrs.items()}
    attrs['date_modified'] = int(os.path.getmtime(filename))
    dims = approximate_dims(filename)
    attrs['max_row_count'] = dims[0]
    attrs['max_col_count'] = dims[1]
    return attrs


def get_collection_info(filename: str) -> Dict[str, Any]:
    """Get metadata and paths of a hdf5 file"""
    with h5py.File(filename, 'r') as infile:
        collection_info = get_group_info(infile)
    collection_info.update(collection_info['attrs'])
    del collection_info['attrs']
    collection_info['date_modified'] = int(os.path.getmtime(filename))
    dims = approximate_dims(filename)
    collection_info['max_row_count'] = dims[0]
    collection_info['max_col_count'] = dims[1]
    return {key: (value.item() if hasattr(value, 'item') else value) for (key, value) in collection_info.items()}


def get_dataset_paths(filename: str) -> List[str]:
    """Get all the paths pointing to h5py.Datasets in this file"""
    paths = []
    with h5py.File(filename, 'r') as infile:
        iterate_dataset_paths(infile, paths)
    return paths


#  Can raise exceptions!
def get_csv(filename: str, path: str) -> str:
    """Get a string containing comma-separated values for a dataset"""
    with h5py.File(filename, 'r') as infile:
        dataset = infile[str(path)]
        s = StringIO()
        if dataset is not None:
            dataset = np.array(dataset)
            if dataset.dtype.type is np.object_:
                dataset = dataset.astype(str)
                np.savetxt(s, dataset, delimiter=',', fmt='%s')
            else:
                np.savetxt(s, dataset, delimiter=',')
        return s.getvalue()


def iterate_dataset_paths(group: h5py.Group, paths: List) -> None:
    """Recursively touch every path in this dataset"""
    [iterate_dataset_paths(group[key], paths) for key in group.keys() if isinstance(group[key], h5py.Group)]
    paths.extend([get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)])


def get_group_info(group: h5py.Group) -> Dict[str, Any]:
    """Get the path, attributes, child groups and child datasets of a group"""

    def process_value(value):
        value = getattr(value, "tolist", lambda x=value: x)()
        return value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else value

    return {
        'path': group.name,
        'attrs': {key: process_value(value) for key, value in group.attrs.items()},
        'groups': [get_group_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Group)],
        'datasets': [get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)]
    }


def get_group_attrs(group: h5py.Group) -> Dict[str, Any]:

    def process_value(value):
        value = getattr(value, "tolist", lambda x=value: x)()
        return value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else value

    main_attrs = {f'{group.name}/{key}': process_value(value) for key, value in group.attrs.items()}
    child_attrs = [get_group_attrs(group[key]) for key in group.keys() if isinstance(group[key], h5py.Group)]
    all_attrs = main_attrs
    for child_attr in child_attrs:
        all_attrs.update(child_attr)
    return all_attrs


def get_dataset_info(dataset: h5py.Dataset) -> Dict[str, Any]:
    """Get the dimensions, data type and attributes of a dataset"""
    rows = 0
    cols = 0
    if len(dataset.shape) == 1:
        rows = dataset.shape[0]
        cols = 1
    if len(dataset.shape) > 1:
        rows = dataset.shape[0]
        cols = dataset.shape[1]
    return {
        'path': dataset.name,
        'attrs': {key: (value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else value)
                  for key, value in dataset.attrs.items()},
        'rows': rows,
        'cols': cols,
        'dtype': str(dataset.dtype)
    }


def get_all_dataset_info(filename: str):
    with h5py.File(filename, 'r') as file:
        return [get_dataset_info(dataset) for dataset in get_datasets(file)]


def update_metadata(filename: str, new_data: Dict[str, Any]) -> Dict[str, Any]:
    with h5py.File(filename, 'r+') as file:
        file.attrs.update(new_data)
    return get_collection_info(filename)


def create_empty_file(filename: str, new_data: Dict[str, Any]) -> Dict[str, Any]:
    with h5py.File(filename, 'w') as file:
        file.attrs.update(new_data)
    return get_collection_info(filename)


def approximate_dims(filename: str) -> (int, int):
    """ Return a (m, n) pair where m is the longest row count and n is longest col count of all datasets"""
    with h5py.File(filename, 'r') as file:
        try:
            m = max([dataset.shape[0] for dataset in get_datasets(file)])
            n = max([dataset.shape[1] if len(dataset.shape) > 1 else 1 for dataset in get_datasets(file)])
            return m, n
        except ValueError:
            return 0, 0


def get_datasets(group: Union[h5py.File, h5py.Group]) -> List[h5py.Dataset]:
    """Get all the datasets in this file (recursively)"""
    datasets = []
    for key in group.keys():
        if isinstance(group[key], h5py.Dataset):
            datasets.append(group[key])
        elif isinstance(group[key], h5py.Group):
            datasets = datasets + get_datasets(group[key])
    return datasets


def add_column(filename: str, name: str, data_type: str = 'string'):
    m, _ = approximate_dims(filename)
    with h5py.File(filename, 'r+') as file:
        if data_type == 'integer':
            file.create_dataset(name, shape=(m, 1), dtype=np.int64)
        elif data_type == 'float':
            file.create_dataset(name, shape=(m, 1), dtype=np.float64)
        elif data_type == 'string':
            file.create_dataset(name, shape=(m, 1), dtype=h5py.special_dtype(vlen=bytes))
        else:
            raise ValueError(f'Improper data_type {data_type}')
