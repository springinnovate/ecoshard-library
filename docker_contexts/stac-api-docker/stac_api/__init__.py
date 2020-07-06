"""Top level STAC api app."""
import json
import logging
import logging.config
import os

from .auth import auth
from .stac import stac
from .db import db
from flask import Flask
import flask_cors
from flask_migrate import Migrate

LOG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'logging.json')

with open(LOG_FILE_PATH) as f:
    logging.config.dictConfig(json.load(f))
LOGGER = logging.getLogger(__name__)


def create_app(config=None):
    """Create the Geoserver STAC Flask app."""
    LOGGER.debug('starting up!')
    # wait for API calls

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # config.py should contain a real secret key and
    # a real IP address/hostname
    app.config.from_pyfile('config.py', silent=False)
    if config is not None:
        app.config.from_mapping(config)
    flask_cors.CORS(app)

    db.init_app(app)
    migrate = Migrate(app, db)

    print(app.config)

    app.register_blueprint(auth.auth_bp, url_prefix="/users")
    app.register_blueprint(stac.stac_bp, url_prefix="/api/v1")

    stac.initalize_geoserver(
        app.config['STAC_DATABASE_URI'], app.config['SERVER_NAME'])

    # TODO: remove any old jobs

    # start up an expiration monitor
    expiration_monitor_thread = threading.Thread(
        target=stac.expiration_monitor)
    expiration_monitor_thread.daemon = True
    expiration_monitor_thread.start()

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app
