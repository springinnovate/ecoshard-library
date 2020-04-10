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
DATABASE_PATH = 'manager_status.db'
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
            "url": 'file:%s' % local_path
          }
        }

        result = do_rest_action(
            session.post,
            'http://localhost:8080',
            f'geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/coveragestores',
            data=coveragestore_payload)
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

        raster_info['projection']

        epsg_crs = ':'.join(
            [raster_srs.GetAttrValue('AUTHORITY', i) for i in [0, 1]])

        cover_payload = {
          "coverage": {
            "abstract": "TODO: ABSTRACT GOES HERE",
            "defaultInterpolationMethod": "nearest neighbor",
            "description": "TODO: DESCRIPTION GOES HERE",
            "dimensions": {
              "coverageDimension": [
                {
                  "description": "GridSampleDimension[min, max]",
                  "name": "GRAY_INDEX",
                  "range": {
                    "max": raster_min,
                    "min": raster_max
                  }
                }
              ]
            },
            "enabled": True,
            "grid": {
              "dimension": "2",
              "crs": epsg_crs,
              "range": {
                "high": "%d %d" % raster_info['raster_size'],
                "low": "0 0"
              },
              "transform": {
                "scaleX": gt[1],
                "scaleY": gt[5],
                "shearX": gt[2],
                "shearY": gt[4],
                "translateX": gt[0],
                "translateY": gt[3]
              }
            },
            "interpolationMethods": {
              "string": [
                "nearest neighbor",
                "bilinear",
                "bicubic"
              ]
            },
            "keywords": {
              "string": [
                "TODO: KEYWORDS", "GO", "HERE",
              ]
            },
            "latLonBoundingBox": {
              "crs": "EPSG:4326",
              "maxx": lat_lng_bounding_box[2],
              "maxy": lat_lng_bounding_box[3],
              "minx": lat_lng_bounding_box[0],
              "miny": lat_lng_bounding_box[1]
            },
            "name": cover_name,
            "namespace": {
              "href": f"http://localhost:8075/geoserver/restng/namespaces/{DEFAULT_WORKSPACE}.json",
              "name": DEFAULT_WORKSPACE
            },
            "nativeBoundingBox": {
              "crs": raster_info['projection'],
              "maxx": raster_info['bounding_box'][2],
              "maxy": raster_info['bounding_box'][3],
              "minx": raster_info['bounding_box'][0],
              "miny": raster_info['bounding_box'][1]
            },
            "nativeCRS": {
              "$": raster_info['projection'],
              "@class": (
                "projected" if raster_srs.IsProjected() else "unprojected")
            },
            "nativeFormat": "GeoTIFF",
            "nativeName": cover_name,
            "requestSRS": {
              "string": [
                epsg_crs
              ]
            },
            "responseSRS": {
              "string": [
                epsg_crs
              ]
            },
            "srs": epsg_crs,
            "store": {
              "@class": "coverageStore",
              "href": f"http://localhost:8075/geoserver/restng/workspaces/{DEFAULT_WORKSPACE}/coveragestores/{cover_name}.json",
              "name": f"{DEFAULT_WORKSPACE}:{cover_name}"
            },
            "supportedFormats": {
              "string": [
                "ARCGRID",
                "IMAGEMOSAIC",
                "GTOPO30",
                "GEOTIFF",
                "GIF",
                "PNG",
                "JPEG",
                "TIFF"
              ]
            },
            "title": "TODO: put title here"
          }
        }
        result = do_rest_action(
            session.post,
            'http://localhost:8080',
            f'geoserver/workspaces/{DEFAULT_WORKSPACE}/'
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
            'get_status', session_id=session_id, _external=True)

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
        """)

    _execute_sqlite(
        create_database_sql, database_path, argument_list=[],
        mode='modify', execute='script')


if __name__ == '__main__':
    LOGGER.debug('starting up!')
    build_schema(DATABASE_PATH)

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

    APP.config.update(SERVER_NAME='localhost:8888')
    APP.run(host='0.0.0.0', port=8888)
