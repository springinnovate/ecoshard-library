"""Flask APP to manage the GeoServer."""
import argparse
import json
import logging
import os
import pathlib
import pickle
import sqlite3
import subprocess
import urllib.parse
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
GEOSERVER_PORT = '8080'
MANAGER_PORT = '8888'
logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'))
LOGGER = logging.getLogger(__name__)


#@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=5000)
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


#@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=5000)
def do_rest_action(
        session_fn, host, suburl, data=None, json=None):
    """Do a 'get' for the host/suburl."""
    try:
        return session_fn(
            urllib.parse.urljoin(host, suburl), data=data, json=json)
    except Exception:
        LOGGER.exception('error in function')
        raise


def add_raster_worker(uri_path):
    """This is used to copy and update a coverage set asynchronously."""
    try:
        local_path = os.path.join(DATA_DIR, os.path.basename(uri_path))
        raster_id = os.path.splitext(os.path.basename(uri_path))[0]
        cover_id = f'{raster_id}_cover'
        _execute_sqlite(
            '''
            UPDATE status_table
            SET work_status='copying local', last_accessed=?
            WHERE raster_id=?;
            ''', DATABASE_PATH, argument_list=[
                time.time(), raster_id],
            mode='modify', execute='execute')

        LOGGER.debug(' to copy %s to %s', uri_path, local_path)
        subprocess.run(
            [f'gsutil cp "{uri_path}" "{local_path}"'], shell=True, check=True)
        if not os.path.exists(local_path):
            raise RuntimeError(f"{local_path} didn't copy")
        _execute_sqlite(
            '''
            UPDATE status_table
            SET work_status='making coverstore', last_accessed=?
            WHERE raster_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), raster_id],
            mode='modify', execute='execute')

        LOGGER.debug('create coverstore on geoserver')
        session = requests.Session()
        session.auth = ('admin', 'geoserver')
        coveragestore_payload = {
          "coverageStore": {
            "name": cover_id,
            "type": 'GeoTIFF',
            "workspace": DEFAULT_WORKSPACE,
            "enabled": True,
            "url": 'file:%s' % local_path
          }
        }

        result = do_rest_action(
            session.post,
            f'http://localhost:{GEOSERVER_PORT}',
            f'geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/coveragestores',
            json=coveragestore_payload)
        LOGGER.debug(result.text)

        LOGGER.debug('update database with coverstore status')
        _execute_sqlite(
            '''
            UPDATE status_table
            SET work_status='making cover', last_accessed=?
            WHERE raster_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), raster_id],
            mode='modify', execute='execute')

        LOGGER.debug('get local raster info')
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

        LOGGER.debug('construct the cover_payload')
        cover_payload = {
            "coverage":
                {
                    "name": raster_basename,
                    "nativeName": raster_basename,
                    "namespace":
                        {
                            "name": DEFAULT_WORKSPACE,
                            "href": (
                                f"http:localhost:{GEOSERVER_PORT}/geoserver/"
                                f"rest/namespaces/{DEFAULT_WORKSPACE}.json")
                        },
                    "title": raster_basename,
                    "description": "description here",
                    "abstract": "abstract here",
                    "keywords": {
                        "string": [raster_basename, "WCS", "GeoTIFF"]
                        },
                    "nativeCRS": {
                        "@class": (
                            "projected" if raster_srs.IsProjected() else
                            "unprojected"),
                        "$": raster_info['projection']
                        },
                    "srs": epsg_crs,
                    "nativeBoundingBox": {
                        "minx": raster_info['bounding_box'][0],
                        "maxx": raster_info['bounding_box'][2],
                        "miny": raster_info['bounding_box'][1],
                        "maxy": raster_info['bounding_box'][3],
                        "crs": {
                            "@class": (
                                "projected" if raster_srs.IsProjected() else
                                "unprojected"),
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
                            "$": f"{cover_id}_{raster_basename}"
                            }
                        },
                    "store": {
                        "@class": "coverageStore",
                        "name": f"{DEFAULT_WORKSPACE}:{cover_id}",
                        "href": (
                            f"http://localhost:{GEOSERVER_PORT}/geoserver/rest"
                            f"/workspaces/{DEFAULT_WORKSPACE}/coveragestores/"
                            "{cover_id}.json")
                        },
                    "serviceConfiguration": False,
                    "nativeFormat": "GeoTIFF",
                    "grid": {
                        "@dimension": "2",
                        "range": {
                            "low": "0 0",
                            "high": (
                                f"{raster_info['raster_size'][0]} "
                                f"{raster_info['raster_size'][1]}")
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
                        "string": [
                            "GEOTIFF", "ImageMosaic", "ArcGrid", "GIF", "PNG",
                            "JPEG", "TIFF", "GeoPackage (mosaic)"]
                        },
                    "interpolationMethods": {
                        "string": ["nearest neighbor", "bilinear", "bicubic"]
                        },
                    "defaultInterpolationMethod": "nearest neighbor",
                    "dimensions": {
                        "coverageDimension": [{
                            "name": "GRAY_INDEX",
                            "description": (
                                "GridSampleDimension[-Infinity,Infinity]"),
                            # TODO: set these to real values
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
                    "nativeCoverageName": raster_basename
                }
            }

        LOGGER.debug('send cover request to GeoServer')
        result = do_rest_action(
            session.post,
            f'http://localhost:{GEOSERVER_PORT}',
            f'geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/'
            f'coveragestores/{cover_id}/coverages', json=cover_payload)
        LOGGER.debug(result.text)

        LOGGER.debug('construct the preview url')
        external_ip = pickle.loads(
            _execute_sqlite(
                '''
                SELECT value
                FROM global_variables
                WHERE key='external_ip'
                ''', DATABASE_PATH, mode='read_only', execute='execute',
                argument_list=[], fetch='one')[0])

        preview_url = (
            f"http://{external_ip}:{GEOSERVER_PORT}/geoserver/"
            f"{DEFAULT_WORKSPACE}/"
            f"wms?service=WMS&version=1.3.0&request=GetMap&layers="
            f"{urllib.parse.quote_plus(raster_basename)}/&bbox="
            f"{'%2C'.join([str(v) for v in raster_info['bounding_box']])}"
            f"&width=1000&height=768&srs=EPSG%3A{epsg_crs}"
            f"&format=application%2Fopenlayers3#toggle")

        LOGGER.debug('update database with complete and cover url')
        _execute_sqlite(
            '''
            UPDATE status_table
            SET work_status='complete', preview_url=?, last_accessed=?
            WHERE raster_id=?;
            ''', DATABASE_PATH, argument_list=[
                preview_url, time.time(), raster_id],
            mode='modify', execute='execute')

    except Exception as e:
        LOGGER.exception('something bad happened when doing raster worker')
        _execute_sqlite(
            '''
            UPDATE status_table
            SET work_status=?, last_accessed=?
            WHERE raster_id=?;
            ''', DATABASE_PATH, argument_list=[
                f'ERROR: {str(e)}', time.time(), raster_id],
            mode='modify', execute='execute')


@APP.route('/api/v1/get_status/<url_raster_id>')
def get_status(url_raster_id):
    """Return the status of the session."""
    valid_check = validate_api(flask.request.args)
    if valid_check != 'valid':
        return valid_check

    raster_id = urllib.parse.unquote_plus(url_raster_id)
    LOGGER.debug('getting status for %s', raster_id)

    status = _execute_sqlite(
        '''
        SELECT work_status, preview_url
        FROM status_table
        WHERE raster_id=?;
        ''', DATABASE_PATH, argument_list=[raster_id],
        mode='read_only', execute='execute', fetch='one')
    if status:
        return {
            'raster_id': raster_id,
            'status': status[0],
            'preview_url': status[1]
            }
    else:
        all_status = _execute_sqlite(
            '''SELECT * FROM status_table''', DATABASE_PATH, argument_list=[],
            mode='read_only', execute='execute', fetch='all')
        LOGGER.debug('all status: %s', all_status)
        return f'no status for {raster_id}', 500


def validate_api(args):
    LOGGER.debug('validating args: %s', str(args))
    if 'api_key' not in flask.request.args:
        return 'api key required', 401
    result = _execute_sqlite(
        '''
        SELECT count(*)
        FROM api_keys
        WHERE key=?
        ''', DATABASE_PATH, argument_list=[flask.request.args['api_key']],
        mode='read_only', execute='execute', fetch='one')
    LOGGER.debug('query result: %s', str(result))
    if result[0] != 1:
        return 'api key not found: %d' % result[0], 401
    return 'valid'


@APP.route('/api/v1/add_raster', methods=['POST'])
def add_raster():
    """Adds a raster to the GeoServer from a local storage.

    Request parameters:
        uri_path (str) -- uri to copy locally in the form:
            file:[/path/to/file.tif]

    Returns:
        200 if successful

    """
    LOGGER.debug('checking key')
    valid_check = validate_api(flask.request.args)
    if valid_check != 'valid':
        return valid_check
    LOGGER.debug('key valid')

    data = json.loads(flask.request.json)
    raster_id = os.path.splitext(os.path.basename(data['uri_path']))[0]
    LOGGER.debug(data)

    with APP.app_context():
        LOGGER.debug('about to get url')
        callback_url = flask.url_for(
            'get_status', url_raster_id=raster_id,
            api_key=flask.request.args['api_key'], _external=True)

    LOGGER.debug('callback_url: %s', callback_url)
    # make sure it's not already processed/is processing
    exists = _execute_sqlite(
        '''
        SELECT EXISTS(SELECT 1 FROM status_table WHERE raster_id=?)
        ''', DATABASE_PATH,
        mode='read_only', execute='execute', argument_list=[raster_id],
        fetch='one')[0]

    if not exists:
        LOGGER.debug('new session entry')
        _execute_sqlite(
            '''
            INSERT INTO status_table (raster_id, work_status, last_accessed)
            VALUES (?, 'scheduled', ?);
            ''', DATABASE_PATH, argument_list=[raster_id, time.time()],
            mode='modify', execute='execute')
        LOGGER.debug('start worker')
        raster_worker_thread = threading.Thread(
            target=add_raster_worker, args=(data['uri_path'],))
        raster_worker_thread.start()

    LOGGER.debug('raster worker started returning now')
    return json.dumps({'callback_url': callback_url})


def build_schema(database_path):
    """Build the database schema."""
    if os.path.exists(database_path):
        os.remove(database_path)

    create_database_sql = (
        """
        CREATE TABLE status_table (
            raster_id TEXT NOT NULL PRIMARY KEY,
            work_status TEXT NOT NULL,
            preview_url TEXT,
            last_accessed REAL NOT NULL
            );

        CREATE TABLE api_keys (
            key TEXT NOT NULL PRIMARY KEY
            );

        CREATE TABLE global_variables (
            key TEXT NOT NULL PRIMARY KEY,
            value BLOB)
        """)

    _execute_sqlite(
        create_database_sql, database_path, argument_list=[],
        mode='modify', execute='script')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create or delete an API key.')
    parser.add_argument('api_key', type=str, help='default api key')
    parser.add_argument(
        'external_ip', type=str,
        help='external ip of this host')
    args = parser.parse_args()
    LOGGER.debug('starting up!')
    build_schema(DATABASE_PATH)
    _execute_sqlite(
        '''
        INSERT INTO global_variables (key, value)
        VALUES (?, ?)
        ''', DATABASE_PATH, argument_list=[
            'external_ip',
            pickle.dumps(args.external_ip)],
        mode='modify', execute='execute')

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
        session.get,
        f'http://localhost:{GEOSERVER_PORT}',
        'geoserver/rest/workspaces.json')
    result = r.json()

    if 'workspace' in result['workspaces']:
        for workspace in result['workspaces']['workspace']:
            workspace_name = workspace['name']
            r = do_rest_action(
                session.delete,
                f'http://localhost:{GEOSERVER_PORT}',
                'geoserver/rest/workspaces/%s.json?recurse=true' %
                workspace_name)
            LOGGER.debug("delete result for %s: %s", workspace_name, str(r))

    # Create empty workspace
    result = do_rest_action(
        session.post,
        f'http://localhost:{GEOSERVER_PORT}',
        'geoserver/rest/workspaces?default=true',
        json={'workspace': {'name': DEFAULT_WORKSPACE}})
    LOGGER.debug(result.text)

    # wait for API calls
    APP.config.update(SERVER_NAME=f'{args.external_ip}:{MANAGER_PORT}')
    APP.run(host='0.0.0.0', port=MANAGER_PORT)
