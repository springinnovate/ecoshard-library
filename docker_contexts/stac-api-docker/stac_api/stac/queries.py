"""Queries for SQLAlchamy STAC view."""
from .models import APIKey
from .models import CatalogEntry


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


def get_allowed_permissions(api_key):
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
