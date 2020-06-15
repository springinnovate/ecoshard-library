import time
from datetime import datetime, timedelta

import stac_api.auth.utils
from freezegun import freeze_time
from stac_api.auth.auth import handle_error
from stac_api.auth.models import db
from stac_api.auth.queries import find_user_by_email
from stac_api.auth.utils import decode_jwt, make_jwt, verify_jwt

from .conftest import USER_PASSWORD

AN_EMAIL = "user@example.com"
TOMORROW = datetime.utcnow() + timedelta(days=1)


def _verify_content_type_and_params(client, endpoint):
    # An invalid payload receives a 400
    result = client.post(endpoint)
    assert result.status_code == 400

    # A bad content-type header returns a 400
    result = client.post(endpoint, content_type="text/html")
    assert result.status_code == 400

    # A missing key returns a 400
    result = client.post(
        endpoint, json={"email": AN_EMAIL}, content_type="application/json",
    )
    assert result.status_code == 400


def test_create_user_400(client):
    _verify_content_type_and_params(client, "/users/create")

    # A bad password returns a 400
    result = client.post(
        "/users/create",
        json={"email": AN_EMAIL, "password": ""},
        content_type="application/json",
    )
    assert result.status_code == 400

    # A bad email returns a 400
    result = client.post(
        "/users/create",
        json={
            "email": "",
            "password": "a password",
            "first_name": "first",
            "last_name": "last",
        },
        content_type="application/json",
    )
    assert result.status_code == 400

    # An unknown key returns a 400
    result = client.post(
        "/users/create",
        json={
            "email": AN_EMAIL,
            "first_name": "Aaron",
            "last_name": "Sigurður",
            "password": "a password",
            "UNKNOWN": "VALUE",
        },
        content_type="application/json",
    )
    assert result.status_code == 400


def test_create_user_200(client):
    # A user is created with valid email and valid password
    result = client.post(
        "/users/create",
        json={
            "email": AN_EMAIL,
            "first_name": "Aaron",
            "last_name": "Sigurður",
            "password": "a password",
        },
        content_type="application/json",
    )
    user = find_user_by_email(AN_EMAIL)
    assert result.status_code == 200
    assert set(result.json.keys()) == set(["id", "email", "token"])
    assert result.json["id"] == user.id

    # Attempting to create a second user with the same email should return a 400
    result = client.post(
        "/users/create",
        json={
            "email": AN_EMAIL,
            "first_name": "Aaron",
            "last_name": "Sigurður",
            "password": "a password",
            "organization": "AnyCo",
        },
        content_type="application/json",
    )
    assert result.status_code == 400
    find_user_by_email(AN_EMAIL)


def test_auth_user(client, user):
    _verify_content_type_and_params(client, "/users/auth")

    # A non-existant user returns a 401
    result = client.post(
        "/users/auth",
        json={"email": "nouser@example.com", "password": "wrong password"},
        content_type="application/json",
    )
    assert result.status_code == 401

    # An invalid password returns a 401
    db.session.add(user)
    db.session.commit()
    result = client.post(
        "/users/auth",
        json={"email": user.email, "password": "wrong password"},
        content_type="application/json",
    )
    assert result.status_code == 401

    # A valid password returns a new JWT token
    result = client.post(
        "/users/auth",
        json={"email": user.email, "password": USER_PASSWORD},
        content_type="application/json",
    )
    assert result.status_code == 200
    assert verify_jwt(user, result.json["token"])


def test_jwt_required(client, user):
    # No authorization header returns a 401
    result = client.post("/users/auth/refresh", content_type="application/json")
    assert result.status_code == 401

    # A non bearer header returns a 401
    result = client.post(
        "/users/auth/refresh",
        content_type="application/json",
        headers={"Authorization": "Basic 123456789"},
    )
    assert result.status_code == 401

    # A badly formatted bearer token returns a 401
    result = client.post(
        "/users/auth/refresh",
        content_type="application/json",
        headers={
            "Authorization": "Bearer eyJ0e  XAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwiZXhwIjoxNTkzNjI2MjQ5LCJpc3MiOiJhcHAiLCJpYXQiOjE1OTEwMzQyNDl9.-j5K1xiYx6GzyKoI5UsKnpiCA1vF1D5gBreCUlnm01o"
        },
    )
    assert result.status_code == 401

    # An badly formatted JWT token returns a 401
    result = client.post(
        "/users/auth/refresh",
        content_type="application/json",
        headers={
            "Authorization": "Bearer XXXXXXXXXXXKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwiZXhwIjoxNTkzNjI2MjQ5LCJpc3MiOiJhcHAiLCJpYXQiOjE1OTEwMzQyNDl9.-j5K1xiYx6GzyKoI5UsKnpiCA1vF1D5gBreCUlnm01o"
        },
    )
    assert result.status_code == 401

    # A valid JWT that is expired returns a 401
    db.session.add(user)
    db.session.commit()
    calling_token = make_jwt(user, TOMORROW).decode("utf-8")
    with freeze_time((TOMORROW + timedelta(days=1)).strftime("%Y-%m-%d")):
        result = client.post(
            "/users/auth/refresh",
            content_type="application/json",
            headers={"Authorization": f"Bearer {calling_token}"},
        )
        assert result.status_code == 401

    # A valid JWT token for a user that doesn't exist returns a 401
    db.session.delete(user)
    db.session.commit()
    time.sleep(1)
    result = client.post(
        "/users/auth/refresh",
        content_type="application/json",
        headers={"Authorization": f"Bearer {calling_token}"},
    )
    assert result.status_code == 401


def test_refresh(client, user):
    db.session.add(user)
    db.session.commit()
    calling_token = make_jwt(user, TOMORROW).decode("utf-8")
    calling_jwt = decode_jwt(calling_token)

    # A non json contenttype returns a 400
    result = client.post(
        "/users/auth/refresh", headers={"Authorization": f"Bearer {calling_token}"},
    )
    assert result.status_code == 400

    # A valid JWT token returns a new token
    # tokens aren't gauranteed to be unique and will be sub-second...so let a
    # little time go by to gaurantee a unique JWT is returned by the endpoint.
    time.sleep(1)
    result = client.post(
        "/users/auth/refresh",
        content_type="application/json",
        headers={"Authorization": f"Bearer {calling_token}"},
    )
    result_jwt = decode_jwt(result.json["token"])
    assert result.status_code == 200
    assert verify_jwt(user, result.json["token"])
    assert result.json["token"] != calling_token
    # its max-exp always equals the calling_token's value
    assert result_jwt["max-exp"] == calling_jwt["max-exp"]


@freeze_time("2020-05-05")
def test_refresh_max_exp(client, user):
    db.session.add(user)
    db.session.commit()
    calling_token = make_jwt(user, datetime.now()).decode("utf-8")

    # Renewing a token that is older than its max-exp returns a 401
    with freeze_time("2020-05-06"):
        result = client.post(
            "/users/auth/refresh",
            content_type="application/json",
            headers={"Authorization": f"Bearer {calling_token}"},
        )
        assert result.status_code == 401


def test_handleerror(client):
    json, status_code = handle_error("an error")
    assert status_code == 500
    assert json == {}
