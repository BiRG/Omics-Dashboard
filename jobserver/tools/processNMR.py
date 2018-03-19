#!/usr/bin/env python3
import numpy as np
import shutil
import sys
import NMRproc
import os

filename = sys.argv[1]
frequency = np.float64(sys.argv[2])
reference = np.float64(sys.argv[3])
x_window = np.float64(sys.argv[4])
outfilename = f'{os.environ["HOME"]}/out.h5'
shutil.copy(filename, outfilename)

NMRproc.scale(outfilename, frequency)
# NMRproc.reference('out.h5', reference, x_window) # this breaks some workflows
