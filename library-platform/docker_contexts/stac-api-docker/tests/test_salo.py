from datetime import datetime
import stac_api
from stac_api.auth.models import db
from stac_api.auth.utils import make_jwt
from stac_api.stac import stac

def test_fetch_no_user(client):
    # Fetching without a jwt token fails.
    result = client.post(
        "/api/v1/fetch",
        content_type="application/json",
        json={
            'catalog': 'cfo',
            'asset_id': 'an-asset-id',
            'type': 'uri',
        }
    )
    assert result.status_code == 401


def test_fetch_valid_token(client, user, catalog_entry, monkeypatch):
    # Fetching with valid JWT token succeeds
    db.session.add(user)
    db.session.add(catalog_entry)
    db.session.commit()
    calling_token = make_jwt(user).decode("utf-8")

    result = client.post(
        "/api/v1/fetch",
        content_type="application/json",
        headers={"Authorization": f"Bearer {calling_token}"},
        json={
            'catalog': 'cfo',
            'asset_id': 'an-asset-id',
            'type': 'uri',
        }
    )
    assert result.status_code == 200


def test_fetch_jwt(client, user, catalog_entry, monkeypatch):
    db.session.add(user)
    db.session.add(catalog_entry)
    db.session.commit()

    # Fetching without a JWT token, but with an api_token works
    def mock_validate(*args, **kwargs):
        return 'valid'

    monkeypatch.setattr(stac, "validate_api", mock_validate)
    result = client.post(
        "/api/v1/fetch?api_key=an-api-key",
        content_type="application/json",
        json={
            'catalog': 'cfo',
            'asset_id': 'an-asset-id',
            'type': 'uri',
        }
    )
    assert result.status_code == 200
    assert result.json["type"] == "uri"


def test_fetch_bad_api_token(client, user, monkeypatch):
    # Fetching without a JWT token, but with an api_token works
    def mock_validate_failure(*args, **kwargs):
        return 'invalid'

    monkeypatch.setattr(stac, "validate_api", mock_validate_failure)
    result = client.post(
        "/api/v1/fetch?api_key=an-api-key",
        content_type="application/json",
        json={
            'catalog': 'cfo',
            'asset_id': 'an-asset-id',
            'type': 'uri',
        }
    )
    assert result.status_code == 200
    assert result.data == b'invalid'
