"""Implementation of STAC API for Salo."""
import argparse
import urllib.parse

import flask
import pystac

APP = flask.Flask(__name__)
TITLE = 'SALO API'


@APP.route('/api/v1')
def capabilities():
    """Essential characteristics of this API."""
    response_json = {
        'title': TITLE,
        'description': TITLE,
        'links': [
            {
                'href': flask.url_for('capabilities', _external=True),
                'rel': 'self',
                'type': 'application/json',
                'title': 'this document',
                },
            {
                'href': flask.url_for('collections', _external=True),
                'rel': 'data',
                'type': 'application/json',
                'title': 'Information about the feature collections',
                },
            {
                'href': flask.url_for('search', _external=True),
                'rel': 'search',
                'type': 'application/json',
                'title': 'Search across feature collections',
                },
            ],
        'stac_version': '0.9.0',
        'id': '',
        }
    return response_json


@APP.route('/api/v1/collections')
def collections():
    pass


@APP.route('/api/v1/search')
def search():
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='launch STAC server')
    parser.add_argument(
        '--external_ip', type=str, default='localhost',
        help='external ip of this host')
    parser.add_argument(
        '--external_port', type=str, default='8080',
        help='external port of this host')
    args = parser.parse_args()

    # wait for API calls
    APP.config.update(SERVER_NAME=f'{args.external_ip}:{args.external_port}')
    APP.run(host='0.0.0.0', port=args.external_port)
