#!/usr/bin/env python3
# python3 getcollection.py collection_id auth_token
import os
import sys
from requests import get
collection_id = int(sys.argv[1])
omics_url = sys.argv[2]
auth_token = f'JWT {sys.argv[3]}'
res = get(f'{omics_url}/api/collections/{collection_id}',
	  headers={'Authorization': auth_token})
with open(f'{collection_id}.h5', 'wb') as outfile:
    shutil.copyfileobj(response.raw, outfile)
