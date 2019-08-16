#!/usr/bin/env python3
# python3 get_csv.py collection path
# collection is hdf5

from os.path import splitext
import sys
from omics_dashboard_client.hdf_tools.collection_tools import get_dataset
import numpy as np

filename = sys.argv[1]
path = sys.argv[2]

dataset = get_dataset(filename, path, True)
np.savetxt(f'{splitext(filename)[0].replace("/", "_")}.csv', dataset, delimiter=',')
