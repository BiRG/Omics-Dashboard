#!/usr/bin/env python3
import sys
import text_parsers as tp
import os
import pandas as pd

filenames = sys.argv[1:len(sys.argv)-1]
name_prefix = sys.argv[len(sys.argv)-1]

has_manifest = any([os.path.basename(f)=='manifest.csv' for f in filenames])

if has_manifest:
    manifest_filename = [f for f in filenames if os.path.basename(f)=='manifest.csv'][0]
    filenames = [f for f in filenames if os.path.basename(f)!='manifest.csv']
    manifest = pd.read_csv(manifest_filename, index_col=0)

for filename in filenames:
    out_filename = f'{os.environ["HOME"]}/{os.path.basename(filename)}.h5'
    data = tp.parse_jcamp(filename)
    metadata = data['metadata']
    numeric_data = data['data']
    metadata['name'] = f'{name_prefix}: {os.path.basename(filename)}'
    
    if has_manifest:
        base_filename = os.path.basename(filename)
        additional_metadata = manifest.loc[base_filename].to_dict()
        metadata = {**additional_metadata, **metadata}
    tp.save_sample_file(out_filename, numeric_data, metadata)
sys.exit(0)
