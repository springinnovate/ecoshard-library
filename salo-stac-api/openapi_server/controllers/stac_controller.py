import connexion
import six

from openapi_server.models.exception import Exception  # noqa: E501
from openapi_server.models.item_collection import ItemCollection  # noqa: E501
from openapi_server.models.search_body import SearchBody  # noqa: E501
from openapi_server import util


def get_search_stac(bbox=None, datetime=None, limit=None, ids=None, collections=None, query=None, sortby=None, fields=None):  # noqa: E501
    """Search STAC items with simple filtering.

    Retrieve Items matching filters. Intended as a shorthand API for simple queries.  This method is optional, but you MUST implement &#x60;POST /search&#x60; if you want to implement this method.  If this endpoint is implemented on a server, it is required to add a link referring to this endpoint with &#x60;rel&#x60; set to &#x60;search&#x60; to the &#x60;links&#x60; array in &#x60;GET /&#x60;. As &#x60;GET&#x60; is the default method, the &#x60;method&#x60; may not be set explicitly in the link. # noqa: E501

    :param bbox: Only features that have a geometry that intersects the bounding box are selected. The bounding box is provided as four or six numbers, depending on whether the coordinate reference system includes a vertical axis (height or depth):  * Lower left corner, coordinate axis 1 * Lower left corner, coordinate axis 2 * Minimum value, coordinate axis 3 (optional) * Upper right corner, coordinate axis 1 * Upper right corner, coordinate axis 2 * Maximum value, coordinate axis 3 (optional)  The coordinate reference system of the values is WGS 84 longitude/latitude (http://www.opengis.net/def/crs/OGC/1.3/CRS84) unless a different coordinate reference system is specified in the parameter &#x60;bbox-crs&#x60;.  For WGS 84 longitude/latitude the values are in most cases the sequence of minimum longitude, minimum latitude, maximum longitude and maximum latitude. However, in cases where the box spans the antimeridian the first value (west-most box edge) is larger than the third value (east-most box edge).  If the vertical axis is included, the third and the sixth number are the bottom and the top of the 3-dimensional bounding box.  If a feature has multiple spatial geometry properties, it is the decision of the server whether only a single spatial geometry property is used to determine the extent or all relevant geometries.  Example: The bounding box of the New Zealand Exclusive Economic Zone in WGS 84 (from 160.6°E to 170°W and from 55.95°S to 25.89°S) would be represented in JSON as &#x60;[160.6, -55.95, -170, -25.89]&#x60; and in a query as &#x60;bbox&#x3D;160.6,-55.95,-170,-25.89&#x60;.
    :type bbox: List[]
    :param datetime: Either a date-time or an interval, open or closed. Date and time expressions adhere to RFC 3339. Open intervals are expressed using double-dots.  Examples:  * A date-time: \&quot;2018-02-12T23:20:50Z\&quot; * A closed interval: \&quot;2018-02-12T00:00:00Z/2018-03-18T12:31:12Z\&quot; * Open intervals: \&quot;2018-02-12T00:00:00Z/..\&quot; or \&quot;../2018-03-18T12:31:12Z\&quot;  Only features that have a temporal property that intersects the value of &#x60;datetime&#x60; are selected.  If a feature has multiple temporal properties, it is the decision of the server whether only a single temporal property is used to determine the extent or all relevant temporal properties.
    :type datetime: str
    :param limit: The optional limit parameter limits the number of items that are presented in the response document.  Only items are counted that are on the first level of the collection in the response document. Nested objects contained within the explicitly requested items shall not be counted.  Minimum &#x3D; 1. Maximum &#x3D; 10000. Default &#x3D; 10.
    :type limit: int
    :param ids: Array of Item ids to return. All other filter parameters that further restrict the number of search results are ignored
    :type ids: List[str]
    :param collections: Array of Collection IDs to include in the search for items. Only Items in one of the provided Collections will be searched 
    :type collections: List[str]
    :param query: query for properties in items. Use the JSON form of the queryFilter used in POST.
    :type query: str
    :param sortby: An array of property names, prefixed by either \&quot;+\&quot; for ascending or \&quot;-\&quot; for descending. If no prefix is provided, \&quot;+\&quot; is assumed.
    :type sortby: str
    :param fields: Determines the shape of the features in the response
    :type fields: str

    :rtype: ItemCollection
    """
    return 'do some magic!'


def post_search_stac(search_body=None):  # noqa: E501
    """Search STAC items with full-featured filtering.

    retrieve items matching filters. Intended as the standard, full-featured query API.  This method is mandatory to implement if &#x60;GET /search&#x60; is implemented. If this endpoint is implemented on a server, it is required to add a link referring to this endpoint with &#x60;rel&#x60; set to &#x60;search&#x60; and &#x60;method&#x60; set to &#x60;POST&#x60; to the &#x60;links&#x60; array in &#x60;GET /&#x60;. # noqa: E501

    :param search_body: 
    :type search_body: dict | bytes

    :rtype: ItemCollection
    """
    if connexion.request.is_json:
        search_body = SearchBody.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
