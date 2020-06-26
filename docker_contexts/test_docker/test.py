"""Tracer code for setting up sqlalchemy."""
import argparse
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dbuser', type=str, help='database username')
    parser.add_argument('dbpassword', type=str, help='database password')
    parser.add_argument('dbhost', type=str, help='database host')
    args = parser.parse_args()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        f'postgresql://{args.dbuser}:{args.dbpassword}@{args.dbhost}'
    db = SQLAlchemy(app)

    class User(db.Model):
        __tablename__ = "users"

        id = db.Column(db.Integer, primary_key=True)
        uuid = db.Column(db.String(32), nullable=False, server_default="")
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

    db.create_all()

    guest = User(
        uuid='sdfjkldsfljk',
        first_name='test',
        last_name='test',
        organization='test',
        email='test',
        password_hash='test',
        password_salt='test',
        )
    db.session.add(guest)
    db.session.commit()

    for user in User.query.all():
        print(user)
