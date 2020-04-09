"""Tracer code to send data to GeoServer app."""
import logging
import json
import urllib.parse
import time

import requests
import retrying


logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'),
    filename='quad_cache_log.txt')
LOGGER = logging.getLogger(__name__)


@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=5000)
def do_rest_action(session_fn, host, suburl, data=None):
    """Do a 'get' for the host/suburl."""
    try:
        return session_fn(urllib.parse.urljoin(host, suburl), data=None)
    except Exception:
        LOGGER.exception('error in function')
        raise


if __name__ == '__main__':
    result = requests.post(
        'http://localhost:8888/api/v1/add_raster',
        json=json.dumps({
            'name': 'test_raster',
            'uri_path': 'gs://shared-with-users/normalized_rasters/normalized_masked_realized_grazing_md5_19085729ae358e0e8566676c5c7aae72.tif'
        }))
    print(result.json())
    callback_url = result.json()['callback_url']
    while True:
        time.sleep(1)
        r = requests.get(callback_url)
        print(r.json())
