#!/usr/bin/env python3
import sys
import h5py
import numpy as np
import shutil
import os
filename = sys.argv[1]
frequency = np.float64(sys.argv[2])
outfile = os.environ['HOME'] + '/out.h5'
shutil.copy(filename, outfile)
with h5py.File(outfile, 'r+') as file:
    file['x'][:] = file['x'][:] / frequency
