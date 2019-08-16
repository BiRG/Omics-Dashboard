#!/usr/bin/env python3
# python3 get_collection.py collection_id auth_token

import sys
from omics_dashboard_client import Session, Collection
import shutil

collection_id = int(sys.argv[1])
omics_url = sys.argv[2]
auth_token = sys.argv[3]
session = Session(omics_url, auth_token=auth_token)
print(collection_id)
collection = session.get(Collection, collection_id, True)
collection.set_attr('collection_id', collection_id)
shutil.copy(collection.local_filename, f'{collection_id}.h5')
