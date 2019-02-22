import numpy as np
import h5py


# value is a list
# converts anything numeric into a float
def process_metadata_value(value):
    if len(value) < 2:
        return ''
    try:
        return int(value[1])
    except ValueError:
        try:
            return float(value[1])
        except ValueError:
            return value[1]


# a function to parse txtXY files
# will parse files with or without metadata
# probably pretty inefficient, but easy to read :)
def parse_txt_xy(filename):
    with open(filename, "r") as file:
        raw_data=file.readlines()
        # strip all whitespace except tabs
        raw_data = [s.replace(" ", "") for s in raw_data]
        # get metadata fields
        split_numeric = [s.split('\t') for s in raw_data if s[0] == '-' or ord(s[0]) in range(ord('0'), ord('9'))]
        split_metadata = [s[1:].replace("\n", "").split(':') for s in raw_data if s[0] == '$']
        data = np.asarray(split_numeric).astype(np.double)
        data = np.transpose(data) # vertical in the input, horizontal in output
        metadata_keys = [line[0] for line in split_metadata]
        metadata_values = [process_metadata_value(line) for line in split_metadata]
        metadata = dict(zip(metadata_keys, metadata_values))
        return {'data': data, 'metadata': metadata}


# will save a sample file, assuming that the first row is x and subsequent rows are Y
# numData is numpy array, metadata is dictionary
def save_sample_file(filename, numData, metadata):
    # clean metadata of empty entries:
    metadata = {key: value for key, value in metadata.items() if value != ''}
    with h5py.File(filename, 'w') as outfile:
        outfile.create_dataset('x', data=numData[0, :].astype(np.double)[None, :])
        outfile.create_dataset('Y', data=numData[1:, :].astype(np.double))
        for key, value in metadata.items():
            if isinstance(value, str):
                outfile.attrs[key] = np.string_(value)
            else:
                outfile.attrs[key] = value


