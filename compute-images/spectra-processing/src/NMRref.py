#!/usr/bin/env python3
import sys
import h5py
import numpy as np
import shutil
filename = sys.argv[1]
reference = np.float64(sys.argv[2])
shutil.copy(filename, 'out.h5')
with h5py.File('out.h5', 'r+') as file:
    file['x'][:] = file['x'][:] - reference
