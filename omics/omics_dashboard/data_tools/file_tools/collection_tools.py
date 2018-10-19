import h5py
import numpy as np
import pandas as pd
from io import StringIO
def get_dataframe(filename: str) -> str:
    """Get a string containing a CSV of a pandas dataframe of a collection"""
    """Note: this requires that there be datasets /Y and /x corresponding to an x-axis and y-values for that axis"""
    # TODO: make this not require datasets called /x and /Y
    buf = StringIO()
    with h5py.File(filename, 'r') as file:
        index = np.asarray(file['/baseSampleId']).flatten() if '/baseSampleId' in file else [i for i in range(0, file['/x'].shape[0]) ]
        additional_columns = [key for key in file.keys() if key != 'baseSampleId' and file[key].shape[1] == 1 and file[key].shape[0] == file['/Y'].shape[0]]
        
        df = pd.DataFrame(data=np.asarray(file['/Y']),
                          columns=np.asarray(file['/x']).flatten(),
                          index=index)
        df.index.name = 'baseSampleId'
        # collect additional columns
        for key in additional_columns:
            if file[key].dtype.type is np.string_:
                df[key] = [row.decode('utf-8') for row in np.asarray(file[key]).flatten()]
            else:
                df[key] = file[key]
    df.to_csv(buf)
    return buf.getvalue()
