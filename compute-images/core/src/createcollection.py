#!/usr/bin/env python3
import h5py
import os
import numpy as np
import sys
import json
import metadatatools
from io import StringIO
import shutil

def is_valid(name):
    try:
        int(name)
        return True
    except ValueError:
        return False

input_file = sys.argv[1]
metadata_file = sys.argv[2]
base_dir = sys.argv[3]
with open(metadata_file, 'r') as f:
    metadata = json.load(f)
print(os.path.splitext(file)[0] for file in os.listdir(base_dir))
ids = [int(os.path.splitext(file)[0]) for file in os.listdir(base_dir) if is_valid(file)]
collection_id = 0 if not ids else max(ids) + 1
output_file = f'{os.environ["HOME"]}/{collection_id}.h5'
shutil.copy(input_file, output_file)
metadatatools.update_metadata(output_file, metadata)