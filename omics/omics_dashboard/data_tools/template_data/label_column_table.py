from data_tools.db import User, Collection
from data_tools.file_tools.collection_tools import get_dataset
from data_tools.template_data.page import PageData
from data_tools.users import is_write_permitted


class LabelColumnTableData(PageData):
    def __init__(self, current_user: User, collection: Collection):
        super(LabelColumnTableData, self).__init__(current_user, is_write_permitted(current_user, collection))
        file_info = collection.get_file_info()
        label_datasets = [dataset for dataset in file_info['datasets']
                          if dataset['rows'] == file_info['max_row_count'] and dataset['cols'] == 1]
        self.headings = [dataset['path'] for dataset in label_datasets]
        self.columns = {path: get_dataset(collection.filename, path, True) for path in self.headings}
        self.row_count = file_info['max_row_count']
