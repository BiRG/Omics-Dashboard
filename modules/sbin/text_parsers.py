import numpy as np
import h5py
import io


# value is a list
# converts anything numeric into a float
def process_metadata_value(value):
    if len(value) < 2:
        return ''
    if value[0] in {'name', 'description'}:
        return value[1]
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
    with io.open(filename, 'r', encoding='ascii', errors='ignore') as file:
        raw_data = [s.replace(' ', '') for s in file]
    
    split_numeric = [s.split('\t') for s in raw_data if s[0] == '-' or ord(s[0]) in range(ord('0'), ord('9') + 1)]
    split_metadata = [s[1:].replace("\n", "").split(':') for s in raw_data if s[0] == '$']
    data = np.asarray(split_numeric).astype(np.double)
    data = np.transpose(data) # vertical in the input, horizontal in output

    reserved_keys = {
        'id', 
        'group_can_read',  'group_can_write', 'all_can_read', 'all_can_write',
        'user_group', 'user_group_id',
        'owner', 'owner_id',
        'creator', 'creator_id',
        'last_editor', 'last_editor_id',
        'created_on', 'updated_on'
    }

    metadata = {line[0]: process_metadata_value(line) for line in split_metadata if line[0] not in reserved_keys}

    #metadata = {key: value for key, value in metadata if key not in reserved_keys}
    return {'data': data, 'metadata': metadata}


def parse_jcamp(filename):
    from jcamp import JCAMP_reader
    reserved_keys = {
        'id', 
        'group_can_read',  'group_can_write', 'all_can_read', 'all_can_write',
        'user_group', 'user_group_id', 'owner', 'owner_id',
        'creator', 'creator_id', 'last_editor', 'last_editor_id',
        'created_on', 'updated_on',
        'x', 'y', 'jcampdx', 'xydata', 'filename', 'data type', 'data class', ''
    }
    all_data = JCAMP_reader(filename)
    metadata = {k: v for k, v in all_data.items() if k not in reserved_keys and not k.startswith('$')}
    return {'data': np.vstack([all_data['x'], all_data['y']]), 'metadata': metadata}


# will save a sample file, assuming that the first row is x and subsequent rows are Y
# numeric_data is numpy array, metadata is dictionary
def save_sample_file(filename, numeric_data, metadata):
    # clean metadata of empty entries:
    metadata = {key: value for key, value in metadata.items() if value != ''}
    with h5py.File(filename, 'w') as out_file:
        out_file.create_dataset('x', data=numeric_data[0, :].astype(np.double)[None, :])
        out_file.create_dataset('Y', data=numeric_data[1:, :].astype(np.double))
        for key, value in metadata.items():
            if isinstance(value, str):
                out_file.attrs[key] = np.string_(value)
            else:
                out_file.attrs[key] = value


