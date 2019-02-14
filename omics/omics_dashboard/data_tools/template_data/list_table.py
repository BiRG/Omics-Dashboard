from typing import Any, Union, List

from data_tools.db import Base, OmicsRecordMixin, User, NumericFileRecordMixin, Collection, Sample
from data_tools.template_data.page import PageData
from data_tools.users import is_write_permitted
from data_tools.workflows import WorkflowModule
from helpers import get_item_link


class ListTableCell:
    def __init__(self, value, href: str = None, editable: bool = False, order_value: Any=None):
        self.value = value
        self.href = href
        self.editable = editable
        self.order_value = order_value
        if isinstance(value, bool):
            self.order_value = int(value)


class ListTableRow:
    """
    Stores a record for storing in the generic list tables
    A list of these is passed to the list template as 'rows'
    """
    def __init__(self, record, special_val: bool = None, special_val_heading: str = None):
        self.values = {
            'ID': ListTableCell(record.id),
            'Name': ListTableCell(record.name, get_item_link(record))
        }
        if hasattr(record, 'description'):
            self.values['Description'] = ListTableCell(record.description)
        if isinstance(record, Base):
            self.values['Date Created'] = ListTableCell(record.created_on.strftime('%-d %b %Y %H:%M'),
                                                        order_value=record.created_on.timestamp())
            self.values['Date Modified'] = ListTableCell(record.updated_on.strftime('%-d %b %Y %H:%M'),
                                                         order_value=record.updated_on.timestamp())
        if isinstance(record, OmicsRecordMixin):
            self.values['Last Modified By'] = ListTableCell(record.last_editor.name, get_item_link(record.last_editor)) if record.last_editor is not None else ListTableCell('None')
        if isinstance(record, NumericFileRecordMixin):
            row_count, column_count = record.get_dimensions()
            print(f'row_count: {row_count}, column_count: {column_count}')
            if row_count is not None or column_count is not None:
                self.values['Rows'] = ListTableCell(row_count)
                self.values['Columns'] = ListTableCell(column_count)
        if special_val_heading is not None and special_val is not None:
            self.values[special_val_heading] = ListTableCell(special_val)
        if isinstance(record, WorkflowModule):
            if 'ID' in self.values: self.values.pop('ID')
            self.values['Package'] = ListTableCell(record.package_name)
            self.values['Subpackage'] = ListTableCell(record.subpackage_name)


class FileListTableRow:
    """
    Stores a record for storing in a list of file attributes
    """
    def __init__(self, record: Union[Sample, Collection], editable: bool = False, special_val: bool = None, special_val_heading: str = None):
        self.values = {'ID': ListTableCell(record.id), 'Name': ListTableCell(record.name, get_item_link(record))}
        if record.file_exists():
            for key, value in record.get_file_attributes().items():
                value_editable = editable if key not in {'max_row_count', 'max_col_count', 'date_modified'} else False
                self.values[key] = ListTableCell(value, None, value_editable)
            row_count, column_count = record.get_dimensions()
            print(f'row_count: {row_count}, column_count: {column_count}')
            self.values['Rows'] = ListTableCell(row_count)
            self.values['Columns'] = ListTableCell(column_count)
        if special_val_heading is not None and special_val is not None:
            self.values[special_val_heading] = ListTableCell(special_val)


class ListTableData(PageData):
    """
    Stores data passed to the generic list table
    """
    def __init__(self, current_user: User, records: List[Any], title: str, special_vals: List[bool] = None,
                 special_val_heading=None):
        super(ListTableData, self).__init__(current_user)
        self.title = title
        self.special_val_heading = special_val_heading if special_val_heading is not None else ''
        if special_vals is None:
            special_vals = [None for _ in records]
        self.rows = [ListTableRow(record, special_val, special_val_heading) for record, special_val in zip(records, special_vals)]
        self.headings = []
        if len(self.rows):
            self.headings = ['ID'] + [key for key in self.rows[0].values.keys() if key not in {'ID', special_val_heading}]
            if 'ID' not in self.rows[0].values.keys():
                self.headings.remove('ID')
        if len(special_vals) and special_vals[0] is not None:
            self.headings.remove('ID')
            self.headings = [special_val_heading] + self.headings
            if 'ID' in self.rows[0].values.keys():
                self.headings = ['ID'] + self.headings


class FileListTableData(PageData):
    """
    Store only file metadata, id and name. Editable file metadata is
    """
    def __init__(self, current_user: User, records: List[Union[Sample, Collection]], title: str, special_vals: List[bool] = None, special_val_heading=None):
        super(FileListTableData, self).__init__(current_user)
        self.title = title
        self.special_val_heading = special_val_heading if special_val_heading is not None else ''
        if special_vals is None:
            special_vals = [None for _ in records]
        self.rows = [FileListTableRow(record, is_write_permitted(current_user, record), special_val, special_val_heading) for record, special_val in zip(records, special_vals)]
        if len(self.rows):
            self.headings = ['ID'] + [key for key in self.rows[0].values.keys() if key not in {'ID', special_val_heading} and all([key in row.values for row in self.rows])]
            if 'ID' not in self.rows[0].values.keys():
                self.headings.remove('ID')
        if len(special_vals) and special_vals[0] is not None:
            self.headings.remove('ID')
            self.headings = [special_val_heading] + self.headings
            if 'ID' in self.rows[0].values.keys():
                self.headings = ['ID'] + self.headings
