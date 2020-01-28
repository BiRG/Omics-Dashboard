from data_tools.wrappers.users import is_write_permitted
from data_tools.db_models import User, Collection
from data_tools.file_tools.collection_tools import get_dataset
from data_tools.template_models.page import PageData


class LabelColumnTableData(PageData):
    def __init__(self, current_user: User, collection: Collection):
        super(LabelColumnTableData, self).__init__(current_user, is_write_permitted(current_user, collection))
        file_info = collection.get_file_info()
        label_datasets = [dataset for dataset in file_info['datasets']
                          if dataset['rows'] == file_info['max_row_count'] and dataset['cols'] == 1]
        self.headings = [dataset['path'] for dataset in label_datasets]
        self.columns = {path: get_dataset(collection.filename, path, True) for path in self.headings}
        self.row_count = file_info['max_row_count']
