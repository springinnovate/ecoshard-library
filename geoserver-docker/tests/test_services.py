import pytest

from stac_api.auth import services, utils

AN_EMAIL = "user@example.com"
A_PASSWORD = "apassword!"
A_FIRST = "Danny"
A_LAST = "Fitzgerald"
AN_ORG = "AnyCo"


def test_create_user_validate_email(app, monkeypatch):
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
