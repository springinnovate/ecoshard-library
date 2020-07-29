import uuid
from datetime import datetime, timedelta

from flanker.addresslib import address

from . import mail, utils
from .models import User, db
from .queries import find_user_by_email

MIN_PASSWORD_LENGTH = 10
RESET_TOKEN_EXPIRATION_HOURS = 24


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


def update_password(user, password, reset_token):
    """ Change a user's password.
    """
    if reset_token != user.reset_token:
        raise ValueError("Reset tokens do not match")

    expiration = user.reset_token_expires_at.utcnow() + timedelta(
        hours=RESET_TOKEN_EXPIRATION_HOURS
    )
    if expiration < datetime.utcnow():
        raise ValueError("reset_token is expired")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Passwords must have length of at least {MIN_PASSWORD_LENGTH}"
        )

    p_hash, p_salt = utils.make_hash(password)
    user.password_hash = p_hash
    user.password_salt = p_salt
    user.reset_token = ""

    db.session.commit()


def request_password_reset(user):
    """ Reset a User's password, and send a reset user.

    Returns True on success.
    """
    user.reset_token = uuid.uuid4().hex
    user.reset_token_expires_at = datetime.utcnow()
    db.session.commit()

    return mail.make_driver().send_reset_email(user)
