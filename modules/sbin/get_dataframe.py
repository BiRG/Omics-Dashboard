#!/usr/bin/env python3
import sys
from os.path import splitext, basename

from omics_dashboard_client.hdf_tools.collection_tools import get_dataframe

filename = sys.argv[1]
numeric_columns = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
include_labels = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
include_only_labels = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else False

df = get_dataframe(filename,
                   include_labels=include_labels,
                   numeric_columns=numeric_columns,
                   include_only_labels=include_only_labels)
df.to_csv(f'{splitext(basename(filename))[0]}.csv')

