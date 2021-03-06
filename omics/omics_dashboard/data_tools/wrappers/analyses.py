from typing import List, Dict, Any

from data_tools.wrappers.users import is_read_permitted, is_write_permitted, get_all_read_permitted_records
from data_tools.db_models import Analysis, Collection, User, db
from data_tools.util import AuthException


def get_analyses(user: User, filter_by: Dict[str, Any] = None) -> List[Analysis]:
    """
    Get all the analyses the user is allowed to view
    :param user:
    :param filter_by:
    :return:
    """
    return get_all_read_permitted_records(user, Analysis, filter_by)


def get_analysis(user: User, analysis_id: int) -> Analysis:
    """
    Get analysis information
    :param user:
    :param analysis_id:
    :return:
    """
    analysis = Analysis.query.filter_by(id=analysis_id).first()
    if is_read_permitted(user, analysis):
        return analysis
    raise AuthException(f'User {user.email} is not permitted to access analysis {analysis_id}')


def update_analysis(user: User, analysis: Analysis, new_data: Dict[str, Any]) -> Analysis:
    """
    Update the analysis with the data in new_data
    :param user:
    :param analysis:
    :param new_data:
    :return:
    """
    if is_write_permitted(user, analysis):
        if 'id' in new_data:
            if analysis.id != int(new_data['id']) and Analysis.query.filter_by(id=new_data['id']) is not None:
                raise ValueError(f'Analysis with id {new_data["id"]} already exists!')
        analysis.update(new_data)
        analysis.last_editor = user
        db.session.commit()
        return analysis
    raise AuthException(f'User {user.email} is not permitted to modify analysis {analysis.id}')


def create_analysis(user: User, data: Dict[str, Any], collections: List[Collection] = None) -> Analysis:
    """
    Create a new analysis with the metdata in data
    :param user:
    :param data:
    :param collections:
    :return:
    """
    if 'id' in data:  # cannot create with designated id
        del data['id']
    analysis = Analysis(creator=user,
                        owner=user,
                        last_editor=user,
                        name=data['name'])
    if collections is not None:
        analysis.collections = collections
    db.session.add(analysis)
    db.session.commit()
    update_analysis(user, analysis, data)
    return analysis


def delete_analysis(user: User, analysis: Analysis) -> Dict[str, str]:
    """
    Remove the record associated with this analysis from the database
    :param user:
    :param analysis:
    :return:
    """
    if is_write_permitted(user, analysis):
        db.session.delete(analysis)
        db.session.commit()
        return {'message': f'Analysis {analysis.id} deleted'}
    raise AuthException(f'User {user.email} is not permitted to modify analysis {analysis.id}')


def attach_collection(user: User, analysis: Analysis, collection: Collection) -> Dict[str, Any]:
    """
    Add a collection to the list of collections belonging to an analysis
    :param user:
    :param analysis:
    :param collection:
    :return:
    """
    # check read permissions on analysis and collection
    if is_read_permitted(user, collection) and is_write_permitted(user, analysis):
        if collection not in analysis.collections:
            analysis.collections.append(collection)
            db.session.commit()
            return {'message': f'collection {collection.id} attached to analysis {analysis.id}'}
        return {'message': f'Collection {collection.id} already attached to analysis {analysis.id}'}
    raise AuthException(f'User {user.email} is not permitted to attach collection {collection.id} '
                        f'to analysis {analysis.id}')


def detach_collection(user: User, analysis: Analysis, collection: Collection) -> Dict[str, Any]:
    """
    Remove a collection from the list of collections belonging to an analysis
    :param user:
    :param analysis:
    :param collection:
    :return:
    """
    if is_write_permitted(user, analysis):
        analysis.collections.remove(collection)
        db.session.commit()
        return {'message': f'collection {collection.id} detached from analysis {analysis.id}'}
    raise AuthException(f'User {user.email} is not permitted to modify analysis {analysis.id}')


def get_attached_collections(user: User, analysis: Analysis) -> List[Collection]:
    """
    Get all collections which belong to an analysis
    :param user:
    :param analysis:
    :return:
    """
    if is_read_permitted(user, analysis):
        return analysis.collections
    raise AuthException(f'User {user.email} is not permitted to access analysis {analysis.id}')


def get_attached_analyses(user: User, collection: Collection) -> List[Analysis]:
    """
    Get all analysis that a collection belongs to
    :param user:
    :param collection:
    :return:
    """
    if is_read_permitted(user, collection):
        return get_all_read_permitted_records(user, collection.analyses)
    raise AuthException(f'User {user.email} not permitted to access collection {collection.id}')
