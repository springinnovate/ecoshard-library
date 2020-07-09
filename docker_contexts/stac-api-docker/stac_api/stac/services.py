"""Services for STAC API SQLAlchemy."""
from .models import db
from .models import Attribute
from .models import CatalogEntry
from .models import Job


def create_job(job_id, data_uri, job_status):
    """Create a job record to monitor job progress.

    Args:
        job_id (str): unique string to index the job
        data_uri (str): URI to data that are being processed
        job_status (str): string of job status to report when queried

    Returns:
        new Job object (not committed)

    """
    job = Job(
        job_id=job_id,
        job_status=job_status,
        )
    db.session.add(job)
    return job


def update_job_status(job_id, new_job_status):
    """Update Job object matching `job_id` with the new job status.

    Args:
        job_id (str): unique job ID string.
        new_job_status (str): job status string to replace current with.

    Returns:
        updated Job object (not committed)

    """
    job = Job.query.filter(Job.job_id == job_id).one()
    job.job_id = job_id
    return job


def create_or_update_catalog_entry(
        asset_id, catalog, xmin, ymin, xmax, ymax,
        utc_datetime, mediatype, description, uri, local_path,
        raster_min, raster_max, raster_mean, raster_stdev,
        default_style, expiration_utc_datetime):
    """Create a new CatalogEntry or update an old one if it exists.

    Args:
        asset_id
        catalog
        xmin
        ymin
        xmax
        ymax
        utc_datetime
        mediatype
        description
        uri
        local_path
        raster_min
        raster_max
        raster_mean
        raster_stdev
        default_style
        expiration_utc_datetime

    Returns:
        New or Updated CatalogEntry object.

    """
    catalog_entry = CatalogEntry.query.filter(
        CatalogEntry.asset_id == asset_id,
        CatalogEntry.catalog == catalog).one_or_none()

    if catalog_entry is None:
        catalog_entry = CatalogEntry(
            asset_id=asset_id,
            catalog=catalog,
            xmin=xmin,
            ymin=ymin,
            xmax=xmax,
            ymax=ymax,
            utc_datetime=utc_datetime,
            mediatype=mediatype,
            description=description,
            uri=uri,
            local_path=local_path,
            raster_min=raster_min,
            raster_max=raster_max,
            raster_mean=raster_mean,
            raster_stdev=raster_stdev,
            default_style=default_style,
            expiration_utc_datetime=expiration_utc_datetime)
        db.session.add(catalog_entry)
    else:
        catalog_entry.xmin = xmin
        catalog_entry.ymin = ymin
        catalog_entry.xmax = xmax
        catalog_entry.ymax = ymax
        catalog_entry.utc_datetime = utc_datetime
        catalog_entry.mediatype = mediatype
        catalog_entry.description = description
        catalog_entry.uri = uri
        catalog_entry.local_path = local_path
        catalog_entry.raster_min = raster_min
        catalog_entry.raster_max = raster_max
        catalog_entry.raster_mean = raster_mean
        catalog_entry.raster_stdev = raster_stdev
        catalog_entry.default_style = default_style
        catalog_entry.expiration_utc_datetime = expiration_utc_datetime
    return catalog_entry


def update_attributes(asset_id, catalog, attribute_dict):
    """Update arbitrary attributes associated with catalog:asset_id.

    Args:
        asset_id (str): asset ID string
        catalog (str): catalog ID string
        attribute_dict (dict): mapping of key/value pairs to store associated
        with catalog:asset_id

    Returns:
        None.

    """
    for key, value in attribute_dict.items():
        attribute = Attribute.query.filter(
            Attribute.asset_id == asset_id,
            Attribute.catalog == catalog).one_or_none()
        if attribute is None:
            attribute = Attribute(
                asset_id=asset_id,
                catalog=catalog,
                key=key,
                value=value)
            db.session.add(attribute)
        else:
            attribute.value = value
