import h5py
import os
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



def h5_merge(infilenames, outfilename, orientation="horiz", reserved_paths=[], sortBy = 'baseSampleId'):
    files = [h5py.File(filename, "r", driver="core") for filename in infilenames]
    # collect all common paths between the files
    paths = set()
    for file in files:
        paths |= get_paths(file, "")
    dim_ind = 0 if orientation == "horiz" else 1
    concat_axis = 1 if orientation == "horiz" else 0
    attr_keys = [key for key in file.attrs.keys() for file in files]
    merge_attrs = set([item for entry in files for item in entry.attrs.keys() if all(item in entry.attrs for entry in files)])
    merge_paths = [path for path in paths if all([path in file and paths_agree(file, files[0], path, dim_ind) for file in files])]
    outfile = h5py.File(outfilename, "w", driver="core")
    
    for path in merge_paths:
        if path in reserved_paths:
            outfile.create_dataset(path, data=files[0][path])
        else:
            outfile.create_dataset(path, data=np.concatenate([file[path] for file in files], axis=concat_axis))
    # have to handle some attrs differently
    ignored_attrs = ['name', 'description', 'userGroup', 'owner', 'createdBy', 'groupPermissions', 'allPermissions']
    merge_attrs = [attr for attr in merge_attrs if attr not in ignored_attrs]
    for attr_key in merge_attrs:
        values = np.array([[file.attrs[attr_key].encode('ascii') if isinstance(file.attrs[attr_key], str) else file.attrs[attr_key] for file in files]])
        np.reshape(values, (1, len(infilenames)))
        outfile.create_dataset(attr_key, data=values)
    # create a dataset which stores sample ids
    baseSampleIds = np.array([[int(os.path.basename(os.path.splitext(infilename)[0])) for infilename in infilenames]])
    # unicode datasets are not supported by all software using hdf5
    baseSampleNames = np.array([[file.attrs['name'].encode('ascii') for file in files]])
    np.reshape(baseSampleIds, (1, len(infilenames)))
    np.reshape(baseSampleNames, (1, len(infilenames)))
    outfile.create_dataset('baseSampleId', data=baseSampleIds)
    outfile.create_dataset('baseSampleName', data=baseSampleNames)
    
    # Sort everything by the specified sortBy path
    ind = np.argsort(outfile[sortBy])[0,:]
    for key in (list(merge_attrs) + merge_paths):
        if key not in reserved_paths:
            try:
                outfile[key][:] = np.asarray(outfile[key])[:,ind]
            except:
                print(f'failed on key: {key}')
    outfile.close()
    for file in files:
        file.close()
