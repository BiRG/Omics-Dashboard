import os
import h5py
import data_tools.file_tools.metadata_tools as mdt


class AuthException(Exception):
    pass


def validate_file(path: str) -> bool:
    """
    Check if the file is an HDF5 and that it has the required attributes
    :param path:
    :return:
    """
    if h5py.is_hdf5(path):
        required_attrs = {'owner', 'name', 'description', 'groupPermissions', 'allPermissions', 'userGroup'}
        return required_attrs.issubset(set(mdt.get_collection_info(path).keys()))
    else:
        print("not HDF5")
    return False


def get_next_id(path: str) -> int:
    """
    Find a numeric id that does not exist in the directory and is one greater than the highest id.
    :param path:
    :return:
    """
    files = os.listdir(path)
    if not files:
        return 0
    ids = [int(os.path.splitext(file)[0]) for file in files]
    return 0 if ids is None else max(ids) + 1


DATADIR: str = os.environ['DATADIR']
TMPDIR: str = os.environ['TMPDIR'] if 'TMPDIR' in os.environ else '/tmp'
COMPUTESERVER: str = os.environ['COMPUTESERVER']
MODULEDIR: str = os.environ['MODULEDIR'] if 'MODULEDIR' in os.environ else DATADIR + '/modules'
UPLOADDIR: str = f'{TMPDIR}/uploads'


class LoginError(Exception):
    pass
