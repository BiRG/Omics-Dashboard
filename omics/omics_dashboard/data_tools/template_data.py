from typing import Any, List, Type


class FormData:
    """
    Stores data used for one line of a creation form.
    """
    def __init__(self, label: str, value: Any, tag: str, custom_template: str = None):
        self.label = label
        self.value = value
        self.tag = tag
        self.custom_template = custom_template


class AttributeTableRow:
    """
    Stores an attribute that can possibly be edited.
    A list of these is passed to the attribute editor as 'attributes'
    """
    def __init__(self, label: str, value: Any, editable: bool, custom_template: str = None):
        self.label = label
        self.value = value
        self.editable = editable
        self.custom_template = custom_template


