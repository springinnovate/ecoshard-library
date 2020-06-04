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
        description, attribute_dict, expiration_utc_datetime, force=False):
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
        expiration_utc_datetime (str): either empty string or UTC formatted
            time to indicate when the raster should be expired from the
            database.

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
            'attribute_dict': attribute_dict,
            'expiration_utc_datetime': expiration_utc_datetime,
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
        description='Start GeoServer REST API server.')
    parser.add_argument(
        '--host_port', type=str, required=True,
        help='host:port of server')
    parser.add_argument(
        '--api_key', type=str, required=True,
        help='api key with access to write to catalog')
    parser.add_argument(
        '--catalog_csv', type=str, required=True,
        help='path to the csv catalog to publish')
    parser.add_argument(
        '--force', action='store_true',
        help='use this to overwrite existing entries on publish')

    args = parser.parse_args()

    # keep_default_na=False ensures empty cellsare  empty strings and not NaNs
    catalog_df = pandas.read_csv(args.catalog_csv, keep_default_na=False)
    table_headers = set(catalog_df)
    LOGGER.debug(set(catalog_df))
    required_headers = {
        'gs_uri', 'catalog', 'asset_id', 'description', 'utc_datetime',
        'expiration_utc_datetime'}
    if required_headers.intersection(table_headers) != required_headers:
        raise ValueError(
            f'missing headers in catalog, expected {required_headers} '
            f'got {set(catalog_df)}')

    extra_headers = table_headers.difference(required_headers)
    for index, row in catalog_df.iterrows():
        LOGGER.debug(f'row {index}: {row}')
        attribute_dict = {}
        try:
            for header in extra_headers:
                if row[header] != '':
                    attribute_dict[header] = row[header]

            publish(
                row['gs_uri'], args.host_port, args.api_key, row['asset_id'],
                row['catalog'], 'GeoTIFF', row['description'], attribute_dict,
                row['expiration_utc_datetime'], force=args.force)
        except Exception:
            LOGGER.exception('publish failed')
            break
