import pathlib
import shutil
import tempfile
from typing import Union, List, Dict

from flask_login import current_user
from wand.image import Image
import cairosvg
import plotly.io as pio
import os
import msgpack
import dash_bootstrap_components as dbc
import dash_html_components as html
import pandas as pd
import numpy as np
from sklearn.utils.multiclass import type_of_target

import data_tools.redis_config as rds
from data_tools.rq_config import rq
from data_tools.access_wrappers.collections import get_collection_copy
from data_tools.config import TMPDIR


class DashboardModel:
    _redis_prefix = ''
    _empty_plot_data = {}

    def __init__(self, load_data=False):
        # any of these can be None
        self._label_df = None
        self._processed_label_df = None
        self._numeric_df = None
        self._x = None
        self._x_min = None
        self._x_max = None
        self._loaded_collection_ids = []
        self._dataframe_filename = None
        self._results_filename = None
        self._good_x_inds = None
        self.load_file_info()
        if load_data:
            try:
                self.load_dataframes()
            except Exception:
                self._label_df = self._processed_label_df = self._numeric_df = None

    @property
    def labels(self):
        self.load_labels()
        return [val for val in self._label_df.columns] if self._label_df is not None else []

    @property
    def unique_vals(self):
        self.load_labels()
        return {label: self._label_df[label].unique() for label in self._label_df.columns}

    def query_exists(self, query):
        self.load_labels()
        return len(self._label_df.query(query)) > 0

    @property
    def root_dir(self):
        try:
            return os.path.dirname(self._dataframe_filename)
        except:
            try:
                return os.path.dirname(self._results_filename)
            except:
                return TMPDIR

    @property
    def redis_prefix(self):
        return self._redis_prefix

    def load_file_info(self):
        data_frame_filename = rds.get_value(f'{self._redis_prefix}_dataframe_filename')
        self._dataframe_filename = data_frame_filename.decode('utf-8') if data_frame_filename is not None else None
        if not self._dataframe_filename or not os.path.isfile(self._dataframe_filename):
            rds.delete_value(f'{self._redis_prefix}_dataframe_filename')
            self._dataframe_filename = None
        try:
            self._loaded_collection_ids = msgpack.loads(rds.get_value(f'{self._redis_prefix}_loaded_collection_ids'))
        except TypeError:
            self._loaded_collection_ids = []

    def set_file_info(self):
        rds.set_value(f'{self._redis_prefix}_dataframe_filename', self._dataframe_filename.encode('utf-8'))
        rds.set_value(f'{self._redis_prefix}_loaded_collection_ids', msgpack.dumps(self._loaded_collection_ids))

    def load_dataframes(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._numeric_df = pd.read_hdf(self._dataframe_filename, 'numeric_df')

    def save_dataframes(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')
        self._numeric_df.to_hdf(self._dataframe_filename, 'numeric_df', mode='a')

    def load_labels(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')

    def save_labels(self):
        self._label_df.to_hdf(self._dataframe_filename, 'label_df', mode='a')

    def get_collections(self, collection_ids: Union[List[int], int]):
        data_dir = os.path.dirname(self._dataframe_filename) if self._dataframe_filename is not None else None
        if data_dir is not None:
            shutil.rmtree(data_dir)
        if not isinstance(collection_ids, list):
            collection_ids = [collection_ids]
        collections = [get_collection_copy(current_user, collection_id) for collection_id in collection_ids]
        if len(collections) > 1:
            collections[0].merge(collections[1:])
            collection = collections[0]
        elif len(collections) == 1:
            collection = collections[0]
        else:
            collection = None
        if collection is not None:
            x = collection.get_dataset('x')
            inds = np.argsort([float(val) for val in x.flatten()])
            y = collection.get_dataset('Y')
            collection.set_dataset('x', x[:, inds])
            collection.set_dataset('Y', y[:, inds])
            try:
                x_min = collection.get_dataset('x_min')[:, inds]
                collection.set_dataset('x_min', x_min)
                self._x_min = x_min
            except:
                self._x_min = None
            try:
                x_max = collection.get_dataset('x_max')[:, inds]
                collection.set_dataset('x_max', x_max)
                self._x_max = x_max
            except:
                self._x_max = None
            del y
            data_dir = os.path.dirname(collection.filename)
            self._results_filename = os.path.join(data_dir, 'results.h5')
            self._dataframe_filename = os.path.join(data_dir, 'dataframes.h5')
            self._loaded_collection_ids = collection_ids
            self._label_df = collection.get_dataframe(include_only_labels=True)
            self._numeric_df = collection.get_dataframe(numeric_columns=True, include_labels=False)
            self._good_x_inds = np.where(self._numeric_df.isnull().sum() == 0)[0]
            self._numeric_df = self._numeric_df[self._numeric_df.columns[self._good_x_inds]]
            self._x = x[:, self._good_x_inds]
            self._x_min = self._x_min[:, self._good_x_inds] if self._x_min is not None else None
            self._x_max = self._x_max[:, self._good_x_inds] if self._x_max is not None else None
            self._processed_label_df = self._label_df
            os.remove(collection.filename)
            self.set_file_info()
            self.save_dataframes()

    def get_collection_badges(self) -> List[html.Span]:
        return [
            html.Span([dbc.Badge(f'{collection_id}', className='badge-pill', color='primary'), ' '])
            for collection_id in self._loaded_collection_ids
        ] if self._loaded_collection_ids else [html.Span([dbc.Badge('None', className='badge-pill')])]

    def get_collection_load_info(self) -> str:
        return f'Collections loaded in {os.path.dirname(self._dataframe_filename)}'

    def load_dataframes(self):
        self._label_df = pd.read_hdf(self._dataframe_filename, 'label_df')
        self._numeric_df = pd.read_hdf(self._dataframe_filename, 'numeric_df')

    @staticmethod
    def reference_image_size(width, height, units, dpi):
        if units == 'in':
            return width * 96, height * 96
        elif units == 'cm':
            return width * 96 / 2.54, height * 96 / 2.54
        elif units == 'px':
            return width * 96 / dpi, height * 96 / dpi
        else:
            raise ValueError(f'Improper value for units: {units}.')

    def save_figure(self, figure, file_format, width, height, units, dpi, filename=None):
        pio.orca.config.use_xvfb = True
        if filename is None:
            filename = f'{",".join([str(col_id) for col_id in self._loaded_collection_ids])}.{file_format}'
            filename = os.path.join(self.root_dir, filename)
        # set width and height from 96 dpi standard density
        # this is just for the svg
        width, height = self.reference_image_size(width, height, units, dpi)
        figure['layout']['width'] = width
        figure['layout']['height'] = height
        if file_format in ('svg', 'pdf'):
            # these are vector formats directly supported by orca
            # because they're vector formats we don't worry about scale
            pio.write_image(figure, filename, height=int(height), width=int(width))
        elif file_format == 'eps':
            tmp_name = os.path.join(self.root_dir, 'tmp.svg')
            pio.write_image(figure, tmp_name, height=int(height), width=int(width))
            cairosvg.svg2ps(url=tmp_name, write_to=filename)
            os.remove(tmp_name)
        else:
            # TIFF or JPG or PNG, need to use ImageMagick to set DPI
            tmp_name = os.path.join(self.root_dir, 'tmp.png')  # PNG is lossless so we should be ok
            pio.write_image(figure, tmp_name, height=int(height), width=int(width), scale=dpi/96)
            with Image(filename=tmp_name, resolution=dpi) as img:
                img.save(filename=filename)
            os.remove(tmp_name)
        return filename

    def get_label_data(self, with_type=False) -> List[Dict[str, str]]:
        self.load_dataframes()
        types = {
            label: f' ({type_of_target(self._label_df[label])})'
            for label in self.labels
        } if with_type else {
            label: ''
            for label in self.labels
        }
        return [{'label': f'{label}{types[label]}', 'value': label} for label in self.labels]


def save_figure(figure, file_format, width, height, units, dpi, filename):
    pio.orca.config.use_xvfb = True
    # set width and height from 96 dpi standard density
    # this is just for the svg
    width, height = DashboardModel.reference_image_size(width, height, units, dpi)
    figure['layout']['width'] = width
    figure['layout']['height'] = height

    # create parent directory if it does not exist
    pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)
    if file_format in ('svg', 'pdf'):
        # these are vector formats directly supported by orca
        # because they're vector formats we don't worry about scale
        pio.write_image(figure, filename.as_posix(), height=int(height), width=int(width))
    elif file_format == 'eps':
        tmp_name = tempfile.mktemp('.svg')
        pio.write_image(figure, tmp_name, height=int(height), width=int(width))
        cairosvg.svg2ps(url=tmp_name, write_to=filename.as_posix())
        os.remove(tmp_name)
    else:
        # TIFF or JPG or PNG, need to use ImageMagick to set DPI
        tmp_name = tempfile.mktemp('.png')
        pio.write_image(figure, tmp_name, height=int(height), width=int(width), scale=dpi/96)
        with Image(filename=tmp_name, resolution=dpi) as img:
            img.save(filename=filename.as_posix())
        os.remove(tmp_name)
    return filename


@rq.job
def save_figures(figure_data, file_formats, width, height, units, dpi, output_dir, redis_hash_name, redis_prefix):
    archive_name = pathlib.Path(output_dir).with_suffix('.zip')
    output_path = pathlib.Path(output_dir)
    n_steps = len(figure_data) * len(file_formats) + 1
    progress = 0
    rds.set_value(f'{redis_prefix}_image_save_progress', 0, redis_hash_name)
    rds.set_value(f'{redis_prefix}_image_save_progress_fraction', f'0/{n_steps}', redis_hash_name)
    rds.set_value(f'{redis_prefix}_image_save_label', 'Saving images', redis_hash_name)
    i = 0
    for file_format in file_formats:
        format_path = output_path.joinpath(file_format)
        format_path.mkdir(parents=True, exist_ok=True)
        for name, figure in figure_data.items():
            path = format_path.joinpath(name).with_suffix(f'.{file_format}')
            rds.set_value(f'{redis_prefix}_image_save_label', f'Saving {path.name}', redis_hash_name)
            progress += 100 / n_steps
            save_figure(figure, file_format, width, height, units, dpi, path)
            i += 1
            rds.set_value(f'{redis_prefix}_image_save_progress', progress, redis_hash_name)
            rds.set_value(f'{redis_prefix}_image_save_progress_fraction', f'{i}/{n_steps}', redis_hash_name)
    rds.set_value(f'{redis_prefix}_image_save_label', f'Creating archive {archive_name}', redis_hash_name)
    out_filename = shutil.make_archive(output_path, 'zip', output_path.parent, output_path.stem)
    shutil.rmtree(output_path)
    rds.set_value(f'{redis_prefix}_image_save_progress', 100, redis_hash_name)
    rds.set_value(f'{redis_prefix}_image_save_progress_fraction', f'{n_steps}/{n_steps}', redis_hash_name)
    rds.set_value(f'{redis_prefix}_image_save_label', f'Created archive {archive_name}', redis_hash_name)
    return out_filename
