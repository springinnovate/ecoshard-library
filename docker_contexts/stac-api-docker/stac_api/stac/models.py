# Models for STAC view.
from ..db import db


class Job(db.Model):
    """Stores info about a non-trivial running job invoked from the API."""
    __tablename__ = 'job_table'

    job_id = db.Column(db.String, primary_key=True)
    uri = db.Column(db.String, nullable=False)
    job_status = db.Column(db.String, nullable=False)
    active = db.Column(db.Integer, nullable=False)
    last_accessed_utc = db.Column(db.String, nullable=False, index=True)

    def __repr__(self):
        """Job status."""
        return (
            f"<Job ID: {self.job_id}, uri: {self.uri}, "
            f"job status: {self.job_status}, active: {self.active}, "
            f"last_accessed: {self.last_accessed_utc}")


class CatalogEntry(db.Model):
    """STAC Raster Catalog Entry."""
    __tablename__ = 'catalog_table'

    asset_id = db.Column(db.String, primary_key=True)
    catalog = db.Column(db.String, primary_key=True)
    bb_xmin = db.Column(db.Float, nullable=False, index=True)
    bb_xmax = db.Column(db.Float, nullable=False, index=True)
    bb_ymin = db.Column(db.Float, nullable=False, index=True)
    bb_ymax = db.Column(db.Float, nullable=False, index=True)
    utc_datetime = db.Column(db.String, nullable=False, index=True)
    expiration_utc_datetime = db.Column(db.String, nullable=False)
    mediatype = db.Column(db.String, nullable=False, index=True)
    description = db.Column(db.String, nullable=False)
    uri = db.Column(db.String, nullable=False)
    local_path = db.Column(db.String, nullable=False)
    raster_min = db.Column(db.Float, nullable=False)
    raster_max = db.Column(db.Float, nullable=False)
    raster_mean = db.Column(db.Float, nullable=False)
    raster_stdev = db.Column(db.Float, nullable=False)
    default_style = db.Column(db.String, nullable=False)

    def __repr__(self):
        """Can be uniqely identified by 'catalog: asset'."""
        return f'Catalog: {self.catalog}, Asset: {self.asset_id}'


class Attribute(db.Model):
    """Additional custom attributes associated with catalog:asset."""
    __tablename__ = 'attribute_table'

    asset_id = db.Column(db.String, primary_key=True)
    catalog = db.Column(db.String, primary_key=True)
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String)

    def __repr__(self):
        """Display unique ID and key value pair."""
        return (
            f'Catalog: {self.catalog}, Asset: {self.asset_id} '
            f'-- {self.key}:{self.value}')


class APIKey(db.Model):
    """API key with permissions associated with STAC operations."""
    __tablename__ = 'api_keys'

    api_key = db.Column(db.String, primary_key=True)
    # permissions is string of READ:catalog WRITE:catalog CREATE
    # where READ/WRITE:catalog allow access to read and write the
    # catalog and CREATE allows creation of a new catalog.
    permissions = db.Column(db.String)

    def __repr__(self):
        """Display the key and permissions."""
        return f'{self.api_key}: {self.permissions}'


class GlobalVariable(db.Model):
    """Used to maintain state in the STAC app."""
    __tablename__ = 'global_variables'

    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.LargeBinary)

    def __repr__(self):
        return f'{self.key}: {self.value}'
