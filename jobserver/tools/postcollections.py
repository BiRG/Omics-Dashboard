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
omics_url = sys.argv[len(sys.argv) - 2]
auth_token = f'JWT {sys.argv[len(sys.argv) - 1]}'
output = []
for output_filename in output_filenames:
    url = f'{omics_url}/api/collections/upload'
    files = {'file': open(output_filename, 'rb')}
    res = requests.post(url,
                        headers={'Authorization': auth_token},
                        files=files)
    output.append(json.loads(res.text))

print(json.dumps(output))
sys.exit(0)
