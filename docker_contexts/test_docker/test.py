"""Tracer code for setting up sqlalchemy."""
import argparse

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #'${DB_USER}', '${DB_PASSWORD}', 'db:5432'
    parser.add_argument('dbuser', type=str, help='database username')
    parser.add_argument('dbpassword', type=str, help='database password')
    parser.add_argument('dbhost', type=str, help='database host')
    args = parser.parse_args()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        f'postgresql://{args.dbuser}:{args.dbpassword}@{args.dbhost}'
    db = SQLAlchemy(app)
