#!/usr/bin/env python3
#python3 getcsv.py collection path
#collection is hdf5
import h5py
import numpy
from os.path import basename
filename = f'{basename(path)}.csv'
with h5py.File(collection, 'r') as file:
    arr = numpy.asarray(file[path])
    numpy.savetxt(filename, arr, delimiter=",")
    