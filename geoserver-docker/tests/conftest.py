import pytest

from flanker.addresslib import address
from stac_api import create_app
from stac_api.auth.models import User, db
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
