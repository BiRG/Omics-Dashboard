import h5py
import os


def get_collection_info(filename):
    infile = h5py.File(filename, "r")
    collection_info = get_group_info(infile)
    collection_id = os.path.splitext(os.path.basename(filename))[0]
    collection_info["id"] = int(collection_id)
    collection_info.update(collection_info["attrs"])
    del collection_info["attrs"]
    collection_info["dateModified"] = int(os.path.getmtime(filename))
    infile.close()
    return {key: (value.item() if hasattr(value, 'item') else value) for (key, value) in collection_info.items()}


def get_group_info(group):
    return {
        "path": group.name,
        "attrs": {key: (value.decode('UTF-8') if isinstance(value, bytes) else value) for key, value in group.attrs.items()},
        "groups": [get_group_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Group)],
        "datasets": [get_dataset_info(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)]
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
        "path": dataset.name,
        "attrs": {key: (value.decode('UTF-8') if isinstance(value, bytes) else value) for key, value in dataset.attrs.items()},
        "rows": rows,
        "cols": cols,
        "dtype": str(dataset.dtype)
    }


def update_metadata(filename, new_data):
    with h5py.File(filename, "r+") as file:
        file.attrs.update(new_data)
    return get_collection_info(filename)

