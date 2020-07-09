from datetime import datetime
import stac_api
from stac_api.auth.models import db
from stac_api.auth.utils import make_jwt

def test_fetch(client, user, monkeypatch):
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

    db.session.add(user)
    db.session.commit()
    calling_token = make_jwt(user).decode("utf-8")

    def mocksql(*args, **kwargs):
        return ['https://a_link.com', 0, 100, 50, 0, 'style']

    monkeypatch.setattr(stac_api, "_execute_sqlite", mocksql)

    # Fetching with valid JWT token succeeds
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

    # Fetching without a JWT token, but with an api_token works
    def mock_validate(*args, **kwargs):
        return 'valid'

    monkeypatch.setattr(stac_api, "validate_api", mock_validate)
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

    monkeypatch.setattr(stac_api, "validate_api", mock_validate_failure)
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
