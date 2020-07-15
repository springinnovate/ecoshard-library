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


class ReverseProxied(object):
    """From https://stackoverflow.com/a/37842465/42897."""
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_FORWARDED_PROTO')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


def create_app():
    """Create the Geoserver STAC Flask app."""
    LOGGER.debug('starting up!')
    # wait for API calls

    app = Flask(__name__, instance_relative_config=False)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', None),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PASSWORD_FILE_PATH=os.environ.get('PASSWORD_FILE_PATH', None),
        INTER_GEOSERVER_DATA_DIR=os.environ.get('INTER_GEOSERVER_DATA_DIR', None),
        GEOSERVER_DATA_DIR=os.environ.get('GEOSERVER_DATA_DIR', None),
        GEOSERVER_MANAGER_HOST=os.environ.get('GEOSERVER_MANAGER_HOST', None),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', None),
        SIGN_URL_PUBLIC_KEY_PATH=os.environ.get(
            'SIGN_URL_PUBLIC_KEY_PATH', None),
        DEFAULT_STYLE=os.environ.get(
            'DEFAULT_STYLE', 'greens')
    )

    flask_cors.CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)

    app.register_blueprint(auth.auth_bp, url_prefix="/users")
    app.register_blueprint(stac.stac_bp, url_prefix="/api/v1")

    # TODO: remove any old jobs

    # register a public api key
    with app.app_context():
        public_access_map = stac.queries.get_allowed_permissions_map('public')
        LOGGER.debug(f'public_access_map: {public_access_map}')
        if public_access_map is None:
            # create the key/permissions
            stac.services.update_api_key(
                PUBLIC_API_KEY,
                {f'{PUBLIC_API_KEY}:READ', f'{PUBLIC_API_KEY}:WRITE'})
            db.session.commit()

    with app.app_context():
        public_access_map = stac.queries.get_allowed_permissions_map('public')
        LOGGER.debug(f'public access: {public_access_map}')

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
