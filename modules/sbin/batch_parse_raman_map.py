#!/usr/bin/env python3
import sys
import raman_text_parsers as tp
import os
in_filenames = [f for f in sys.argv[1:len(sys.argv)-1] if f != 'manifest.csv']
name_prefix = sys.argv[len(sys.argv)-1]
for in_filename in in_filenames:
    out_filename = f'{os.environ["HOME"]}/{os.path.basename(in_filename)}.h5'
    tp.save_map_sample_file(in_filename, out_filename, name_prefix)
sys.exit(0)
