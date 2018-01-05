#!/usr/bin/env python3
import sys
import h5py
import numpy as np 
filename = sys.argv[1]
frequency = np.float64(sys.argv[2])
with h5py.File(filename, 'r+') as file:
    file['x'][:] = np.array(file['Y']) / frequency

