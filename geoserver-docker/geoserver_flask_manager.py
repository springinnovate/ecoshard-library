"""Flask APP to manage the GeoServer."""
import argparse
import flask
import urllib.parse

import requests

APP = flask.Flask(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GeoServer manager')
    parser.add_argument(
        'geoserver_host', type=str, help='geoserver host/port to connect to')
    parser.add_argument(
        'geoserver_admin_password', type=str, help='geoserver admin password')

    args = parser.parse_args()

    r = requests.get(
        urllib.parse.urljoin(
            args.geoserver_host, 'geoserver/rest/layers.json'),
        auth=('admin', args.geoserver_admin_password))
    result = r.json()
    print(result)
    for layer in result['layers']:
        print(layer['name'])
