import numpy as np
import h5py


# value is a list
# converts anything numeric into a float
def processMetadataValue(value):
    if len(value) < 2:
        return ''
    try:
        return float(value[1])
    except ValueError:
        return value[1]


# a fuction to parse txtXY files
# will parse files with or without metadata
# probably pretty inefficient, but easy to read :)
def parseTxtXY(filename):
    with open(filename, "r") as file:
        rawdata=file.readlines()
        # strip all whitespace except tabs
        rawdata = [s.replace(" ", "") for s in rawdata]
        # get metadata fields
        splitNumeric = [s.split('\t') for s in rawdata if s[0] == '-' or ord(s[0]) in range(ord('0'), ord('9'))]
        splitMetadata = [s[1:].replace("\n", "").split(':') for s in rawdata if s[0] == '$']
        data = np.asarray(splitNumeric).astype(np.double)
        metadataKeys = [line[0] for line in splitMetadata]
        metadataValues = [processMetadataValue(line) for line in splitMetadata]
        metadata = dict(zip(metadataKeys, metadataValues))
        return {'data': data, 'metadata': metadata}


# will save a sample file, assuming that the first row is x and subsequent rows are Y
# numData is numpy array, metadata is dictionary
def saveSampleFile(filename, numData, metadata):
    # clean metadata of empty entries:
    metadata = {key: value for key, value in metadata.items() if value != ''}
    with h5py.File(filename, 'w') as outfile:
        outfile.create_dataset('x', data=numData[:, 0].astype(np.double)[:, None])
        outfile.create_dataset('Y', data=numData[:, 1:].astype(np.double))
        for key, value in metadata.items():
            if isinstance(value, str):
                outfile.attrs[key] = np.string_(value)
            else:
                outfile.attrs[key] = value


