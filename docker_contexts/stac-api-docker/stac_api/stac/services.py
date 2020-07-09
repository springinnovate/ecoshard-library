"""Services for STAC API SQLAlchemy."""
import uuid
from flanker.addresslib import address

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
