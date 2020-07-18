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
        GEOSERVER_PASSWORD_FILE=os.environ.get('GEOSERVER_PASSWORD_FILE', None),
        GEOSERVER_USER=os.environ.get('GEOSERVER_USER', None),
        INTER_GEOSERVER_DATA_DIR=os.environ.get('INTER_GEOSERVER_DATA_DIR', None),
        GEOSERVER_DATA_DIR=os.environ.get('GEOSERVER_DATA_DIR', None),
        GEOSERVER_MANAGER_HOST=os.environ.get('GEOSERVER_MANAGER_HOST', None),
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
        ALLOW_PUBLIC_API=os.environ.get(
            'ALLOW_PUBLIC_API', 0),
    )
    LOGGER.debug(os.environ.get('INTER_GEOSERVER_DATA_DIR'))

    flask_cors.CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)

    app.register_blueprint(auth.auth_bp, url_prefix="/users")
    app.register_blueprint(stac.stac_bp, url_prefix="/api/v1")

    if app.config['FLASK_INITALIZE_ONLY']:
        LOGGER.debug('initalize only! returning now')
        return app

    with app.app_context():
        if app.config['ALLOW_PUBLIC_API']:
            public_access_map = stac.queries.get_allowed_permissions_map(
                'public')
            LOGGER.debug(f'public_access_map: {public_access_map}')
            if public_access_map is None:
                # create the key/permissions
                stac.services.update_api_key(
                    PUBLIC_API_KEY,
                    {f'{PUBLIC_API_KEY}:READ', f'{PUBLIC_API_KEY}:WRITE'})

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
            f'{app.config["GEOSERVER_MANAGER_HOST"]}',
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
            f'{app.config["GEOSERVER_MANAGER_HOST"]}',
            'geoserver/rest/reload')
