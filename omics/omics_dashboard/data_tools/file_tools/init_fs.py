#!/usr/bin/env python3
import os


def initialize_fs() -> None:
    """Create the necessary directories for data to be stored"""
    """If the default Docker configuration is used, this will be unnecessary"""
    datadir = os.environ['DATADIR']
    paths = [
        f'{datadir}/samples',
        f'{datadir}/collections',
        f'{datadir}/logs'
    ]
    [os.makedirs(path, exist_ok=True) for path in paths]


if __name__ == '__main__':
    # test1.py executed as script
    # do something
    initialize_fs()
