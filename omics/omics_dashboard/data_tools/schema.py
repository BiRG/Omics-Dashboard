from data_tools.database.db import query_db

required_attrs = {'name', 'description', 'createdBy', 'owner', 'groupPermissions', 'allPermissions', 'userGroup'}
permissions = {'readonly', 'full', ''}


def user_exists(user_id):
    return query_db('select * from Users where id=?;', [str(user_id)]) is not None


def verify_collection_attributes():

    return True


def verify_collection_datasets():
    return True


def verify_database():
    return True