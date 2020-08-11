import numpy as np
import h5py
import io


def parse_wide_map(filename):
    data = np.genfromtxt(filename, delimiter='\t')
    x = data[0, 2:]
    Y = data[1:, 2:]
    spatial_x = data[1:, 0]
    spatial_y = data[1:, 1]
    return x, Y, spatial_x, spatial_y


def parse_paired_text(filename):
    data = np.genfromtxt(filename, delimiter='\t')
    x = data[:, 0]
    Y = data[:, 1]
    return x, Y


def save_map_sample_file(in_filename, out_filename, prefix):
    x, Y, spatial_x, spatial_y = parse_wide_map(in_filename) 
    with h5py.File(out_filename, 'w') as out_file:
        out_file.create_dataset('x', data=x)
        out_file.create_dataset('Y', data=Y)
        out_file.create_dataset('spatial_x', data=spatial_x)
        out_file.create_dataset('spatial_y', data=spatial_y)
        out_file.attrs['name'] = f'{prefix}: {os.path.basename(in_filename)}'
        out_file.attrs['filename'] = os.path.basename(in_filename)


def save_point_sample_file(in_filename, out_filename, prefix):
    x, Y = parse_paired_text(in_filename)
    with h5py.File(out_filename, 'w') as out_file:
        out_file.create_dataset('x', data=x)
        out_file.create_dataset('Y', data=Y)
        out_file.attrs['name'] = f'{prefix}: {os.path.basename(in_filename)}'
        out_file.attrs['filename'] = os.path.basename(in_filename)

