#!/usr/bin/env python3
# python3 uploadsamples.py <input_filenames> metadata_filename collection_id_start auth_token

import h5py
import os
import sys
import json
import shutil
from requests import post


def update_metadata(filename, new_data):
    with h5py.File(filename, 'r+') as file:
        file.attrs.update(new_data)


input_filenames = sys.argv[1:len(sys.argv) - 5]
metadata_file = sys.argv[len(sys.argv) - 5]
collection_id_start = int(sys.argv[len(sys.argv) - 4])
wf_token = sys.argv[len(sys.argv) - 3]
omics_url = sys.argv[len(sys.argv) - 2]
auth_token = f'JWT {sys.argv[len(sys.argv) - 1]}' # every workflow that talks to the omics server should have a 'token' parameter handled by the server.


collection_ids = [i for i in range(collection_id_start, collection_id_start + len(input_filenames))]
output_filenames = [f'{os.environ["HOME"]}/{collection_id}.h5' for collection_id in collection_ids]
# we have to copy to an output directory because the reference CWL runner treats input files as immutable.
[shutil.copy(input_filename, output_filename) 
        for input_filename, output_filename in zip(input_filenames, output_filenames)]
output = []
metadata = json.load(open(metadata_file, 'r'))
if 'name' in metadata:
    del metadata['name'] # preserve name set up in previous steps
for output_filename, collection_id in zip(output_filenames, collection_ids):
    url = f'{omics_url}/api/samples/{collection_id}'
    files = {'file': open(output_filename, 'rb')}
    res = post(url,
               headers={'Authorization': auth_token},
               data=metadata,
               files=files)
    res.raise_for_status()
    output.append(json.loads(res.text))
res = post(f'{omics_url}/api/finalize', 
     	   headers={'Authorization': auth_token},
           json={'wf_token': wf_token})
if res.status_code == 500:
    print(res.json())
res.raise_for_status()
sys.exit(0)
