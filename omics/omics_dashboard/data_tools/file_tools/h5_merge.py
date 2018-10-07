import h5py
import os
import numpy as np
from typing import List, Set


def get_paths(group: h5py.Group, path: str) -> Set[str]:
    """Recursively find all the paths of Datasets which are children of this group"""
    """The first call should have an empty string for path"""
    out = set()
    for key in group.keys():
        if isinstance(group[key], h5py.Group):
            out |= get_paths(group[key], f'{path}/{key}')
        if isinstance(group[key], h5py.Dataset):
            out.add(f'{path}/{key}')
    return out


def paths_agree(file1: h5py.File, file2: h5py.File, path: str, dim: int) -> bool:
    """Check if the paths in two files have the same size in the specified dimension"""
    try:
        return (path in file1) and (path in file2) and file1[path].shape[dim] == file2[path].shape[dim]
    except IndexError:
        # 1D arrays do weird things
        return len(file1[path].shape) == len(file2[path].shape) == dim == 1


def get_range(files: List[h5py.File], path: str) -> (int, int):
    """Get the smallest and largest values of the datasets with the specified path in the files"""
    extrema = [(min(file[path][:]), max(file[path][:])) for file in files]
    return max([val[0] for val in extrema]), min([val[1] for val in extrema])


def h5_merge(infilenames: list, outfilename: str, orientation: str="horiz", reserved_paths: list=list(),
             sort_by: str='baseSampleId', align_at: str=None) -> None:
    """Merge a list of hdf5 files into a single file"""
    files = [h5py.File(filename, "r", driver="core") for filename in infilenames]

    # collect all common paths between the files
    dim_ind = 1
    concat_axis = 0

    paths = set()
    for file in files:
        paths |= get_paths(file, "")

    merge_attrs = set(
        item for entry in files for item in entry.attrs.keys() if all(item in entry.attrs for entry in files)
    )

    alignment_paths = set(
        path for path in paths
        if all(file[path].shape[dim_ind] == file[align_at].shape[dim_ind] for file in files)
    ) if align_at is not None else set()

    merge_paths = set(
        path for path in paths
        if path not in alignment_paths and path is not align_at
        and all(path in file and paths_agree(file, files[0], path, dim_ind) for file in files)
    )

    outfile = h5py.File(outfilename, "w", driver="core")

    # plain concatenation
    for path in merge_paths:
        if path in reserved_paths:
            outfile.create_dataset(path,
                                   data=files[0][path],
                                   maxshape=(None, None))
        else:
            outfile.create_dataset(path,
                                   data=np.concatenate([file[path] for file in files], axis=concat_axis),
                                   maxshape=(None, None))
    # handle alignment of vectors
    if align_at is not None:
        align_min, align_max = get_range(files, align_at)
        for path in alignment_paths:
            arrs = [(np.array(file[align_at]), np.array(file[path])) for file in files]
            # indices for every file
            indices = [np.where(np.logical_and(arrpair[0] >= align_min, arrpair[0] <= align_max)) for arrpair in arrs]
            outfile.create_dataset(path,
                                   data=np.concatenate([arrpair[1][ind, :]
                                                        for arrpair, ind in zip(arrs, indices)], axis=concat_axis),
                                   maxshape=(None, None))

    # have to handle some attrs differently
    ignored_attrs = ['name', 'description', 'userGroup', 'owner', 'createdBy', 'groupPermissions', 'allPermissions']
    merge_attrs = set([attr for attr in merge_attrs if attr not in ignored_attrs])
    for attr_key in merge_attrs:
        values = np.array([[file.attrs[attr_key].encode('ascii')
                            if isinstance(file.attrs[attr_key], str) else file.attrs[attr_key] for file in files]])
        values = np.transpose(values)
        np.reshape(values, (len(infilenames), 1))
        print(values.shape)
        outfile.create_dataset(attr_key, data=values, maxshape=(None, 1))
    # create a dataset which stores sample ids
    base_sample_ids = np.array([[int(os.path.basename(os.path.splitext(infilename)[0])) for infilename in infilenames]])
    # unicode datasets are not supported by all software using hdf5
    base_sample_names = np.array([[file.attrs['name'].encode('ascii')
                                 if isinstance(file.attrs['name'], str) else file.attrs['name'] for file in files]])
    base_sample_ids = np.transpose(base_sample_ids)
    base_sample_names = np.transpose(base_sample_names)
    np.reshape(base_sample_ids, (len(infilenames), 1))
    np.reshape(base_sample_names, (len(infilenames), 1))
    outfile.create_dataset('baseSampleId', data=base_sample_ids, maxshape=(None, 1))
    outfile.create_dataset('baseSampleName', data=base_sample_names, maxshape=(None, 1))
    
    # Sort everything by the specified sortBy path
    ind = np.argsort(outfile[sort_by])[0, :]
    for key in merge_attrs.intersection(merge_paths):
        if key not in reserved_paths:
            try:
                outfile[key][:] = np.asarray(outfile[key])[:, ind]
            except KeyError as e:
                print(f'Failed on key: {key}: key not found.\n{e}')
            except TypeError as e:
                print(f'failed on key: {key}: incompatible dimensions.\n{e}')
    outfile.close()
    for file in files:
        file.close()
