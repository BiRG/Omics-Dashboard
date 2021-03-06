import h5py


class AuthException(Exception):
    pass


class NotFoundException(Exception):
    pass


class LoginError(Exception):
    def __init__(self, message, redirect_url=None):
        super(LoginError, self).__init__(message)
        self.redirect_url = redirect_url


def validate_file(path: str) -> bool:
    """
    Check if the file is an HDF5 file
    Modify this to allow for other file types!
    (Note some records can be text or arbitrary binary files but we don't need to validate them)
    :param path:
    :return:
    """
    return h5py.is_hdf5(path)
