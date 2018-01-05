import h5py
import numpy as np


def get_paths(group, path):
    out = set()
    for key in group.keys():
        if isinstance(group[key], h5py.Group):
            out |= get_paths(group[key], path + "/" + key)
        if isinstance(group[key], h5py.Dataset):
            out.add(path + "/" + key)
    return out


def h5_merge(infilenames, outfilename, orientation="vert"):
    files = [h5py.File(filename, "r", driver="core", libver="latest") for filename in infilenames]
    # collect all common paths between the files
    paths = set()
    for file in files:
        paths |= get_paths(file, "")
    dim_ind = 0 if orientation == "horiz" else 1
    merge_paths = [path for path in paths
                  if all([(path in file) and file[path].shape[dim_ind] == files[0][path].shape[dim_ind]
                          for file in files])]
    outfile = h5py.File(outfilename, "w", driver="core", libver="latest")
    for path in merge_paths:
        dim_ind = 1 if orientation == "horiz" else 0 # opposite of the path checking
        outfile.create_dataset(path, data=np.concatenate([file[path] for file in files], dim_ind))
    outfile.close()
    for file in files:
        file.close()
