"""Queries for SQLAlchamy STAC view."""
from .models import CatalogEntry


def find_catalog_by_id(catalog, asset_id):
    return CatalogEntry.query.filter(
        CatalogEntry.catalog == catalog,
        CatalogEntry.asset_id == asset_id).one_or_none()
