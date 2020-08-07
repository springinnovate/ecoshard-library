import pytest
import uuid

from flanker.addresslib import address
from stac_api import create_app
from stac_api.db import db
from stac_api.auth.models import User
from stac_api.stac.models import CatalogEntry
from stac_api.auth.utils import make_hash

USER_PASSWORD = "atestpass"


@pytest.fixture
def app():
    # create a temporary file to isolate the database for each test
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
            "DEBUG": True,
            "SECRET_KEY": "PYTEST",
            "FLASK_INITALIZE_ONLY": 1,
        }
    )
    db.init_app(app)

    with app.app_context():
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    p_hash, p_salt = make_hash(USER_PASSWORD)
    return User(
        uuid=uuid.uuid4().hex,
        email="anemail@example.com",
        first_name="firstname",
        last_name="lastname",
        organization="Any Organization",
        password_hash=p_hash,
        password_salt=p_salt,
    )


@pytest.fixture(autouse=True)
def no_mx_dns_calls(monkeypatch):
    monkeypatch.setattr(address, "validate_address", lambda x: True)


@pytest.fixture
def catalog_entry(app):
    return CatalogEntry(
        asset_id="an-asset-id",
        catalog="cfo",
        bb_xmin=0.0,
        bb_xmax=0.0,
        bb_ymin=0.0,
        bb_ymax=0.0,
        utc_datetime="",
        expiration_utc_datetime="",
        mediatype="",
        description="",
        uri="",
        local_path="",
        raster_min=0.0,
        raster_max=0.0,
        raster_mean=0.0,
        raster_stdev=0.0,
        default_style="",
    )


