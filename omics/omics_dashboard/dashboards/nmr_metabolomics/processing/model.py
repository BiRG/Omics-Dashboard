import os

from flask_login import current_user
import h5py
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.colors import DEFAULT_PLOTLY_COLORS

from dashboards.dashboard_model import DashboardModel
from data_tools.db_models import collection_analysis_membership, db, Analysis
from data_tools.wrappers.collections import upload_collection, get_collection
import config.redis_config as rds
import msgpack
import birg_chemometrics_tools.normalization as nm
import birg_chemometrics_tools.baseline as bl


class CollectionProcessingModel(DashboardModel):
    _redis_prefix = 'collection_editor'
    _empty_plot_data = {}

    def __init__(self, load_data=False):
        self._processed_numeric_df = None
        self._special_numeric_df = None
        super().__init__(load_data)

    def get_collections(self, collection_ids):
        super().get_collections(collection_ids)
        try:
            self.processing_log = get_collection(current_user, collection_ids[0]).get_attr('processing_log')
        except Exception as e:
            print(e)
            self.processing_log = ''
        x = [float(i) for i in self._numeric_df.columns]
        self.x_axis_range = [max(x), min(x)]
        y_max = np.max(self._numeric_df.values)
        self.y_axis_range = [-0.05*y_max, 1.05 * y_max]

    def load_dataframes(self):
        super().load_dataframes()
        with h5py.File(self._dataframe_filename, 'r') as file:
            has_processed_label_df = 'processed_label_df' in file
            has_processed_numeric_df = 'processed_numeric_df' in file
            has_special_numeric_df = 'special_numeric_df' in file

        if has_processed_label_df:
            self._processed_label_df = pd.read_hdf(self._dataframe_filename, 'processed_label_df')
        else:
            self._processed_label_df = None
        if has_processed_numeric_df:
            self._processed_numeric_df = pd.read_hdf(self._dataframe_filename, 'processed_numeric_df')
        else:
            self._processed_numeric_df = None
        if has_special_numeric_df:
            self._special_numeric_df = pd.read_hdf(self._dataframe_filename, 'special_numeric_df')
        else:
            self._special_numeric_df = None

    def save_dataframes(self):
        super().save_dataframes()
        try:
            self._processed_label_df.to_hdf(self._dataframe_filename, 'processed_label_df', mode='a')
        except AttributeError:
            with h5py.File(self._dataframe_filename, 'r+') as file:
                if 'processed_label_df' in file:
                    del file['processed_label_df']
            pass
        try:
            self._processed_numeric_df.to_hdf(self._dataframe_filename, 'processed_numeric_df', mode='a')
        except AttributeError:
            with h5py.File(self._dataframe_filename, 'r+') as file:
                if 'processed_numeric_df' in file:
                    del file['processed_numeric_df']
        try:
            self._special_numeric_df.to_hdf(self._dataframe_filename, 'special_numeric_df', mode='a')
        except AttributeError:
            with h5py.File(self._dataframe_filename, 'r+') as file:
                if 'special_numeric_df' in file:
                    del file['special_numeric_df']

    @property
    def special_numeric_df_label(self):
        val = rds.get_value(f'{self._redis_prefix}_special_numeric_df_label')
        if val is not None:
            return val.decode('utf-8')
        return 'Special'

    @special_numeric_df_label.setter
    def special_numeric_df_label(self, value):
        value = value.encode('utf-8') if isinstance(value, str) else value
        rds.set_value(f'{self._redis_prefix}_special_numeric_df_label', value)

    @property
    def processed_numeric_df_label(self):
        val = rds.get_value(f'{self._redis_prefix}_processed_numeric_df_label')
        if val is not None:
            return val.decode('utf-8')
        return 'Processed'

    @processed_numeric_df_label.setter
    def processed_numeric_df_label(self, value):
        value = value.encode('utf-8') if isinstance(value, str) else value
        rds.set_value(f'{self._redis_prefix}_processed_numeric_df_label', value)

    @property
    def processing_log(self):
        val = rds.get_value(f'{self._redis_prefix}_processing_log')
        if val is not None:
            return val.decode('utf-8')
        return ''

    @processing_log.setter
    def processing_log(self, value):
        value = value.encode('utf-8') if isinstance(value, str) else value
        rds.set_value(f'{self._redis_prefix}_processing_log', value)

    @property
    def x_axis_range(self):
        val = rds.get_value(f'{self._redis_prefix}_x_axis_range')
        if val is not None:
            return msgpack.loads(val)
        else:
            return [12, 0]

    @x_axis_range.setter
    def x_axis_range(self, value):
        rds.set_value(f'{self._redis_prefix}_x_axis_range', msgpack.dumps(value))

    @property
    def y_axis_range(self):
        val = rds.get_value(f'{self._redis_prefix}_y_axis_range')
        if val is not None:
            return msgpack.loads(val)
        else:
            return [0, 1]

    @y_axis_range.setter
    def y_axis_range(self, value):
        rds.set_value(f'{self._redis_prefix}_y_axis_range', msgpack.dumps(value))

    @property
    def finalize_n_clicks(self):
        val = rds.get_value(f'{self._redis_prefix}_finalize_n_clicks')
        val = int(val) if val is not None else None
        return val

    @finalize_n_clicks.setter
    def finalize_n_clicks(self, value):
        rds.set_value(f'{self._redis_prefix}_finalize_n_clicks', value)

    @property
    def normalize_n_clicks(self):
        val = rds.get_value(f'{self._redis_prefix}_normalize_n_clicks')
        val = int(val) if val is not None else None
        return val

    @normalize_n_clicks.setter
    def normalize_n_clicks(self, value):
        rds.set_value(f'{self._redis_prefix}_normalize_n_clicks', value)

    @property
    def baseline_n_clicks(self):
        val = rds.get_value(f'{self._redis_prefix}_baseline_n_clicks')
        val = int(val) if val is not None else None
        return val

    @baseline_n_clicks.setter
    def baseline_n_clicks(self, value):
        rds.set_value(f'{self._redis_prefix}_baseline_n_clicks', value)

    @property
    def region_n_clicks(self):
        val = rds.get_value(f'{self._redis_prefix}_region_n_clicks')
        val = int(val) if val is not None else None
        return val

    @region_n_clicks.setter
    def region_n_clicks(self, value):
        rds.set_value(f'{self._redis_prefix}_region_n_clicks', value)

    @property
    def collection_count(self):
        return len(self._loaded_collection_ids)

    @property
    def loaded_collection_ids(self):
        return self._loaded_collection_ids

    @property
    def analysis_ids(self):
        # slightly faster, but more complicated. iterating through Collection.analyses not working in this context
        query = collection_analysis_membership.select().where(collection_analysis_membership.c.collection_id.in_(self.loaded_collection_ids))
        analysis_ids = [row[1] for row in db.engine.execute(query).fetchall()]
        return [
            analysis.id for analysis in Analysis.query.filter(Analysis.id.in_(analysis_ids)).all()
            if analysis.write_permitted(current_user)
        ]

    @property
    def x_range(self):
        if self._numeric_df is None:
            return 0, 12
        else:
            x = [float(i) for i in self._numeric_df.columns]
            return min(x), max(x)

    @property
    def x_step(self):
        try:
            return abs(float(self._numeric_df.columns[1]) - float(self._numeric_df.columns[0]))
        except (ValueError, AttributeError, IndexError):
            return 0.01

    @property
    def spectrum_count(self):
        try:
            return len(self._numeric_df)
        except TypeError:
            return 0

    @property
    def is_finalized(self):
        self.load_dataframes()
        return self._processed_numeric_df is None and self._special_numeric_df is None

    def finalize(self):
        self.load_dataframes()
        self._numeric_df = self._processed_numeric_df
        self._label_df = self._processed_label_df
        self.processing_log += f' {self.processed_numeric_df_label}.'
        self._processed_numeric_df = None
        self._special_numeric_df = None
        self.processed_numeric_df_label = None
        self.special_numeric_df_label = None
        self.save_dataframes()

    def get_plot(self, spectrum_ind, show_box, box_min, box_max, theme):
        background_color = 'rgba(255,255,255,0)'
        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }

        if show_box:
            shapes = [
                go.layout.Shape(
                    type='rect',
                    xref='x',
                    yref='paper',
                    x0=box_min,
                    y0=0,
                    x1=box_max,
                    y1=1,
                    fillcolor=DEFAULT_PLOTLY_COLORS[3],
                    opacity=0.20,
                    layer='below',
                    line_width=0
                )
            ]
        else:
            shapes = []

        layout = go.Layout(
            font={'size': 16},
            margin={'t': 25, 'l': 25, 'b': 25, 'r': 25},
            template=theme,
            plot_bgcolor=background_color,
            paper_bgcolor=background_color,
            title='',
            xaxis={
                'title': 'Chemical Shift (ppm)',
                'range': self.x_axis_range,
                **axis_line_style
            },
            yaxis={
                'title': 'Intensity',
                'range': self.y_axis_range,
                **axis_line_style
            },
            shapes=shapes
        )
        figure = go.Figure(layout=layout)

        if self._numeric_df is not None:
            spectrum_ind = spectrum_ind if spectrum_ind < len(self._numeric_df) else len(self._numeric_df) - 1
        else:
            return figure

        if self._label_df is not None:
            text = '<br>'.join([f'{label}: {self._label_df.iloc[spectrum_ind][label]}' for label in self._label_df.columns])
        else:
            text = f'Spectrum #{spectrum_ind}'
        if self._numeric_df is not None:
            figure.add_trace(
                go.Scatter(
                    x=[float(i) for i in self._numeric_df.columns],
                    y=self._numeric_df.iloc[spectrum_ind],
                    text=text,
                    name='Spectrum',
                    mode='lines',
                    marker={'size': 2}
                )
            )
        if self._processed_numeric_df is not None:
            figure.add_trace(
                go.Scatter(
                    x=[float(i) for i in self._processed_numeric_df.columns],
                    y=self._processed_numeric_df.iloc[spectrum_ind],
                    text=text,
                    name=self.processed_numeric_df_label,
                    mode='lines',
                    marker={'size': 2}
                )
            )
        if self._special_numeric_df is not None:
            figure.add_trace(
                go.Scatter(
                    x=[float(i) for i in self._special_numeric_df.columns],
                    y=self._special_numeric_df.iloc[spectrum_ind],
                    text=text,
                    name=self.special_numeric_df_label,
                    mode='lines',
                    marker={'size': 2}
                )
            )
        return figure

    def nearest_x(self, x0, x1):
        if self._numeric_df is not None:
            x = np.array([float(i) for i in self._numeric_df.columns])
            x0 = x[np.abs(x - x0).argmin()]
            x1 = x[np.abs(x - x1).argmin()]
        return sorted([x0, x1])

    def normalize(self, method, **kwargs):
        if method == 'sum':
            corrected = nm.SumNormalizer(kwargs['norm_sum']).fit_transform(self._numeric_df)
            self.processed_numeric_df_label = f'Sum normalized (sum={kwargs["norm_sum"]})'
        elif method == 'label':
            corrected = self._numeric_df / self._label_df[kwargs['norm_label']]
            self.processed_numeric_df_label = f'Normalized to {kwargs["norm_label"]}'
        elif method == 'region':
            region_columns = [column for column in self._numeric_df.columns if kwargs['region_min']
                              <= float(column) <= kwargs['region_max']]
            corrected = self._numeric_df.mul(
                kwargs['region_peak_intensity'] / self._numeric_df[region_columns].max(axis=1),
                axis=0)
            self.processed_numeric_df_label = f'Normalized to max of ({kwargs["region_min"]}, {kwargs["region_max"]})' \
                                              f' intensity={kwargs["region_peak_intensity"]}'
        elif method == 'min_max':
            corrected = nm.MinMaxNormalizer().fit_transform(self._numeric_df)
            self.processed_numeric_df_label = 'Min/max normalized'
        elif method == 'histogram':
            print(f'hist_ref_query: {kwargs["hist_ref_query"]}')
            if kwargs['hist_ref_query'] is not None:
                reference_spectra = self._numeric_df.loc[self._label_df.query(kwargs['hist_ref_query']).index]
            else:
                reference_spectra = self._numeric_df
            normalizer = nm.HistogramNormalizer(kwargs['hist_ref_type'])
            corrected = normalizer.fit(reference_spectra).transform(self._numeric_df)
            self.processed_numeric_df_label = f'Histogram (CDF) Normalized to {kwargs["hist_ref_type"]} ' \
                                              f'of {kwargs["hist_ref_query"] or "all spectra"}'
        elif method == 'probability_quotient':
            print(f'pqn_ref_query: {kwargs["pqn_ref_query"]}')
            if kwargs['pqn_ref_query'] is not None:
                reference_spectra = self._numeric_df.loc[self._label_df.query(kwargs['pqn_ref_query']).index]
            else:
                reference_spectra = self._numeric_df
            normalizer = nm.ProbabilisticQuotientNormalizer(kwargs['pqn_ref_type'])
            corrected = normalizer.fit(reference_spectra).transform(self._numeric_df)
            self.processed_numeric_df_label = f'PQ Normalized to {kwargs["pqn_ref_type"]} ' \
                                              f'of {kwargs["pqn_ref_query"] or "all_spectra"}'
        else:
            corrected = self._numeric_df.values
            self.processed_numeric_df_label = None

        self.special_numeric_df_label = None
        self._special_numeric_df = None

        self._processed_numeric_df = pd.DataFrame(data=corrected,
                                                  index=self._numeric_df.index,
                                                  columns=self._numeric_df.columns)

        self.processing_log = f'{self.processing_log} {self.processed_numeric_df_label}.'
        self.save_dataframes()

    def correct_baseline(self, method, **kwargs):
        if method == 'rolling_ball':
            rb = bl.RollingBallBaseline(kwargs['rolling_ball_min_max'],
                                        kwargs['rolling_ball_smoothing'],
                                        True)
            corrected = rb.fit_transform(self._numeric_df)
            self._processed_numeric_df = pd.DataFrame(data=corrected,
                                                      columns=self._numeric_df.columns,
                                                      index=self._numeric_df.index)
            self._special_numeric_df = pd.DataFrame(data=rb.baseline_,
                                                    columns=self._processed_numeric_df.columns,
                                                    index=self._processed_numeric_df.index)
            self.special_numeric_df_label = 'Baseline'
            self.processed_numeric_df_label = f'Rolling-ball Corrected ' \
                                              f'(wm={kwargs["rolling_ball_min_max"]},' \
                                              f' ws={kwargs["rolling_ball_smoothing"]})'
        self.processing_log = f'{self.processing_log} {self.processed_numeric_df_label}.'
        self.save_dataframes()

    def process_region(self, method, region_min, region_max):
        region_columns = [column for column in self._numeric_df.columns if region_min <= float(column) <= region_max]
        self._special_numeric_df = None
        if method == 'zero':
            print('method==zero')
            self._processed_numeric_df = self._numeric_df.copy()
            self._processed_numeric_df[region_columns] = 0
            self.processed_numeric_df_label = f'Zeroed [{region_min}, {region_max}]'
        elif method == 'crop':
            print('method==crop')
            self._processed_numeric_df = self._numeric_df[region_columns].copy()
            self.processed_numeric_df_label = f'Cropped [{region_min}, {region_max}]'
        elif method == 'delete':
            print('method==delete')
            good_columns = [column for column in self._numeric_df.columns if column not in region_columns]
            self._processed_numeric_df = self._numeric_df[good_columns].copy()
            self.processed_numeric_df_label = f'Deleted [{region_min}, {region_max}]'
        elif method == 'reference':
            print('method==reference')
            max_columns = self._numeric_df[region_columns].idxmax(axis=1)
            referenced = []
            for i in self._numeric_df.index:
                spectrum = self._numeric_df.loc[[i]]
                spectrum.columns = [float(column) - float(max_columns.loc[i]) for column in spectrum.columns]
                referenced.append(spectrum)
            self._processed_numeric_df = pd.concat(referenced).dropna(axis=1)
            self.processed_numeric_df_label = f'Referenced to [{region_min}, {region_max}]'
        self.processing_log = f'{self.processing_log} {self.processed_numeric_df_label}.'
        self.save_dataframes()

    def post_collection(self, name, analysis_ids):
        self.load_dataframes()
        parent_collections = [
            get_collection(current_user, collection_id) for collection_id in self.loaded_collection_ids
        ]
        label_df = self._label_df
        # merge collection attributes
        if len(self.loaded_collection_ids) > 1:
            collection_lengths = [
                len(self._label_df[self._label_df.original_collection_id == collection_id])
                for collection_id in self.loaded_collection_ids
            ]
            collection_attrs = [collection.get_file_attributes() for collection in parent_collections]
            all_attr_keys = set.union(*[set(collection_attr.keys()) for collection_attr in collection_attrs])
            attr_values = {
                attr_key: [
                    collection_attr[attr_key] if attr_key in collection_attr else None
                    for collection_attr in collection_attrs
                ]
                for attr_key in all_attr_keys
            }
            attrs = {}
            for attr_key, attr_values_ in attr_values.items():
                valid_values = [v for v in attr_values_ if v is not None]
                if len(valid_values) == 1:
                    attrs[attr_key] = valid_values[0]
                else:
                    vals = [[v for _ in range(length)] for v, length in zip(valid_values, collection_lengths)]
                    label_df[attr_key] = [item for sublist in vals for item in sublist]
        else:
            attrs = get_collection(current_user, self.loaded_collection_ids[0]).get_file_attributes()

        filename = os.path.join(self.root_dir, 'processed.h5')
        attrs['processing_log'] = self.processing_log
        description = '\n\n'.join([collection.description for collection in parent_collections] + [self.processing_log])

        new_data = {
            'name': name,
            'description': description,
            'analysis_ids': analysis_ids,
            'parent_collection_id': self.loaded_collection_ids[0],
            'group_can_read': all([collection.group_can_read for collection in parent_collections]),
            'all_can_read': all([collection.all_can_read for collection in parent_collections]),
            'group_can_write': all([collection.group_can_write for collection in parent_collections]),
            'all_can_write': all([collection.all_can_write for collection in parent_collections])
        }

        self.write_collection(self._numeric_df, label_df, attrs, filename)
        new_collection = upload_collection(current_user, filename, new_data)
        return new_collection
