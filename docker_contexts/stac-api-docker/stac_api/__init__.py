"""Top level STAC api app."""
import json
import logging
import logging.config
import os
import threading

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
PUBLIC_API_KEY = 'public'


def create_app():
    """Create the Geoserver STAC Flask app."""
    LOGGER.debug('starting up!')
    # wait for API calls

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', None),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PASSWORD_FILE_PATH=os.environ.get('PASSWORD_FILE_PATH', None),
        GEOSERVER_DATA_DIR=os.environ.get('GEOSERVER_DATA_DIR', None),
        GEOSERVER_MANAGER_HOST=os.environ.get('GEOSERVER_MANAGER_HOST', None),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', None),
        SIGN_URL_PUBLIC_KEY_PATH=os.environ.get(
            'SIGN_URL_PUBLIC_KEY_PATH', None),
    )

    # config.py should contain a real secret key and
    # a real IP address/hostname
    if os.path.exists('config.py'):
        app.config.from_pyfile('config.py', silent=False)
        app.config['PASSWORD_FILE_PATH'] = os.path.join(
            app.config['GEOSERVER_DATA_DIR'], 'secrets', 'password')
        with app.app_context():
            stac.initalize_geoserver()
    else:
        LOGGER.warning("config.py not found")

    flask_cors.CORS(app)

    db.init_app(app)
    migrate = Migrate(app, db)

    app.register_blueprint(auth.auth_bp, url_prefix="/users")
    app.register_blueprint(stac.stac_bp, url_prefix="/api/v1")

    # TODO: remove any old jobs

    # register a public api key
    with app.app_context():
        public_access_map = stac.queries.get_allowed_permissions_map('public')
        if public_access_map is None:
            # create the key/permissions
            stac.services.update_api_key(
                'public', {'public:READ', 'public:WRITE'})
            db.session.commit()

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
