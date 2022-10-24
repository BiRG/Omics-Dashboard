#!/usr/bin/env python3
import sys
import raman_text_parsers as tp
import os
import pandas as pd
from itertools import takewhile


in_filenames = [f for f in sys.argv[1:len(sys.argv) - 1] if not f.endswith('manifest.csv')]
manifest_filenames = [f for f in sys.argv[1:len(sys.argv) - 1] if f.endswith('manifest.csv')]
name_prefix = sys.argv[len(sys.argv)-1]

manifest = pd.concat([pd.read_csv(f, index_col=0) for f in manifest_filenames])
# get common prefix of all files (in the Omics Dashboard service such a common prefix exists)
# filenames in the manifest index are based on this common prefix
prefix = ''.join(c[0] for c in takewhile(lambda x: all(x[0] == y for y in x), zip(*in_filenames)))
basename_prefix = ''.join(c[0] for c in takewhile(lambda x: all(x[0] == y for y in x), zip(*manifest.index)))
if len(basename_prefix):
    manifest.index = [prefix[:-len(basename_prefix)] + i for i in manifest.index]
else:
    manifest.index = [prefix + i for i in manifest.index]
manifest = manifest.loc[pd.unique(manifest.index)]

print(manifest.to_string())
print('\n'.join(in_filenames))

for in_filename in in_filenames:
    out_filename = f'{os.environ["HOME"]}/{os.path.basename(in_filename)}.h5'
    attrs = manifest.loc[in_filename].to_dict()
    tp.save_point_sample_file(in_filename, out_filename, name_prefix, attrs)
sys.exit(0) 
