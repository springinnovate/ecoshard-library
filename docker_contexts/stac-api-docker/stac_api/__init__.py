"""Top level STAC api app."""
import argparse
import json
import logging
import logging.config
import os
import secrets
import threading

from .auth import auth
from .stac import stac
from .db import db
from flask import Flask
import flask_cors
from flask_migrate import Migrate
import requests

LOG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'logging.json')

with open(LOG_FILE_PATH) as f:
    logging.config.dictConfig(json.load(f))
LOGGER = logging.getLogger("stac")


class ReverseProxied(object):
    """From https://stackoverflow.com/a/37842465/42897."""
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_FORWARDED_PROTO')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


def create_app(config=None):
    """Create the Geoserver STAC Flask app."""
    LOGGER.debug('starting up!')
    # wait for API calls

    public_catalog_string = os.environ.get('PUBLIC_CATALOGS', None)
    if public_catalog_string not in ['', None]:
        public_catalog_list = public_catalog_string.split(',')
    else:
        public_catalog_list = []

    app = Flask(__name__, instance_relative_config=False)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', None),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        GEOSERVER_PASSWORD_FILE=os.environ.get('GEOSERVER_PASSWORD_FILE', None),
        GEOSERVER_USER=os.environ.get('GEOSERVER_USER', None),
        INTER_GEOSERVER_DATA_DIR=os.environ.get('INTER_GEOSERVER_DATA_DIR', None),
        GEOSERVER_DATA_DIR=os.environ.get('GEOSERVER_DATA_DIR', None),
        API_SERVER_HOST=os.environ.get('API_SERVER_HOST', None),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', None),
        SIGN_URL_PUBLIC_KEY_PATH=os.environ.get(
            'SIGN_URL_PUBLIC_KEY_PATH', None),
        DEFAULT_STYLE=os.environ.get(
            'DEFAULT_STYLE', 'greens'),
        DISK_RESIZE_SERVICE_HOST=os.environ.get(
            'DISK_RESIZE_SERVICE_HOST', None),
        FLASK_INITALIZE_ONLY=os.environ.get(
            'FLASK_INITALIZE_ONLY', 0),
        ROOT_API_KEY=os.environ.get(
            'ROOT_API_KEY', None),
        MAP_SERVER_HOST=os.environ.get(
            'MAP_SERVER_HOST', None),
        PUBLIC_CATALOGS=public_catalog_list,
        EMAIL_DRIVER=os.environ.get('EMAIL_DRIVER', 'null'),
        SENDGRID_API_KEY=os.environ.get('SENDGRID_API_KEY', None),
        SENDGRID_RESET_TEMPLATE_ID=os.environ.get(
            'SENDGRID_RESET_TEMPLATE_ID', None),
        MAPBOX_BASEMAP_URL=os.environ.get('MAPBOX_BASEMAP_URL', None),
        MAPBOX_ACCESS_TOKEN=os.environ.get('MAPBOX_ACCESS_TOKEN', None),
    )
    LOGGER.debug(os.environ.get('INTER_GEOSERVER_DATA_DIR'))

    # add custom config options (typically for testing)
    if config is not None:
        app.config.from_mapping(config)

    flask_cors.CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)

    app.register_blueprint(auth.auth_bp, url_prefix="/users")
    app.register_blueprint(stac.stac_bp, url_prefix="/api/v1")

    LOGGER.debug(f'value of {app.config["FLASK_INITALIZE_ONLY"]}')

    if int(app.config['FLASK_INITALIZE_ONLY']) == 1:
        LOGGER.debug('initalize only! returning now')
        return app

    with app.app_context():
        LOGGER.debug(f"here's the value of root: {app.config['ROOT_API_KEY']}")
        if app.config['ROOT_API_KEY'] is not None:
            root_access_map = stac.queries.get_allowed_permissions_map(
                app.config['ROOT_API_KEY'])
            LOGGER.debug(f'current root_access_map: {root_access_map}')
            # create the key/permissions
            stac.services.update_api_key(
                app.config["ROOT_API_KEY"],
                {f'READ:*', f'WRITE:*'})

        # remove any old jobs
        jobs_removed = stac.services.clear_all_jobs()
        LOGGER.info(f'will remove {jobs_removed} previously running jobs')
        db.session.commit()

    # start up an expiration monitor
    expiration_monitor_thread = threading.Thread(
        target=stac.expiration_monitor,
        args=(app,))
    expiration_monitor_thread.daemon = True
    expiration_monitor_thread.start()

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.app = app

    initalize_geoserver(app)
    return app


def initalize_geoserver(app):
    """Ensure database exists, set security, and set server initial stores."""
    # make new random admin password
    with db.app.app_context():
        if app.config['GEOSERVER_PASSWORD_FILE'] is None:
            LOGGER.warn(
                'no password file path defined, assuming unconfigured and'
                'not initalizing geoserver')
            return

        if os.path.exists(app.config['GEOSERVER_PASSWORD_FILE']):
            with open(app.config['GEOSERVER_PASSWORD_FILE'], 'r') as \
                    password_file:
                geoserver_password = password_file.read()
            LOGGER.info(f'password already set {geoserver_password}')
            return

        try:
            os.makedirs(os.path.dirname(app.config['GEOSERVER_PASSWORD_FILE']))
        except OSError:
            pass
        with open(app.config['GEOSERVER_PASSWORD_FILE'], 'w') as password_file:
            geoserver_password = secrets.token_urlsafe(16)
            password_file.write(geoserver_password)

        session = requests.Session()
        # 'geoserver' is the default geoserver password, we'll need to be
        # authenticated to do the push
        session.auth = (app.config['GEOSERVER_USER'], 'geoserver')
        password_update_request = stac.do_rest_action(
            session.put,
            f'https://{app.config["API_SERVER_HOST"]}',
            'geoserver/rest/security/self/password',
            json={
                'newPassword': geoserver_password
            })
        if not password_update_request:
            raise RuntimeError(
                'could not reset admin password: ' +
                password_update_request.text)

        # there's a bug in GeoServer 2.17 that requires a reload of the
        # configuration before the new password is used
        password_update_request = stac.do_rest_action(
            session.post,
            f'https://'
            f'{app.config["API_SERVER_HOST"]}',
            'geoserver/rest/reload')
