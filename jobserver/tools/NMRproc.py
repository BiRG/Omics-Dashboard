#!/usr/bin/env python3
import sys
import numpy as np
import h5py

def reference(filename, reference, x_window):
    ref_min = reference - x_window
    ref_max = reference + x_window
    with h5py.File('out.h5', 'r+') as file:
        sub_ind = np.where(np.logical_and(file['x'][:]<=ref_max, file['x'][:]>=ref_min))
        print(sub_ind)
        reference_ind = np.argmax(file['Y'][sub_ind, 0])
        print(reference_ind)
        file['x'][:] = file['x'][:] - reference

    
def scale(filename, frequency):
    with h5py.File(filename, 'r+') as file:
        file['x'][:] = file['x'][:] / frequency
        file.attrs['units_chemical_shift'] = 'ppm'
