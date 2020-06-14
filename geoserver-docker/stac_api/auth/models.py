from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    organization = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(127), nullable=False)
    password_salt = db.Column(db.String(127), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.utcnow()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"
