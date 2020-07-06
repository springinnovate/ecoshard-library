"""Top level STAC api app."""
from .auth import auth_bp
from .db import db
#from .stac import stac_bp
from flask import Flask
from flask_migrate import Migrate

app = Flask(__name__)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(auth_bp, url_prefix="/users")
#app.register_blueprint(stac_bp, url_prefix="/api")
