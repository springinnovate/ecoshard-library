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

    class Job(db.Model):
        __tablename__ = 'job_table'
        job_id = db.Column(db.String, primary_key=True)
        uri = db.Column(db.String, nullable=False)
        job_status = db.Column(db.String, nullable=False)
        active = db.Column(db.Integer, nullable=False)
        last_accessed_utc = db.Column(db.String, nullable=False, index=True)

        def __repr__(self):
            return (
                f"<Job ID: {self.job_id}, uri: {self.uri}, "
                f"job status: {self.job_status}, active: {self.active}, "
                f"last_accessed: {self.last_accessed_utc}")

    class CatalogEntry(db.Model):
        __tablename__ = 'catalog_table'

        asset_id = db.Column(db.String, primary_key=True)
        catalog = db.Column(db.String, primary_key=True)
        bb_xmin = db.Column(db.Float, nullable=False, index=True)
        bb_xmax = db.Column(db.Float, nullable=False, index=True)
        bb_ymin = db.Column(db.Float, nullable=False, index=True)
        bb_ymax = db.Column(db.Float, nullable=False, index=True)
        utc_datetime = db.Column(db.String, nullable=False, index=True)
        expiration_utc_datetime = db.Column(db.String, nullable=False)
        mediatype = db.Column(db.String, nullable=False, index=True)
        description = db.Column(db.String, nullable=False)
        uri = db.Column(db.String, nullable=False)
        local_path = db.Column(db.String, nullable=False)
        raster_min = db.Column(db.Float, nullable=False)
        raster_max = db.Column(db.Float, nullable=False)
        raster_mean = db.Column(db.Float, nullable=False)
        raster_stdev = db.Column(db.Float, nullable=False)
        default_style = db.Column(db.String, nullable=False)

        def __repr__(self):
            return f'Catalog: {self.catalog}, Asset: {self.asset_id}'

    class Attribute(db.Model):
        __tablename__ = 'attribute_table'

        asset_id = db.Column(db.String, primary_key=True)
        catalog = db.Column(db.String, primary_key=True)
        key = db.Column(db.String, primary_key=True)
        value = db.Column(db.String)

        def __repr__(self):
            return (
                f'Catalog: {self.catalog}, Asset: {self.asset_id} '
                f'-- {self.key}:{self.value}')

    class APIKey(db.Model):
        __tablename__ = 'api_keys'

        api_key = db.Column(db.String, primary_key=True)
        # permissions is string of READ:catalog WRITE:catalog CREATE
        # where READ/WRITE:catalog allow access to read and write the
        # catalog and CREATE allows creation of a new catalog.
        permissions = db.Column(db.String)

        def __repr__(self):
            return f'{self.api_key}: {self.permissions}'

    class GlobalVariable(db.Model):
        __tablename__ = 'global_variables'

        key = db.Column(db.String, primary_key=True)
        value = db.Column(db.LargeBinary)

        def __repr__(self):
            return f'{self.key}: {self.value}'

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
