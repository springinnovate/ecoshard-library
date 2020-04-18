import connexion
import six

from openapi_server.models.catalog_definition import CatalogDefinition  # noqa: E501
from openapi_server.models.collections import Collections  # noqa: E501
from openapi_server import util


def collections_collection_id_items_feature_id_versions_get(collection_id, feature_id):  # noqa: E501
    """returns a list of links for a versioned item

    returns a list of links for a versioned item # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param feature_id: local identifier of a feature
    :type feature_id: str

    :rtype: CatalogDefinition
    """
    return 'do some magic!'


def collections_collection_id_items_feature_id_versions_version_id_get(collection_id, feature_id, version_id):  # noqa: E501
    """returns the requested version of an item

    returns the requested version of an item # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param feature_id: local identifier of a feature
    :type feature_id: str
    :param version_id: local identifier of a version
    :type version_id: str

    :rtype: Collections
    """
    return 'do some magic!'


def collections_collection_id_versions_get(collection_id):  # noqa: E501
    """returns a list of links for a versioned collection

    returns a list of links for a versioned collection # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str

    :rtype: CatalogDefinition
    """
    return 'do some magic!'


def collections_collection_id_versions_version_id_get(collection_id, version_id):  # noqa: E501
    """returns the requested version of a collection

    returns the requested version of a collection # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param version_id: local identifier of a version
    :type version_id: str

    :rtype: Collections
    """
    return 'do some magic!'
