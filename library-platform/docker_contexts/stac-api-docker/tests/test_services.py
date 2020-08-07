from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from stac_api.auth import services, utils
from stac_api.db import db

AN_EMAIL = "user@example.com"
A_PASSWORD = "apassword!"
A_FIRST = "Danny"
A_LAST = "Fitzgerald"
AN_ORG = "AnyCo"


def test_create_user_validate_email(app):
    # When no email is provided a ValueError is raised
    with pytest.raises(ValueError):
        services.create_user("", A_PASSWORD, A_FIRST, A_LAST, AN_ORG)

    # When an invalid email is provided a ValueError is raised.
    with pytest.raises(ValueError):
        services.create_user("bad@@example.com", A_PASSWORD, A_FIRST, A_LAST, AN_ORG)


def test_create_user_validate_password(app):
    # When a password of length < 10 is provided, a ValueError is raised.
    with pytest.raises(ValueError):
        services.create_user(AN_EMAIL, "", A_FIRST, A_LAST, AN_ORG)
    with pytest.raises(ValueError):
        services.create_user(AN_EMAIL, "123456789", A_FIRST, A_LAST, AN_ORG)

    # When a password of length >= 10 is provided, a user is created:
    assert (
        services.create_user(AN_EMAIL, "1234567890", A_FIRST, A_LAST, AN_ORG)
        is not None
    )


def test_create_user_validate_first_name(app):
    # When no first name is provided, a ValueError is raised.
    with pytest.raises(ValueError):
        services.create_user(AN_EMAIL, A_PASSWORD, None, A_LAST, AN_ORG)
    with pytest.raises(ValueError):
        services.create_user(AN_EMAIL, A_PASSWORD, "", A_LAST, AN_ORG)


def test_create_user_validate_last_name(app):
    # When no last name is provided, a ValueError is raised.
    with pytest.raises(ValueError):
        services.create_user(AN_EMAIL, A_PASSWORD, A_LAST, None, AN_ORG)
    with pytest.raises(ValueError):
        services.create_user(AN_EMAIL, A_PASSWORD, A_LAST, "", AN_ORG)


def test_create_user(app):
    # Given: good email/passwords are provided, a user is saved
    user = services.create_user(AN_EMAIL, A_PASSWORD, A_FIRST, A_LAST, AN_ORG)
    # Then: a user is created, with email and password hash.
    assert user.email == AN_EMAIL
    assert user.password_hash != A_PASSWORD
    assert user.first_name == A_FIRST
    assert user.last_name == A_LAST
    assert user.organization == AN_ORG
    assert len(user.password_salt) > 0
    # and the hash would return true if verified
    assert utils.verify_hash(A_PASSWORD, user.password_hash, user.password_salt)

    # The org can be None
    user = services.create_user(AN_EMAIL, A_PASSWORD, A_FIRST, A_LAST, None)
    assert user.organization == None

    # The org can be ""
    user = services.create_user(AN_EMAIL, A_PASSWORD, A_FIRST, A_LAST, "")
    assert user.organization == ""


def test_request_password_reset_email_down(app, monkeypatch):
    # Given: existing user, matching password
    user = services.create_user(AN_EMAIL, A_PASSWORD, A_FIRST, A_LAST, AN_ORG)
    db.session.add(user)
    db.session.commit()
    driver_mock = Mock()
    driver_mock.send_reset_email.return_value = False
    monkeypatch.setattr(services.mail, "make_driver", lambda: driver_mock)

    # Then: the user's reset_token is updated, and an email is sent.
    assert not services.request_password_reset(user)
    driver_mock.send_reset_email.assert_called_once()


def test_request_password_reset(app, monkeypatch):
    # Given: existing user, matching password
    user = services.create_user(AN_EMAIL, A_PASSWORD, A_FIRST, A_LAST, AN_ORG)
    db.session.add(user)
    db.session.commit()
    driver_mock = Mock()
    monkeypatch.setattr(services.mail, "make_driver", lambda: driver_mock)

    # Then: the user's reset_token is updated, and an email is sent.
    original_reset_token = user.reset_token
    assert services.request_password_reset(user)
    driver_mock.send_reset_email.assert_called_once()
    assert driver_mock.mock_calls[0][1][0].id == user.id
    assert user.reset_token != original_reset_token
    assert user.reset_token_expires_at < datetime.utcnow()


def test_update_password_no_reset_token(app, user):
    assert services.request_password_reset(user)
    with pytest.raises(ValueError):
        services.update_password(user, A_PASSWORD, "not right")


def test_update_password_bad_password(app, user):
    assert services.request_password_reset(user)
    reset_token = user.reset_token
    with pytest.raises(ValueError):
        services.update_password(user, "tooshort", user.reset_token)
    # and the token can be used again:
    assert user.reset_token == reset_token


def test_update_password_expired_token(app, user):
    # Given: user with matching reset_token and password
    assert services.request_password_reset(user)

    # Then: no update b/c the reset_token is expired
    with freeze_time(
        datetime.utcnow() + timedelta(hours=services.RESET_TOKEN_EXPIRATION_HOURS + 1)
    ), pytest.raises(ValueError):
        services.update_password(user, A_PASSWORD, user.reset_token)

    utils.verify_hash(A_PASSWORD, user.password_hash, user.password_salt)


def test_update_password(app, user):
    # Given: user with matching reset_token and password
    assert services.request_password_reset(user)
    services.update_password(user, A_PASSWORD, user.reset_token)

    # Then: the user's password is updated and the reset_token cannot be reused.
    assert utils.verify_hash(A_PASSWORD, user.password_hash, user.password_salt)
    assert user.reset_token == ""
