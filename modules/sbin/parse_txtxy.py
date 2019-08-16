#!/usr/bin/env python3
import sys
from .text_parsers import parse_txt_xy, save_sample_file
import os

in_filename = sys.argv[1]
out_filename = f'{os.environ["HOME"]}/{os.path.basename(in_filename)}.h5'
data = parse_txt_xy(in_filename)
save_sample_file(out_filename, data['data'], data['metadata'])
sys.exit(0)
