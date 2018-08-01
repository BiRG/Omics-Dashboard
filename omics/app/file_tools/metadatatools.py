import h5py
import os
from io import StringIO


def get_collection_metadata(filename):
    with h5py.File(filename, 'r') as infile:
        attrs = {key: (value.decode('UTF-8') if isinstance(value, bytes) else value) for key, value in infile.attrs.items()}
    collection_id = os.path.splitext(os.path.basename(filename))[0]
    attrs['id'] = int(collection_id)
    attrs['dateModified'] = int(os.path.getmtime(filename))
    dims = approximate_dims(filename)
    attrs['maxRowCount'] = dims[0]
    attrs['maxColCount'] = dims[1]
    return {key: (value.item() if hasattr(value, 'item') else value) for (key, value) in attrs.items()}


def get_collection_info(filename):
    with h5py.File(filename, 'r') as infile:
        collection_info = get_group_info(infile)
    collection_id = os.path.splitext(os.path.basename(filename))[0]
    collection_info['id'] = int(collection_id)
    collection_info.update(collection_info['attrs'])
    del collection_info['attrs']
    collection_info['dateModified'] = int(os.path.getmtime(filename))
    dims = approximate_dims(filename)
    collection_info['maxRowCount'] = dims[0]
    collection_info['maxColCount'] = dims[1]
    return {key: (value.item() if hasattr(value, 'item') else value) for (key, value) in collection_info.items()}


def get_dataset_paths(filename):
    paths = []
    with h5py.File(filename, 'r') as infile:
        iterate_dataset_paths(infile, paths)
    return paths


#  Can raise exceptions!
def get_csv(filename, path):
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


def create_empty_file(filename, new_data):
    with h5py.File(filename, 'w') as file:
        file.attrs.update(new_data)
    return get_collection_info(filename)


def approximate_dims(filename):
    """ Return a (m, n) pair where m is the longest row count and n is longest col count of all datasets"""
    with h5py.File(filename, 'r') as file:
        try:
            m = max([dataset.shape[0] for dataset in get_datasets(file)])
            n = max([dataset.shape[1] if len(dataset.shape) > 1 else 1 for dataset in get_datasets(file)])
            return m, n
        except ValueError:
            return 0, 0


def get_datasets(file):
    return [file[key] for key in file.keys() if isinstance(file[key], h5py.Dataset)]
