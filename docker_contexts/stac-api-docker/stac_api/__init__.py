# sitemaker/__init__.py

from flask import Flask
from .auth import auth_bp, auth_db
from .stac import stac_bp, stac_db
from flask_migrate import Migrate

app = Flask(__name__)

auth_db.init_app(app)
migrate = Migrate(app, auth_db)

app.register_blueprint(auth_bp, url_prefix="/users")
