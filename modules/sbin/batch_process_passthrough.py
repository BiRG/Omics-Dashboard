#!/usr/bin/env python3
import numpy as np
import shutil
import sys
import os

filenames = sys.argv[1:]
out_filenames = [f'{os.path.basename(filename)}_out.h5' for filename in filenames]
[shutil.copy(filename, outfilename) for filename, outfilename in zip(filenames, out_filenames)]
sys.exit(0)
