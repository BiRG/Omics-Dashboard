import os
import h5py


class AuthException(Exception):
    pass


class NotFoundException(Exception):
    pass


def validate_file(path: str) -> bool:
    """
    Check if the file is an HDF5 file
    Modify this to allow for other file types!
    :param path:
    :return:
    """
    return h5py.is_hdf5(path)


DATADIR: str = os.environ['DATADIR']
TMPDIR: str = os.environ['TMPDIR'] if 'TMPDIR' in os.environ else '/tmp'
COMPUTESERVER: str = os.environ['COMPUTESERVER']
MODULEDIR: str = os.environ['MODULEDIR'] if 'MODULEDIR' in os.environ else DATADIR + '/modules'
UPLOADDIR: str = f'{TMPDIR}/uploads'


class LoginError(Exception):
    def __init__(self, message, redirect_url=None):
        super(LoginError, self).__init__(message)
        self.redirect_url = redirect_url
