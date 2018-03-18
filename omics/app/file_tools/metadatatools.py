import h5py
import os
import numpy as np
from io import StringIO


def get_collection_metadata(filename):
    with h5py.File(filename, 'r') as infile:
        attrs = {key: (value.decode('UTF-8') if isinstance(value, bytes) else value) for key, value in infile.attrs.items()}
    collection_id = os.path.splitext(os.path.basename(filename))[0]
    attrs['id'] = int(collection_id)
    attrs['dateModified'] = int(os.path.getmtime(filename))
    return attrs


def get_collection_info(filename):
    with h5py.File(filename, 'r') as infile:
        collection_info = get_group_info(infile)
    collection_id = os.path.splitext(os.path.basename(filename))[0]
    collection_info['id'] = int(collection_id)
    collection_info.update(collection_info['attrs'])
    del collection_info['attrs']
    collection_info['dateModified'] = int(os.path.getmtime(filename))
    return {key: (value.item() if hasattr(value, 'item') else value) for (key, value) in collection_info.items()}


def get_dataset_paths(filename):
    paths = []
    with h5py.File(filename, 'r') as infile:
        iterate_dataset_paths(infile, paths)
    return paths


#  Can raise exceptions!
def get_csv(filename, path):
    print('get_csv')
    print(filename)
    print(path)
    with h5py.File(filename, 'r') as infile:
        dataset = infile[str(path)].value
    s = StringIO()
    if dataset is not None:
        for row in dataset:
            s.write(convert_row(row))
            s.write('\n')
        return s.getvalue()
    raise ValueError('File or path not found')


def convert_row(row):
    if isinstance(row, bytes):
        return row.decode('ascii')
    else:
        return ','.join([convert_cell(cell) for cell in row])


def convert_cell(cell):
    return cell.decode('ascii') if isinstance(cell, bytes) else str(cell)


def iterate_dataset_paths(group, paths):
    [iterate_dataset_paths(group[key], paths) for key in group.keys() if isinstance(group[key], h5py.Group)]
    paths.extend([get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)])


def get_group_info(group):
    return {
        'path': group.name,
        'attrs': {key: (value.decode('UTF-8') if isinstance(value, bytes) else value) for key, value in group.attrs.items()},
        'groups': [get_group_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Group)],
        'datasets': [get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)]
    }


def get_dataset_info(dataset):
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
        'attrs': {key: (value.decode('UTF-8') if isinstance(value, bytes) else value) for key, value in dataset.attrs.items()},
        'rows': rows,
        'cols': cols,
        'dtype': str(dataset.dtype)
    }


def update_metadata(filename, new_data):
    with h5py.File(filename, 'r+') as file:
        file.attrs.update(new_data)
    return get_collection_info(filename)

