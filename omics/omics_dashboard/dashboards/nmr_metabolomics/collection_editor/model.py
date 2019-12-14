import os

import dash_bootstrap_components as dbc
import dash_html_components as html
from flask_login import current_user
from flask import url_for
import pandas as pd

from dashboards.dashboard_model import DashboardModel
from data_tools.db_models import collection_analysis_membership, db, Analysis
from data_tools.wrappers.collections import upload_collection, get_collection


class CollectionEditorModel(DashboardModel):
    _redis_prefix = 'collection_editor'
    _empty_plot_data = {}

    @property
    def collection_count(self):
        return len(self._loaded_collection_ids)

    @property
    def loaded_collection_ids(self):
        return self._loaded_collection_ids

    @property
    def analysis_ids(self):
        print(f'collection_ids: {self.loaded_collection_ids}')
        # slightly faster, but more complicated. iterating through Collection.analyses not working in this context
        query = collection_analysis_membership.select().where(collection_analysis_membership.c.collection_id.in_(self.loaded_collection_ids))
        analysis_ids = [row[1] for row in db.engine.execute(query).fetchall()]
        return [
            analysis.id for analysis in Analysis.query.filter(Analysis.id.in_(analysis_ids)).all()
            if analysis.write_permitted(current_user)
        ]

    def proposed_name(self, filter_by_query, join_on_labels):
        if isinstance(join_on_labels, list):
            if len(join_on_labels) == 0:
                join_on_labels = None
        if len(self._loaded_collection_ids) > 1 and join_on_labels:
            name = 'Merged Collections ' + ' + '.join([str(cid) for cid in self._loaded_collection_ids])
        elif join_on_labels is not None:
            name = f'Collections {self._loaded_collection_ids[0]} and {self._loaded_collection_ids[1]} joined on ({", ".join(join_on_labels)})'
        else:
            name = f'Collection {self._loaded_collection_ids[0]}'

        if filter_by_query is not None:
            name += f' [{filter_by_query}]'

        return name

    def post_collection(self, filter_by_query, ignore_by_query, join_on_labels, left_collection_id, name, analysis_ids):
        left_collection_id = left_collection_id if left_collection_id is not None else self.loaded_collection_ids[0]

        label_df = self._label_df
        if ignore_by_query is not None:
            label_df = label_df.query(ignore_by_query)
        if filter_by_query is not None:
            label_df = label_df.query(filter_by_query)
        label_df = label_df.copy()
        numeric_df = self._numeric_df.loc[label_df.index].dropna(axis=1).copy()

        if len(label_df) == 0:
            return [dbc.Alert(f'No spectra meet the specified criteria ({filter_by_query}) & ({ignore_by_query}).',
                              dismissable=True,
                              color='warning')]
        collections = [
            get_collection(current_user, collection_id) for collection_id in self.loaded_collection_ids
        ]
        # merge collection attributes
        if len(self.loaded_collection_ids) > 1:
            print(label_df.columns)
            collection_lengths = [
                len(label_df[label_df.original_collection_id == collection_id])
                for collection_id in self.loaded_collection_ids
            ]
            collection_attrs = [collection.get_file_attributes() for collection in collections]
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

        if ignore_by_query is not None:
            attrs['ignore_by'] = ignore_by_query

        if join_on_labels is not None:
            right_collection_id = list(set(self.loaded_collection_ids) - {left_collection_id})[0]
            attrs.update({'left_collection_id': left_collection_id, 'right_collection_id': right_collection_id})

            left_label_df = collections[0].get_dataframe(include_only_labels=True)
            right_label_df = collections[1].get_dataframe(include_only_labels=True)
            left_numeric_df = collections[0].get_dataframe(include_labels=False, numeric_columns=True)
            right_numeric_df = collections[1].get_dataframe(include_labels=False, numeric_columns=True)

            if ignore_by_query is not None:
                left_label_df = left_label_df.query(ignore_by_query)
                right_label_df = right_label_df.query(ignore_by_query)
            if filter_by_query is not None:
                left_label_df = left_label_df.query(filter_by_query)
                right_label_df = right_label_df.query(filter_by_query)

            left_label_df = left_label_df.copy()
            right_label_df = right_label_df.copy()
            left_numeric_df = left_numeric_df.loc[left_label_df.index].copy()
            right_numeric_df = right_numeric_df.loc[right_label_df.index].copy()

            left_numeric_df = left_numeric_df[[c for c in left_numeric_df.columns if float(c) > 0]]
            right_numeric_df = right_numeric_df[[c for c in right_numeric_df.columns if float(c) > 0]]
            right_numeric_df.columns = [-float(c) for c in right_numeric_df.columns]
            left_numeric_df = pd.concat([left_numeric_df, left_label_df[join_on_labels]])
            right_numeric_df = pd.concat([right_numeric_df, right_label_df[join_on_labels]])

            left_numeric_df = left_numeric_df.groupby(join_on_labels).mean()
            right_numeric_df = right_numeric_df.groupby(join_on_labels).mean()

            numeric_df = left_numeric_df.join(right_numeric_df, how='inner')
            numeric_df.reset_index(inplace=True)
            numeric_df = numeric_df.drop(join_on_labels, axis=1)

            left_label_df = left_label_df.groupby(join_on_labels).mean()
            right_label_df = right_label_df.groupby(join_on_labels).mean()
            label_df = left_label_df.join(right_label_df, how='inner', lsuffix='_left', rsuffix='_right')
            label_df.reset_index(inplace=True)

        filename = os.path.join(self.root_dir, 'processed.h5')

        new_data = {
            'name': name,
            'description': self.proposed_name(filter_by_query, join_on_labels),
            'analysis_ids': analysis_ids,
            'group_can_read': all([collection.group_can_read for collection in collections]),
            'all_can_read': all([collection.all_can_read for collection in collections]),
            'group_can_write': all([collection.group_can_write for collection in collections]),
            'all_can_write': all([collection.all_can_write for collection in collections])
        }

        self.write_collection(numeric_df, label_df, attrs, filename)
        new_collection = upload_collection(current_user, filename, new_data)
        return [
            dbc.Alert(
                [
                    'Posted results as ',
                    html.A(f'Collection {new_collection.id}.',
                           href=url_for('collections.render_collection',
                                        collection_id=new_collection.id))
                ],
                dismissable=True, color='success')
        ]
