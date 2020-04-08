"""Flask APP to manage the GeoServer."""
import argparse
import flask
import logging
import urllib.parse

import requests
import retrying


APP = flask.Flask(__name__)


logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'),
    filename='quad_cache_log.txt')
LOGGER = logging.getLogger(__name__)


@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=5000)
def do_rest_action(session_fn, host, suburl):
    """Do a 'get' for the host/suburl."""
    try:
        return session_fn(urllib.parse.urljoin(host, suburl))
    except Exception:
        LOGGER.exception('error in function')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GeoServer manager')
    parser.add_argument(
        'geoserver_host', type=str, help='geoserver host/port to connect to')
    parser.add_argument(
        'geoserver_admin_password', type=str, help='geoserver admin password')
    args = parser.parse_args()

    session = requests.Session()
    session.auth = ('admin', args.geoserver_admin_password)

    r = do_rest_action(
        session.get, args.geoserver_host, 'geoserver/rest/workspaces.json')
    result = r.json()

    for workspace in result['workspaces']['workspace']:
        workspace_name = workspace['name']
        r = do_rest_action(
            session.delete, args.geoserver_host,
            'geoserver/rest/workspaces/%s?recurse=true' % workspace_name)
        LOGGER.debug("delete result for %s: %s", workspace_name, str(r.json()))
