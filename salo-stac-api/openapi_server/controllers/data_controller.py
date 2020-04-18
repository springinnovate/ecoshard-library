import connexion
import six

from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.feature_collection_geo_json import FeatureCollectionGeoJSON  # noqa: E501
from openapi_server.models.item import Item  # noqa: E501
from openapi_server import util


def get_feature(collection_id, feature_id):  # noqa: E501
    """fetch a single feature

    Fetch the feature with id &#x60;featureId&#x60; in the feature collection with id &#x60;collectionId&#x60;.  Use content negotiation to request HTML or GeoJSON. # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param feature_id: local identifier of a feature
    :type feature_id: str

    :rtype: Item
    """
    return 'do some magic!'


def get_features(collection_id, limit=None, bbox=None, datetime=None):  # noqa: E501
    """fetch features

    Fetch features of the feature collection with id &#x60;collectionId&#x60;.  Every feature in a dataset belongs to a collection. A dataset may consist of multiple feature collections. A feature collection is often a collection of features of a similar type, based on a common schema.  Use content negotiation to request HTML or GeoJSON. # noqa: E501

    :param collection_id: local identifier of a collection
    :type collection_id: str
    :param limit: The optional limit parameter limits the number of items that are presented in the response document.  Only items are counted that are on the first level of the collection in the response document. Nested objects contained within the explicitly requested items shall not be counted.  Minimum &#x3D; 1. Maximum &#x3D; 10000. Default &#x3D; 10.
    :type limit: int
    :param bbox: Only features that have a geometry that intersects the bounding box are selected. The bounding box is provided as four or six numbers, depending on whether the coordinate reference system includes a vertical axis (height or depth):  * Lower left corner, coordinate axis 1 * Lower left corner, coordinate axis 2 * Minimum value, coordinate axis 3 (optional) * Upper right corner, coordinate axis 1 * Upper right corner, coordinate axis 2 * Maximum value, coordinate axis 3 (optional)  The coordinate reference system of the values is WGS 84 longitude/latitude (http://www.opengis.net/def/crs/OGC/1.3/CRS84) unless a different coordinate reference system is specified in the parameter &#x60;bbox-crs&#x60;.  For WGS 84 longitude/latitude the values are in most cases the sequence of minimum longitude, minimum latitude, maximum longitude and maximum latitude. However, in cases where the box spans the antimeridian the first value (west-most box edge) is larger than the third value (east-most box edge).  If the vertical axis is included, the third and the sixth number are the bottom and the top of the 3-dimensional bounding box.  If a feature has multiple spatial geometry properties, it is the decision of the server whether only a single spatial geometry property is used to determine the extent or all relevant geometries.  Example: The bounding box of the New Zealand Exclusive Economic Zone in WGS 84 (from 160.6°E to 170°W and from 55.95°S to 25.89°S) would be represented in JSON as &#x60;[160.6, -55.95, -170, -25.89]&#x60; and in a query as &#x60;bbox&#x3D;160.6,-55.95,-170,-25.89&#x60;.
    :type bbox: List[]
    :param datetime: Either a date-time or an interval, open or closed. Date and time expressions adhere to RFC 3339. Open intervals are expressed using double-dots.  Examples:  * A date-time: \&quot;2018-02-12T23:20:50Z\&quot; * A closed interval: \&quot;2018-02-12T00:00:00Z/2018-03-18T12:31:12Z\&quot; * Open intervals: \&quot;2018-02-12T00:00:00Z/..\&quot; or \&quot;../2018-03-18T12:31:12Z\&quot;  Only features that have a temporal property that intersects the value of &#x60;datetime&#x60; are selected.  If a feature has multiple temporal properties, it is the decision of the server whether only a single temporal property is used to determine the extent or all relevant temporal properties.
    :type datetime: str

    :rtype: FeatureCollectionGeoJSON
    """
    return 'do some magic!'
