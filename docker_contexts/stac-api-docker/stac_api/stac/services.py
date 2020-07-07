"""Services for STAC API SQLAlchemy."""
import uuid
from flanker.addresslib import address

from . import utils
from .models import User, db

MIN_PASSWORD_LENGTH = 10


def create_user(email, password, first_name, last_name, organization):
    """ Create a User.

    Note: The db.session is not committed. Be sure to commit the session.

    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Passwords must have length of at least {MIN_PASSWORD_LENGTH}"
        )
    if address.parse(email) is None:
        raise ValueError("Invalid email")
    if first_name is None or len(first_name) == 0:
        raise ValueError("Invalid first_name")
    if last_name is None or len(last_name) == 0:
        raise ValueError("Invalid last_name")

    p_hash, p_salt = utils.make_hash(password)
    user = User(
        uuid=uuid.uuid4().hex,
        email=email,
        password_hash=p_hash,
        password_salt=p_salt,
        first_name=first_name,
        last_name=last_name,
        organization=organization,
    )
    db.session.add(user)
    return user
