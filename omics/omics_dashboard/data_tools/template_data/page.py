from data_tools.db import User


class PageData:
    def __init__(self, current_user: User, editable: bool = False):
        self.current_user = current_user
        self.editable = editable


