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


def paths_agree(file1, file2, path, dim):
    try:
        return (path in file1) and (path in file2) and file1[path].shape[dim] == file2[path].shape[dim]
    except IndexError as e:
        #1D arrays do weird things
        return len(file1[path].shape) == len(file2[path].shape) == dim == 1


def h5_merge(infilenames, outfilename, orientation="horiz", reserved_paths=[]):
    files = [h5py.File(filename, "r", driver="core", libver="latest") for filename in infilenames]
    # collect all common paths between the files
    paths = set()
    for file in files:
        paths |= get_paths(file, "")
    dim_ind = 0 if orientation == "horiz" else 1
    merge_paths = [path for path in paths if all([path in file and paths_agree(file, files[0], path, dim_ind) for file in files])]
    outfile = h5py.File(outfilename, "w", driver="core", libver="latest")
    for path in merge_paths:
        concat_axis = 1 if orientation == "horiz" else 0
        if path in reserved_paths:
            outfile.create_dataset(path, data=files[0][path])
        else:
            outfile.create_dataset(path, data=np.concatenate([file[path] for file in files], axis=concat_axis))
    outfile.close()
    for file in files:
        file.close()
