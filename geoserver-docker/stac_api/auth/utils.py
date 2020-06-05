import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from calendar import timegm
from typing import Tuple

import jwt
from flask import current_app
from jwt.exceptions import PyJWTError

JWT_EXPIRATION_DAYS = 14
JWT_MAX_EXPIRATION_DAYS = 3 * JWT_EXPIRATION_DAYS
JWT_ALGORITHM = "HS256"


def _s_since_epoch(dt):
    """ Convert datetime to seconds since the Unix epoch """
    return timegm(dt.utctimetuple())


def to_datetime(s_since_epoch):
    """ Convert seconds since the Unix epoch to datetime """
    return datetime.fromtimestamp(s_since_epoch, tz=timezone.utc)


def make_hash(password: str, salt: str = None) -> Tuple[str, str]:
    """ Make a hash of a password.

    If a salt is not provided, a random one is created.

    Returns the hash and salt. """
    # NIST guidelines for password storage:
    #  * salt > 32 bits
    #  * PBKDF2
    #  * iterate at least 10,000 times.
    #  * TODO consider adding pepper (probably SECRET_KEY?)
    if salt is None:
        salt = secrets.token_urlsafe(32)
    return (
        hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 10000
        ).hex(),
        salt,
    )


def verify_hash(password: str, p_hash: str, salt: str) -> bool:
    """ Returns True when 'password' matches a value from make_hash(). """
    return make_hash(password, salt)[0] == p_hash


def make_jwt(user, max_expiration=None):
    """ Create a JWT token for a user.

    Includes two non-jwt values:
     * id: a user id.
     * max-exp: the maximum date that we want to allow one to be able to refresh
                their JWT token (enforced by verify_jwt()). Formatted as seconds
                since the Unix epoch (same as exp field)
    """
    if max_expiration is None:
        max_expiration = datetime.now() + timedelta(days=JWT_MAX_EXPIRATION_DAYS)

    expiration = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    max_expiration = _s_since_epoch(max_expiration)
    return jwt.encode(
        {
            "id": user.id,
            "exp": expiration,
            "max-exp": max_expiration,
            "iss": current_app.name,
            "iat": datetime.utcnow(),
        },
        current_app.config["SECRET_KEY"],
        algorithm=JWT_ALGORITHM,
    )


def decode_jwt(jwt_string, secret=None):
    """ Decode a JWT token.

    Returns the JWT if it is valid, otherwise None.
    """
    if secret is None:
        secret = current_app.config["SECRET_KEY"]

    try:
        a_jwt = jwt.decode(jwt_string, secret, algorithms=JWT_ALGORITHM)

        if "id" not in a_jwt or "max-exp" not in a_jwt:
            current_app.logger.info("decode_jwt: missing id/max-exp")
            return False

        return a_jwt
    except PyJWTError:
        return False


def verify_jwt(user, jwt_string, secret=None):
    """ Verify that a JWT token is from a user, and is still valid.

    Returns True if the JWT is valid.
    """
    a_jwt = decode_jwt(jwt_string, secret)

    if not a_jwt:
        return False

    if int(a_jwt["max-exp"]) < _s_since_epoch(datetime.now()):
        return False

    return a_jwt["id"] == user.id
