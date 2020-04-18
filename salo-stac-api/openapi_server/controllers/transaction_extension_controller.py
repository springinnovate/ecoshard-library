import connexion
import six

from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.item import Item  # noqa: E501
from openapi_server.models.one_ofitemitem_collection import OneOfitemitemCollection  # noqa: E501
from openapi_server.models.partial_item import PartialItem  # noqa: E501
from openapi_server.models.unknownbasetype import UNKNOWN_BASE_TYPE  # noqa: E501
from openapi_server import util


def delete_feature(collection_id, feature_id, if_match):  # noqa: E501
    """delete an existing feature by Id

    Use this method to delete an existing feature. # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param feature_id: local identifier of a feature
    :type feature_id: str
    :param if_match: Only take the action if the ETag of the item still matches
    :type if_match: str

    :rtype: None
    """
    return 'do some magic!'


def patch_feature(collection_id, feature_id, if_match=None, partial_item=None):  # noqa: E501
    """update an existing feature by Id with a partial item definition

    Use this method to update an existing feature. Requires a GeoJSON fragement (containing the fields to be updated) be submitted. # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param feature_id: local identifier of a feature
    :type feature_id: str
    :param if_match: Only take the action if the ETag of the item still matches
    :type if_match: str
    :param partial_item: 
    :type partial_item: dict | bytes

    :rtype: str
    """
    if connexion.request.is_json:
        partial_item = PartialItem.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def post_feature(collection_id, unknown_base_type=None):  # noqa: E501
    """add a new feature to a collection

    create a new feature in a specific collection # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param unknown_base_type: 
    :type unknown_base_type: dict | bytes

    :rtype: str
    """
    if connexion.request.is_json:
        unknown_base_type = UNKNOWN_BASE_TYPE.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def put_feature(collection_id, feature_id, if_match, item=None):  # noqa: E501
    """update an existing feature by Id with a complete item definition

    Use this method to update an existing feature. Requires the entire GeoJSON  description be submitted. # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param feature_id: local identifier of a feature
    :type feature_id: str
    :param if_match: Only take the action if the ETag of the item still matches
    :type if_match: str
    :param item: 
    :type item: dict | bytes

    :rtype: str
    """
    if connexion.request.is_json:
        item = Item.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
