import h5py
import os
import numpy as np
from scipy.interpolate import interp1d
from typing import List, Set, Tuple, Callable


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
    extrema = [(np.amin(file[path][:]), np.amax(file[path][:])) for file in files]
    return max([val[0] for val in extrema]), min([val[1] for val in extrema])


def interpolate(files: List[h5py.File], align_path: str, target_path: str, concat_fn: Callable) -> Tuple[np.array, np.array]:
    align_min, align_max = get_range(files, align_path)
    array_length = min([file[align_path].size for file in files])
    new_align = np.linspace(align_min, align_max, array_length)
    aligned = concat_fn([interp1d(np.ravel(file[align_path]), np.ravel(file[target_path]), assume_sorted=False)(new_align) for file in files])
    # make new_align a m x 1 or 1 x n instead of 1D
    return new_align, aligned

def h5_merge(infilenames: list, outfilename: str, orientation: str='vert', reserved_paths: list=list(),
    sort_by: str='base_sample_id', align_at: str=None) -> None:
    """
    Merge a list of hdf5 files into a single file
    :param infilenames: A list of filenames to merge
    :param outfilename: Location of output file
    :param orintation: Whether to concatenate vertically ("vert") or horizontally ("horiz")
    :param reserved_paths: Paths that are assumed identical between collections
    :param sort_by: the name of the field in the final collection to sort columns/rows by
    :param align_at: the name of the label field to sort records by
    """
    
    
    files = [h5py.File(filename, "r", driver="core") for filename in infilenames]

    # collect all common paths between the files
    concat_fn = np.vstack if orientation == 'vert' else np.hstack
    dim_ind = 1 if orientation == 'vert' else 0
    
    # if we concat vertically, labels are 1 column
    # if we concat horizontally, labels are 1 row
    label_shape = (len(infilenames), 1) if orientation=='vert' else (1, len(infilenames))
    label_maxshape = (None, 1) if orientation=='vert' else (1, None)

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
    alignment_paths.remove(align_at)

    merge_paths = set(
        path for path in paths
        if path not in alignment_paths and path is not align_at
        and all(path in file and paths_agree(file, files[0], path, dim_ind) for file in files)
    )

    with h5py.File(outfilename, "w", driver="core") as outfile:
        # handle alignment of vectors
        if align_at is not None:
            for path in alignment_paths:
                align, aligned = interpolate(files, align_at, path, concat_fn)
                align_shape = [1,1]
                align_shape[dim_ind] = align.size
                aligned_shape = [len(files), len(files)]
                aligned_shape[dim_ind] = align.size
                outfile.create_dataset(path,
                                       data=np.reshape(aligned, aligned_shape),
                                       maxshape=(None, None))
                if align_at not in outfile:
                    outfile.create_dataset(align_at,
                                           data=np.reshape(align, align_shape),
                                           maxshape=(None, None))
        # plain concatenation
        for path in merge_paths:
            if path in reserved_paths and path is not align_at:
                outfile.create_dataset(path,
                                       data=files[0][path],
                                       maxshape=(None, None))
            else:
                outfile.create_dataset(path,
                                       data=concat_fn([file[path] for file in files]),
                                       maxshape=(None, None))
        # have to handle some attrs differently
        ignored_attrs = ['name', 'description']
        merge_attrs = set([attr for attr in merge_attrs if attr not in ignored_attrs])


        for attr_key in merge_attrs:
            values = np.array([[file.attrs[attr_key].encode('ascii')
                                if isinstance(file.attrs[attr_key], str) else file.attrs[attr_key] for file in files]])
            outfile.create_dataset(attr_key, data=np.reshape(values, label_shape), maxshape=label_maxshape)
        base_sample_ids = np.array([[int(os.path.basename(os.path.splitext(infilename)[0])) for infilename in infilenames]])
        # unicode datasets are not supported by all software using hdf5
        base_sample_names = np.array([[file.attrs['name'].encode('ascii')
                                     if isinstance(file.attrs['name'], str) else file.attrs['name'] for file in files]])
        outfile.create_dataset('base_sample_id', data=np.reshape(base_sample_ids, label_shape), maxshape=label_maxshape)
        outfile.create_dataset('base_sample_name', data=np.reshape(base_sample_names, label_shape), maxshape=label_maxshape)

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
    for file in files: file.close()
