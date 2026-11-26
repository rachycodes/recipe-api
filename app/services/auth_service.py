from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from ..models import User
from ..extensions import db


def create_user(
    username: str,
    email: str,
    password: str
):
    """Register a new user."""

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )

    try:
        db.session.add(user)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return None, "integrity_error"

    return user, None

def get_user_by_username(username: str):
    """Retrieve a user by their username."""

    return db.session.scalar(
        db.select(User).where(User.username == username)
    )