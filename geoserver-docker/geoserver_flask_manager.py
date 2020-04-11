"""Flask APP to manage the GeoServer."""
import argparse
import json
import logging
import os
import pathlib
import sqlite3
import subprocess
import urllib.parse
import uuid
import time
import threading

from osgeo import gdal
from osgeo import osr
import flask
import pygeoprocessing
import requests
import retrying


APP = flask.Flask(__name__)
DEFAULT_WORKSPACE = 'salo'
DATABASE_PATH = 'manager.db'
DATA_DIR = '../data_dir/data'

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'))
LOGGER = logging.getLogger(__name__)


@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=5000)
def _execute_sqlite(
        sqlite_command, database_path, argument_list=None,
        mode='read_only', execute='execute', fetch=None):
    """Execute SQLite command and attempt retries on a failure.

    Parameters:
        sqlite_command (str): a well formatted SQLite command.
        database_path (str): path to the SQLite database to operate on.
        argument_list (list): `execute == 'execute` then this list is passed to
            the internal sqlite3 `execute` call.
        mode (str): must be either 'read_only' or 'modify'.
        execute (str): must be either 'execute', 'many', or 'script'.
        fetch (str): if not `None` can be either 'all' or 'one'.
            If not None the result of a fetch will be returned by this
            function.

    Returns:
        result of fetch if `fetch` is not None.

    """
    cursor = None
    connection = None
    try:
        if mode == 'read_only':
            ro_uri = r'%s?mode=ro' % pathlib.Path(
                os.path.abspath(database_path)).as_uri()
            LOGGER.debug(
                '%s exists: %s', ro_uri, os.path.exists(os.path.abspath(
                    database_path)))
            connection = sqlite3.connect(ro_uri, uri=True)
        elif mode == 'modify':
            connection = sqlite3.connect(database_path)
        else:
            raise ValueError('Unknown mode: %s' % mode)

        if execute == 'execute':
            cursor = connection.execute(sqlite_command, argument_list)
        elif execute == 'many':
            cursor = connection.executemany(sqlite_command, argument_list)
        elif execute == 'script':
            cursor = connection.executescript(sqlite_command)
        else:
            raise ValueError('Unknown execute mode: %s' % execute)

        result = None
        payload = None
        if fetch == 'all':
            payload = (cursor.fetchall())
        elif fetch == 'one':
            payload = (cursor.fetchone())
        elif fetch is not None:
            raise ValueError('Unknown fetch mode: %s' % fetch)
        if payload is not None:
            result = list(payload)
        cursor.close()
        connection.commit()
        connection.close()
        return result
    except Exception:
        LOGGER.exception('Exception on _execute_sqlite: %s', sqlite_command)
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.commit()
            connection.close()
        raise


@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=5000)
def do_rest_action(
        session_fn, host, suburl, data=None, json=None):
    """Do a 'get' for the host/suburl."""
    try:
        return session_fn(
            urllib.parse.urljoin(host, suburl), data=data, json=json)
    except Exception:
        LOGGER.exception('error in function')
        raise


def add_raster_worker(session_id, cover_name, uri_path):
    """This is used to copy and update a coverage set asynchronously."""
    try:
        local_path = os.path.join(DATA_DIR, os.path.basename(uri_path))

        _execute_sqlite(
            '''
            UPDATE work_status_table
            SET work_status='copying local', last_accessed=?
            WHERE session_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), session_id],
            mode='modify', execute='execute')

        LOGGER.debug('about to copy %s to %s', uri_path, local_path)
        subprocess.run(
            [f'gsutil cp "{uri_path}" "{local_path}"'], shell=True, check=True)
        if not os.path.exists(local_path):
            raise RuntimeError(f"{local_path} didn't copy")
        _execute_sqlite(
            '''
            UPDATE work_status_table
            SET work_status='making coverstore', last_accessed=?
            WHERE session_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), session_id],
            mode='modify', execute='execute')

        session = requests.Session()
        session.auth = ('admin', 'geoserver')
        coveragestore_payload = {
          "coverageStore": {
            "name": cover_name,
            "type": 'GeoTIFF',
            "workspace": DEFAULT_WORKSPACE,
            "enabled": True,
            "url": 'file:%s' % local_path
          }
        }

        result = do_rest_action(
            session.post,
            'http://localhost:8080',
            f'geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/coveragestores',
            json=coveragestore_payload)
        LOGGER.debug(result.text)

        _execute_sqlite(
            '''
            UPDATE work_status_table
            SET work_status='making cover', last_accessed=?
            WHERE session_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), session_id],
            mode='modify', execute='execute')

        raster_info = pygeoprocessing.get_raster_info(local_path)
        raster = gdal.OpenEx(local_path, gdal.OF_RASTER)
        band = raster.GetRasterBand(1)
        raster_min, raster_max, raster_mean, raster_stdev = \
            band.GetStatistics(0, 1)
        gt = raster_info['geotransform']

        raster_srs = osr.SpatialReference()
        raster_srs.ImportFromWkt(raster_info['projection'])

        wgs84_srs = osr.SpatialReference()
        wgs84_srs.ImportFromEPSG(4326)
        lat_lng_bounding_box = pygeoprocessing.transform_bounding_box(
            raster_info['bounding_box'],
            raster_info['projection'], wgs84_srs.ExportToWkt())

        epsg_crs = ':'.join(
            [raster_srs.GetAttrValue('AUTHORITY', i) for i in [0, 1]])

        raster_basename = os.path.splitext(local_path)[0]

        cover_payload = {
            "coverage":
                {
                    "name": "Copy of Mann-BurnProb-2001-2025-BAU",
                    "nativeName": "Copy of Mann-BurnProb-2001-2025-BAU",
                    "namespace":
                        {
                            "name": DEFAULT_WORKSPACE,
                            "href": f"http:localhost:8080/geoserver/rest/namespaces/{DEFAULT_WORKSPACE}.json"
                        },
                    "title": raster_basename,
                    "description": "description here",
                    "abstract": "abstract here",
                    "keywords": {
                        "string": ["Copy of Mann-BurnProb-2001-2025-BAU", "WCS", "GeoTIFF"]
                        },
                    "nativeCRS": {
                        "@class": "projected" if raster_srs.IsProjected() else "unprojected",
                        "$": raster_info['projection']
                        },
                    "srs": epsg_crs,
                    "nativeBoundingBox": {
                        "minx": raster_info['bounding_box'][0],
                        "maxx": raster_info['bounding_box'][2],
                        "miny": raster_info['bounding_box'][1],
                        "maxy": raster_info['bounding_box'][3],
                        "crs": {
                            "@class": "projected" if raster_srs.IsProjected() else "unprojected",
                            "$": raster_info['projection']
                            },
                        },
                    "latLonBoundingBox": {
                        "minx": lat_lng_bounding_box[0],
                        "maxx": lat_lng_bounding_box[2],
                        "miny": lat_lng_bounding_box[1],
                        "maxy": lat_lng_bounding_box[3],
                        "crs": "EPSG:4326"
                        },
                    "projectionPolicy": "NONE",
                    "enabled": True,
                    "metadata": {
                        "entry": {
                            "@key": "dirName",
                            "$": f"{cover_name}_{raster_basename}"
                            }
                        },
                    "store": {
                        "@class": "coverageStore",
                        "name": f"{DEFAULT_WORKSPACE}:{cover_name}",
                        "href": f"http://localhost:8080/geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/coveragestores/{cover_name}.json"
                        },
                    "serviceConfiguration": False,
                    "nativeFormat": "GeoTIFF",
                    "grid": {
                        "@dimension": "2",
                        "range": {
                            "low": "0 0",
                            "high": f"{raster_info['raster_size'][0]} {raster_info['raster_size'][1]}"
                            },
                        "transform": {
                            "scaleX": gt[1],
                            "scaleY": gt[5],
                            "shearX": gt[2],
                            "shearY": gt[4],
                            "translateX": gt[0],
                            "translateY": gt[3]
                            },
                        "crs": raster_info['projection']
                        },
                    "supportedFormats": {
                        "string": ["GEOTIFF", "ImageMosaic", "ArcGrid", "GIF", "PNG", "JPEG", "TIFF", "GeoPackage (mosaic)"]
                        },
                    "interpolationMethods": {
                        "string": ["nearest neighbor", "bilinear", "bicubic"]
                        },
                    "defaultInterpolationMethod": "nearest neighbor",
                    "dimensions": {
                        "coverageDimension": [{
                            "name": "GRAY_INDEX",
                            "description": "GridSampleDimension[-Infinity,Infinity]",
                            "range": {"min": 0, "max": 0.22},
                            "nullValues": {"double": [-9999]},
                            "dimensionType":{"name": "REAL_32BITS"}
                            }]
                        },
                    "parameters": {
                        "entry": [
                            {"string": "InputTransparentColor", "null": ""},
                            {"string": ["SUGGESTED_TILE_SIZE", "512,512"]},
                            {
                                "string": "RescalePixels",
                                "boolean": True
                            }]
                        },
                    "nativeCoverageName": "Copy of Mann-BurnProb-2001-2025-BAU"
                }
            }

        result = do_rest_action(
            session.post,
            'http://localhost:8080',
            f'geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/'
            f'coveragestores/{cover_name}/coverages', json=cover_payload)
        LOGGER.debug(result.text)
        _execute_sqlite(
            '''
            UPDATE work_status_table
            SET work_status='complete', last_accessed=?
            WHERE session_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), session_id],
            mode='modify', execute='execute')
    except Exception as e:
        _execute_sqlite(
            '''
            UPDATE work_status_table
            SET work_status=?, last_accessed=?
            WHERE session_id=?;
            ''', DATABASE_PATH, argument_list=[
                str(e), time.time(), session_id],
            mode='modify', execute='execute')


@APP.route('/api/v1/get_status/<session_id>')
def get_status(session_id):
    """Return the status of the session."""
    result = validate_api(flask.request.args)
    if result != 'valid':
        return result

    status = _execute_sqlite(
        '''
        SELECT work_status
        FROM work_status_table
        WHERE session_id=?;
        ''', DATABASE_PATH, argument_list=[session_id],
        mode='read_only', execute='execute', fetch='one')
    return {
        'session_id': session_id,
        'status': status[0]
        }


def validate_api(args):
    if 'api_key' not in flask.request.args:
        return 'api key required', 401
    result = _execute_sqlite(
        '''
        SELECT count(*)
        FROM api_keys
        WHERE key=?
        ''', DATABASE_PATH, argument_list=[flask.request.args['api_key']],
        mode='read_only', execute='execute', fetch='one')
    if result[0] != 1:
        return 'api key not found: %d' % result[0], 401
    return 'valid'


@APP.route('/api/v1/add_raster', methods=['POST'])
def add_raster():
    """Adds a raster to the GeoServer from a local storage.

    Request parameters:
        name (str) -- name of raster
        uri_path (str) -- uri to copy locally in the form:
            file:[/path/to/file.tif]

    Returns:
        200 if successful

    """
    result = validate_api(flask.request.args)
    if result != 'valid':
        return result

    data = json.loads(flask.request.json)
    LOGGER.debug(data)
    session_id = uuid.uuid4().hex

    LOGGER.debug('new session entry')
    _execute_sqlite(
        '''
        INSERT INTO work_status_table (session_id, work_status, last_accessed)
        VALUES (?, 'scheduled', ?);
        ''', DATABASE_PATH, argument_list=[session_id, time.time()],
        mode='modify', execute='execute')

    with APP.app_context():
        LOGGER.debug('about to get url')
        callback_url = flask.url_for(
            'get_status', session_id=session_id,
            api_key=flask.request.args['api_key'], _external=True)

    LOGGER.debug(callback_url)
    raster_worker_thread = threading.Thread(
        target=add_raster_worker, args=(
            session_id, data['name'], data['uri_path']))
    raster_worker_thread.start()

    LOGGER.debug('raster worker started returning now')
    return json.dumps({'callback_url': callback_url})


def build_schema(database_path):
    """Build the database schema."""
    if os.path.exists(database_path):
        os.remove(database_path)

    create_database_sql = (
        """
        CREATE TABLE work_status_table (
            session_id TEXT NOT NULL PRIMARY KEY,
            work_status TEXT NOT NULL,
            last_accessed REAL NOT NULL
            );

        CREATE TABLE api_keys (
            key TEXT NOT NULL PRIMARY KEY
            );
        """)

    _execute_sqlite(
        create_database_sql, database_path, argument_list=[],
        mode='modify', execute='script')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create or delete an API key.')
    parser.add_argument(
        'api_key', action='store_true', help='default api key')
    args = parser.parse_args()
    LOGGER.debug('starting up!')
    build_schema(DATABASE_PATH)
    _execute_sqlite(
        '''
        INSERT INTO api_keys (key)
        VALUES (?)
        ''', DATABASE_PATH, argument_list=[args.api_key], mode='modify',
        execute='execute')

    # First delete all the defaults off the geoserver
    session = requests.Session()
    session.auth = ('admin', 'geoserver')
    r = do_rest_action(
        session.get, 'http://localhost:8080', 'geoserver/rest/workspaces.json')
    result = r.json()

    if 'workspace' in result['workspaces']:
        for workspace in result['workspaces']['workspace']:
            workspace_name = workspace['name']
            r = do_rest_action(
                session.delete, 'http://localhost:8080',
                'geoserver/rest/workspaces/%s.json?recurse=true' %
                workspace_name)
            LOGGER.debug("delete result for %s: %s", workspace_name, str(r))

    # Create empty workspace
    result = do_rest_action(
        session.post, 'http://localhost:8080',
        'geoserver/rest/workspaces?default=true',
        json={'workspace': {'name': DEFAULT_WORKSPACE}})
    LOGGER.debug(result.text)

    # wait for API calls
    APP.config.update(SERVER_NAME='localhost:8888')
    APP.run(host='0.0.0.0', port=8888)
