from .models import User


def find_user_by_email(email):
    """ Find a user by their email, or return None """
    return User.query.filter(User.email == email).one_or_none()


def find_user_by_id(user_id):
    """ Find a user by their id, or return None """
    return User.query.filter(User.id == user_id).one_or_none()
