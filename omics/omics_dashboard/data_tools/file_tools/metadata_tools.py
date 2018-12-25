import h5py
import os
from io import StringIO
from typing import List, Dict, Any
import numpy as np


def get_collection_metadata(filename: str) -> Dict[str, Any]:
    """Get attributes of a hdf5 file, its last modified date, and the sizes of its largest datasets"""
    with h5py.File(filename, 'r') as infile:
        attrs = {key: (value.decode('UTF-8') if isinstance(value, bytes) else value)
                 for key, value in infile.attrs.items()}
    attrs['date_modified'] = int(os.path.getmtime(filename))
    dims = approximate_dims(filename)
    attrs['max_row_count'] = dims[0]
    attrs['max_col_count'] = dims[1]
    return {key: (value.item() if hasattr(value, 'item') else value) for (key, value) in attrs.items()}


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
        dataset = infile[str(path)].value
    s = StringIO()
    if dataset is not None:
        for row in dataset:
            s.write(convert_row(row))
            s.write('\n')
        return s.getvalue()
    raise ValueError('File or path not found')


def convert_row(row: np.array) -> str:
    """Get a comma-separated string representation of a row of a dataset"""
    if isinstance(row, bytes):
        return row.decode('ascii')
    else:
        return ','.join([convert_cell(cell) for cell in row])


def convert_cell(cell: Any) -> str:
    """Convert an array cell to utf-8 string"""
    return cell.decode('ascii') if isinstance(cell, bytes) else str(cell)


def iterate_dataset_paths(group: h5py.Group, paths: List) -> None:
    """Recursively touch every path in this dataset"""
    [iterate_dataset_paths(group[key], paths) for key in group.keys() if isinstance(group[key], h5py.Group)]
    paths.extend([get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)])


def get_group_info(group: h5py.Group) -> Dict[str, Any]:
    """Get the path, attributes, child groups and child datasets of a group"""
    return {
        'path': group.name,
        'attrs': {key: (value.decode('UTF-8') if isinstance(value, bytes) else value)
                  for key, value in group.attrs.items()},
        'groups': [get_group_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Group)],
        'datasets': [get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)]
    }


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
        'attrs': {key: (value.decode('UTF-8') if isinstance(value, bytes) else value)
                  for key, value in dataset.attrs.items()},
        'rows': rows,
        'cols': cols,
        'dtype': str(dataset.dtype)
    }


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


def get_datasets(file: h5py.File) -> List[h5py.Dataset]:
    """Get all the datasets in this file"""
    return [file[key] for key in file.keys() if isinstance(file[key], h5py.Dataset)]
