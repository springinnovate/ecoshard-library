"""Example how how to publish many rasters if they are in a csv."""
import argparse
import logging
import json
import time

import pandas
import requests

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'))
LOGGER = logging.getLogger(__name__)


def publish(
        gs_uri, host_port, api_key, asset_id, catalog, mediatype,
        description, attribute_dict, force=False):
    """Publish a gs raster to an ecoserver.

    Args:
        gs_uri (str): path to gs:// bucket that will be readable by
            `host_port`.
        host_port (str): `host:port` string pair to identify server to post
            publish request to.
        api_key (str): an api key that as write access to the catalog on the
            server.
        asset_id (str): unique id for the catalog
        catalog (str): STAC catalog to post to on the server
        mediatype (str): STAC media type, only GeoTIFF supported
        description (str): description of the asset
        force (bool): if already exists on the server, request an overwrite.
        attribute_dict (dict): these key/value pairs are added as additional
            elements in the attribute database for this asset.

    Returns:
        None

    """
    post_url = f'http://{host_port}/api/v1/publish'

    LOGGER.debug('publish posting to here: %s' % post_url)
    publish_response = requests.post(
        post_url,
        params={'api_key': api_key},
        json=json.dumps({
            'uri': gs_uri,
            'asset_id': asset_id,
            'catalog': catalog,
            'mediatype': mediatype,
            'description': description,
            'force': force,
            'attribute_dict': attribute_dict
        }))
    if not publish_response:
        LOGGER.error(f'response from server: {publish_response.text}')
        raise RuntimeError(publish_response.text)

    LOGGER.debug(publish_response.json())
    callback_url = publish_response.json()['callback_url']
    LOGGER.debug(callback_url)
    while True:
        LOGGER.debug('checking server status')
        r = requests.get(callback_url)
        print(r.text)
        payload = r.json()
        if payload['status'] == 'complete':
            LOGGER.info(
                'published! fetch with:\npython -m ecoshard fetch '
                f'--api_key {api_key} --catalog {catalog} '
                f'--asset_id {asset_id} --asset_type WMS_preview')
            break
        if 'error' in payload['status'].lower():
            LOGGER.error(payload['status'])
            break
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Single shot delete.')
    parser.add_argument(
        '--host_port', type=str, required=True,
        help='host:port of server')
    parser.add_argument(
        '--api_key', type=str, required=True,
        help='api key with access to write to catalog')
    parser.add_argument(
        '--catalog', type=str, required=True,
        help='catalog to delete from')
    parser.add_argument(
        '--asset_id', type=str, required=True,
        help='asset to delete')

    args = parser.parse_args()

    post_url = f'http://{args.host_port}/api/v1/delete'

    LOGGER.debug('deleting to here: %s' % post_url)
    delete_response = requests.post(
        post_url,
        params={'api_key': args.api_key},
        json=json.dumps({
            'asset_id': args.asset_id,
            'catalog': args.catalog,
        }))
    if not delete_response:
        LOGGER.error(f'response from server: {delete_response.text}')
        raise RuntimeError(delete_response.text)
