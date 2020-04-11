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
        params={'api_key': 'test_key'},
        json=json.dumps({
            'uri_path': 'gs://salo-api/test_rasters/Copy of Mann-BurnProb-2001-2025-BAU.tif'
        }))
    print(result.text)
    print(result.json())
    callback_url = result.json()['callback_url']
    print(callback_url)
    while True:
        time.sleep(1)
        r = requests.get(callback_url)
        print(r.text)
        payload = r.json()
        print(payload)
        if payload['status'] == 'complete':
            break
    print(payload['preview_url'])
