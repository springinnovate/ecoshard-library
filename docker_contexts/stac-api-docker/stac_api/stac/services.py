"""Services for STAC API SQLAlchemy."""
import uuid
from flanker.addresslib import address

from . import utils
from .models import db
from .models import Job

MIN_PASSWORD_LENGTH = 10


def create_job(job_id, data_uri, job_status):
    """Create a job record to monitor job progress.

    Args:
        job_id (str): unique string to index the job
        data_uri (str): URI to data that are being processed
        job_status (str): string of job status to report when queried

    Returns:
        None.

    """
    job = Job(
        job_id=job_id,
        job_status=job_status,
        )
    db.session.add(job)
    return job
