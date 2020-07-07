"""Queries for SQLAlchamy STAC view."""
from .models import APIKey
from .models import Attribute
from .models import CatalogEntry
from sqlalchemy import and_

def find_catalog_by_id(catalog, asset_id):
    """Find the single catalong entry matching catalog:asset_id.

    Args:
        catalog (str): catalog id
        asset_id (str): asset id in that catalog.

    Returns:
        CatalogEntry that matches the catalog:asset_id pair or None.

    """
    return CatalogEntry.query.filter(
        CatalogEntry.catalog == catalog,
        CatalogEntry.asset_id == asset_id).one_or_none()


def get_allowed_permissions_map(api_key):
    """Get allowed permissions for the given api key.

    Args:
        api_key (str): arbitrary api key string

    Returns:
        dictionary with 'READ' and 'WRITE' keys mapping to a set of catalog
        names and/or '*' to indicate full permissions allowed or None if
        the api key is not found.

    """
    result = APIKey.query.filter(
        APIKey.api_key == api_key).one_or_none()

    if result is None:
        return None

    allowed_permissions = {}
    for permission_type in ['READ', 'WRITE']:
        allowed_permissions[permission_type] = set([
            permission.split(':')[1]
            for permission in result.permissions.split(' ')
            if permission.startswith(f'{permission_type}:')])

    return allowed_permissions


def get_assets(
        bounding_box_list, datetime_str, catalog_set, asset_id, description):
    """Get a list of assets that match the search terms.

    Args:
        bounding_box_list (list): bounding box coordinates in order of
            [xmin, ymin, xmax, ymax]. If not None, any assets that intersect
            this box are returned.
        datetime_str (str):  "exact time" | "low_time/high_time" |
            "../high time" | "low time/..". If not None, any assets are bounded
            against this time or time range.
        catalog_set (set): Only assets in these catalogs are returned.
        asset_id (str): If not None, search for partial or exact match to this
            asset id.
        description (str): If not None, search for this partial or exact match
            to this description.


    Returns:
        List of CatalogEntry for those entries that match the search
        parameters.

    """
    query_parameter_list = []
    if bounding_box_list is not None:
        s_xmin, s_ymin, s_xmax, s_ymax = bounding_box_list
        query_parameter_list.extend(
            s_xmin <= CatalogEntry.bb_xmax,
            s_xmax >= CatalogEntry.bb_xmin,
            s_ymin <= CatalogEntry.bb_ymax,
            s_ymax >= CatalogEntry.bb_ymin)

    if datetime_str is not None:
        if '/' in datetime_str:
            min_time, max_time = datetime_str.split('/')
            if min_time != '..':
                query_parameter_list.append(
                    CatalogEntry.utc_datetime >= min_time)
            if max_time != '..':
                query_parameter_list.append(
                    CatalogEntry.utc_datetime <= max_time)
        else:
            query_parameter_list.append(
                CatalogEntry.utc_datetime == datetime_str)

    query_parameter_list.append(CatalogEntry.catalog.in_(*catalog_set))

    if asset_id is not None:
        query_parameter_list.append(CatalogEntry.asset_id.ilike(
            f'%{asset_id}%'))

    if description is not None:
        query_parameter_list.append(CatalogEntry.description.ilike(
            f'%{description}%'))

    return CatalogEntry.query.filter(and_(*query_parameter_list)).all()


def get_asset_attributes(catalog, asset_id):
    """Get additional asset attributes associated with catalog:asset_id.

    Args:
        catalog (str): the catalog to search in
        asset_id (str): the asset id to search for.

    Returns:
        dict of key/value pairs attributes associated with this catalog:asset.

    """
    return {
        attribute.key: attribute.value
        for attribute in Attribute.query(and_(
            Attribute.asset_id == asset_id,
            Attribute.catalog == catalog)).all()}
