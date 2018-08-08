#!/usr/bin/env python3
import os

def initfs():
    DATADIR = os.environ['DATADIR']
    paths = [
        f'{DATADIR}/samples',
        f'{DATADIR}/collections',
        f'{DATADIR}/logs',
        f'{DATADIR}/sessions'
    ]
    [os.makedirs(path, exist_ok=True) for path in paths]


if __name__ == '__main__':
    # test1.py executed as script
    # do something
    initfs()
