"""SQLAlchamy queries for the STAC view."""
from .models import Job
from .models import CatalogEntry
from .models import Attribute
from .models import APIKey
from .models import GlobalVariable


def find_catalog_by_id(catalog, asset_id):
    return CatalogEntry.query.filter(
        CatalogEntry.catalog == catalog,
        CatalogEntry.asset_id == asset_id).one_or_none()

