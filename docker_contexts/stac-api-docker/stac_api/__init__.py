# sitemaker/__init__.py

from flask import Flask
from .auth import auth_bp, db
from flask_migrate import Migrate

app = Flask(__name__)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(auth_bp, url_prefix="/users")
