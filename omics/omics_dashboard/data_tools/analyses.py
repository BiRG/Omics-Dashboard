from data_tools.collections import get_collection
from data_tools.util import AuthException
from data_tools.users import is_read_permitted, is_write_permitted
from data_tools.database import db
import data_tools.file_tools.metadata_tools as mdt
from data_tools.util import DATADIR
from typing import List, Dict, Any


def get_analyses(user_id: int) -> List[Dict[str, Any]]:
    """
    Get all the analyses the user is allowed to view
    :param user_id:
    :return:
    """
    results = db.query_db('select * from Analyses;')
    return [result for result in results if is_read_permitted(user_id, result)]


def get_analysis(user_id: int, analysis_id: int) -> Dict[str, Any]:
    """
    Get analysis information
    :param user_id:
    :param analysis_id:
    :return:
    """
    result = db.query_db('select id, * from Analyses where rowid=?;', [str(analysis_id)], True)
    if is_read_permitted(user_id, result):
        return result
    raise AuthException(f'User {user_id} is not permitted to access analysis {analysis_id}')


def update_analysis(user_id: int, analysis_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the analysis with the data in new_data
    :param user_id:
    :param analysis_id:
    :param new_data:
    :return:
    """
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    valid_keys = ['name', 'description', 'owner', 'groupPermissions', 'allPermissions', 'userGroup']
    if is_write_permitted(user_id, analysis):
        params = [str(value) for key, value in new_data.items() if key in valid_keys]
        if len(params) > 0:
            query = 'update Analyses set ' \
                    + ','.join([f' {key} = ?' for key in new_data.keys() if key in valid_keys]) \
                    + ' where id=?;'
            params.append(str(analysis_id))
            db.query_db(query, params)
        return get_analysis(user_id, analysis_id)
    raise AuthException(f'User {user_id} is not permitted to modify analysis {analysis_id}')


def create_analysis(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new analysis with the metdata in data
    :param user_id:
    :param data:
    :return:
    """
    db.query_db('insert into Analyses '
                '(name, description, createdBy, owner, groupPermissions, allPermissions, userGroup) '
                'values (?, ?, ?, ?, ?, ?, ?);',
                [str(data['name']), str(data['description']), str(user_id), str(user_id), str(data['groupPermissions']),
                 str(data['allPermissions']), str(data['userGroup'])],
                True)
    return db.query_db('select id, * from Analyses where id=last_insert_rowid()', (), True)


def delete_analysis(user_id: int, analysis_id: int) -> Dict[str, str]:
    """
    Remove the record associated with this analysis from the database
    :param user_id:
    :param analysis_id:
    :return:
    """
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    if analysis is None:
        return {'message': f'Analysis {analysis_id} does not exist'}
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from Analyses where id=?;', [str(analysis_id)])
        return {'message': f'analysis {analysis_id} deleted'}
    raise AuthException(f'User {user_id} is not permitted to modify analysis {analysis_id}')


def attach_collection(user_id: int, analysis_id: int, collection_id: int) -> Dict[str, Any]:
    """
    Add a collection to the list of collections belonging to an analysis
    :param user_id:
    :param analysis_id:
    :param collection_id:
    :return:
    """
    # check read permissions on analysis and collection
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    collection = mdt.get_collection_metadata(f'{DATADIR}/collections/{collection_id}.h5')
    if is_write_permitted(user_id, collection) and is_write_permitted(user_id, analysis):
        db.query_db('insert into CollectionMemberships (collectionId, analysisId) values (?,?);',
                    [str(collection_id), str(analysis_id)])
        # see if attached
        return {'message': f'collection {collection_id} attached to analysis {analysis_id}'}
    raise AuthException(f'User {user_id} is not permitted to attach collection {collection_id} '
                        f'to analysis {analysis_id}')


def detach_collection(user_id: int, analysis_id: int, collection_id: int) -> None:
    """
    Remove a collection from the list of collections belonging to an analysis
    :param user_id:
    :param analysis_id:
    :param collection_id:
    :return:
    """
    analysis = db.query_db('select * from Analyses where id=?;', [str(analysis_id)], True)
    if is_write_permitted(user_id, analysis):
        db.query_db('delete from CollectionMemberships where collectionId=? and analysisId=?;',
                    [str(collection_id), str(analysis_id)])
    raise AuthException(f'User {user_id} is not permitted to modify analysis {analysis_id}')


def get_attached_collections(user_id: int, analysis_id: int) -> List[Dict[str, Any]]:
    """
    Get all collections which belong to an analysis
    :param user_id:
    :param analysis_id:
    :return:
    """
    analysis = get_analysis(user_id, analysis_id)
    attachment_data = db.query_db('select * from CollectionMemberships where analysisId=?;', [str(analysis_id)])
    print(attachment_data)
    if is_read_permitted(user_id, analysis):
        collections = [
            mdt.get_collection_info(f'{DATADIR}/collections/{attachment["collectionId"]}.h5')
            for attachment in attachment_data
        ]
        print([collection for collection in collections if is_read_permitted(user_id, collection)])
        return [collection for collection in collections if is_read_permitted(user_id, collection)]
    raise AuthException(f'User {user_id} is not permitted to access analysis {analysis_id}')


def get_attached_analyses(user_id: int, collection_id: int) -> List[Dict[str, Any]]:
    """
    Get all analysis that a collection belongs to
    :param user_id:
    :param collection_id:
    :return:
    """
    collection = get_collection(user_id, collection_id)
    attachment_data = db.query_db('select * from CollectionMemberships where collectionId=?;', [str(collection_id)])
    if is_read_permitted(user_id, collection):
        analyses = []
        for attachment in attachment_data:
            analysis = db.query_db('select * from Analyses where id=?', [str(attachment['analysisId'])])
            if is_read_permitted(user_id, analysis):
                analyses.append(analysis)
        return analyses
    raise AuthException(f'User {user_id} not permitted to access collection {collection_id}')
