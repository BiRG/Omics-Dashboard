#!/usr/bin/env python3
import numpy as np
import shutil
import sys
import NMRproc

filename = sys.argv[1]
frequency = np.float64(sys.argv[2])
reference = np.float64(sys.argv[3])
x_window = np.float64(sys.argv[4])
shutil.copy(filename, 'out.h5')

NMRproc.scale('out.h5', frequency)
# NMRproc.reference('out.h5', reference, x_window) # this breaks some workflows
