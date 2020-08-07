from stac_api.auth.models import db
from stac_api.auth import queries


def test_find_user_by_email(user):
    # When there is no matching user:
    assert queries.find_user_by_email(None) is None
    assert queries.find_user_by_email("a_user@example.com") is None
    assert queries.find_user_by_email(user.email) is None

    # When there is:
    db.session.add(user)
    db.session.commit()
    assert queries.find_user_by_email(user.email) == user


def test_find_user_by_id(user):
    # When there is no matching user:
    assert queries.find_user_by_id(None) is None
    assert queries.find_user_by_id(1234) is None
    assert queries.find_user_by_id(user.id) is None

    # When there is:
    db.session.add(user)
    db.session.commit()
    assert queries.find_user_by_id(user.id) == user
