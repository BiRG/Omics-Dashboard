#!/usr/bin/env python3
import numpy as np
import shutil
import sys
import NMRproc
import os

filenames = sys.argv[1:len(sys.argv) - 1]
frequency = np.float64(sys.argv[len(sys.argv) - 1])
outfilenames = [f'{os.path.basename(filename)}_out.h5' for filename in filenames]
[shutil.copy(filename, outfilename) for filename, outfilename in zip(filenames, outfilenames)]
[NMRproc.scale(outfilename, frequency) for outfilename in outfilenames]
sys.exit(0)
