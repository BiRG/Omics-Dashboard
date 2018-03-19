#!/usr/bin/env python3
import h5py
import os
import sys
import json
import shutil

def update_metadata(filename, new_data):
    with h5py.File(filename, 'r+') as file:
        file.attrs.update(new_data)


input_filenames = sys.argv[1:len(sys.argv) - 2]
metadata_file = sys.argv[len(sys.argv) - 2]
base_dir = sys.argv[len(sys.argv) - 1]

with open(metadata_file, 'r') as f:
    metadata = json.load(f)

ids = []
for file in os.listdir(base_dir):
    try:
        ids.append(int(os.path.splitext(file)[0]))
    except Exception:
        sys.exc_clear()

collection_id_start = 0 if not ids else max(ids) + 1
collection_ids = [i for i in range(collection_id_start, collection_id_start + len(input_filenames))]
output_filenames = [f'{os.environ["HOME"]}/{collection_id}.h5' for collection_id in collection_ids]
[shutil.copy(input_filename, output_filename) 
        for input_filename, output_filename in zip(input_filenames, output_filenames)]
[update_metadata(output_filename, metadata) for output_filename in output_filenames]
sys.exit(0)
