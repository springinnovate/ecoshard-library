"""Flask APP to manage the GeoServer."""
import argparse
import datetime
import hashlib
import json
import logging
import os
import pathlib
import pickle
import re
import secrets
import sqlite3
import subprocess
import urllib.parse
import time
import threading

from osgeo import gdal
from osgeo import osr
import flask
import ecoshard
import numpy
import pygeoprocessing
import requests
import retrying

APP = flask.Flask(__name__)
# relative to the geoserver 'data_dir'

INTER_DATA_DIR = 'data'
FULL_DATA_DIR = os.path.abspath(
    os.path.join('..', 'data_dir', INTER_DATA_DIR))
DATABASE_PATH = os.path.join(FULL_DATA_DIR, 'flask_manager.db')
GEOSERVER_PORT = '8080'
MANAGER_PORT = '8888'
PASSWORD_FILE_PATH = os.path.join(FULL_DATA_DIR, 'secrets', 'adminpass')
GEOSERVER_USER = 'admin'

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'))
LOGGER = logging.getLogger(__name__)


def utc_now():
    """Return string of current time in UTC."""
    return str(datetime.datetime.now(datetime.timezone.utc))


@APP.route('/api/v1/pixel_pick', methods=["POST"])
def pixel_pick():
    """Pick the value from a pixel.

    Args:
        body parameters:
            catalog (str): catalog to query
            asset_id (str): asset id to query
            lng (float): longitude coordinate
            lat (float): latitude coordinate

    Returns:
        {'val': val, 'x': x, 'y': y} if pixel in valid range otherwise
        {'val': 'out of range', 'x': x, 'y': y} if pixel in valid range
            otherwise

    """
    try:
        picker_data = flask.request.get_data()
        LOGGER.debug(str(picker_data))
        local_path_payload = _execute_sqlite(
            '''
            SELECT local_path
            FROM catalog_table
            WHERE asset_id=? AND catalog=?
            ''', DATABASE_PATH, argument_list=[
                picker_data["asset_id"], picker_data["catalog"]],
            execute='execute', fetch='one')
        r = gdal.OpenEx(local_path_payload[0], gdal.OF_RASTER)
        b = r.GetRasterBand(1)
        gt = r.GetGeoTransform()
        inv_gt = gdal.InvGeoTransform(gt)
        x_coord, y_coord = [
            int(p) for p in gdal.ApplyGeoTransform(
                inv_gt, picker_data['lng'], picker_data['lat'])]
        if (x_coord < 0 or y_coord < 0 or
                x_coord >= b.XSize or y_coord >= b.YSize):
            return {
                    'val': 'out of range',
                    'x': x_coord,
                    'y': y_coord
                }
        val = r.ReadAsArray(x_coord, y_coord, 1, 1)[0, 0]
        nodata = b.GetNoDataValue()
        if numpy.isclose(val, nodata):
            return {
                'val': 'nodata',
                'x': x_coord,
                'y': y_coord
            }
        else:
            return {
                'val': val,
                'x': x_coord,
                'y': y_coord
            }
    except Exception as e:
        LOGGER.exception('something bad happened')
        return str(e), 500


@APP.route('/api/v1/fetch', methods=["POST"])
def fetch():
    """Search the catalog using STAC format.

    The body parameters can be queried from

    Args:
        query parameter:
            api_key, used to filter query results, must have READ:* or
                READ:[catalog] access to get results from that catalog.
        body parameters include:
            catalog (str): catalog the asset is located in
            asset_id (str): asset it of the asset in the given catalog.
            type (str): can be one of "WMS"|"href" where
                "WMS_preview": gives a link for a public WMS preview layer that
                    can be scraped for the raw WMS url or inspected directly.
                "uri": gives a URI that is the direct link to the dataset,
                    this may be a gs:// or https:// or other url. The caller
                    will infer this from context.

    Responses:
        json:
            {
                type (str): "WMS" or "herf" depending on body type passed
                link (str): url for the specified type
            }

        400 if invalid api key or catalog:asset_id not found

    Returns:
        None.

    """
    fetch_data = json.loads(flask.request.json)
    api_key = flask.request.args['api_key']
    valid_check = validate_api(api_key, f'READ:{fetch_data["catalog"]}')
    if valid_check != 'valid':
        return valid_check

    fetch_payload = _execute_sqlite(
        '''
        SELECT uri, xmin, ymin, xmax, ymax
        FROM catalog_table
        WHERE asset_id=? AND catalog=?
        ''', DATABASE_PATH, argument_list=[
            fetch_data["asset_id"], fetch_data["catalog"]],
        execute='execute', fetch='one')

    if not fetch_payload:
        return (
            f'{fetch_data["asset_id"]}:{fetch_data["catalog"]} not found', 400)

    if fetch_data["type"] == 'uri':
        return {
            'type': fetch_data['type'],
            'link': fetch_payload[0],
           }

    if fetch_data['type'] == 'WMS_preview':
        return {
            'type': fetch_data['type'],
            'link': flask.url_for(
                'viewer', catalog=fetch_data['catalog'],
                asset_id=fetch_data['asset_id'], api_key=api_key,
                _external=True)
            }


@APP.route('/api/v1/viewer')
def viewer():
    """Render a viewer webpage."""
    catalog = flask.request.args['catalog']
    asset_id = flask.request.args['asset_id']
    # TODO: is the api key necessary? api_key = flask.request.args['api_key']

    external_ip = pickle.loads(
        _execute_sqlite(
            '''
            SELECT value
            FROM global_variables
            WHERE key='external_ip'
            ''', DATABASE_PATH, mode='read_only', execute='execute',
            argument_list=[], fetch='one')[0])

    fetch_payload = _execute_sqlite(
        '''
        SELECT xmin, ymin, xmax, ymax
        FROM catalog_table
        WHERE asset_id=? AND catalog=?
        ''', DATABASE_PATH, argument_list=[asset_id, catalog],
        execute='execute', fetch='one')

    if not fetch_payload:
        return (
            f'{asset_id}:{catalog} not found', 400)

    xmin = fetch_payload[0]
    ymin = fetch_payload[1]
    xmax = fetch_payload[2]
    ymax = fetch_payload[3]

    x_center = (xmax+xmin)/2
    y_center = (ymax+ymin)/2

    return flask.render_template('viewer.html', **{
        'layer': f'{catalog}:{asset_id}',
        'style_css_url': flask.url_for('static', filename='style.css'),
        'geoserver_url': (
            f"http://{external_ip}:8080/"
            f"geoserver/{catalog}/wms"),
        'x_center': x_center,
        'y_center': y_center}, _external=True)


@retrying.retry(
    wait_exponential_multiplier=100, wait_exponential_max=2000,
    stop_max_attempt_number=5)
def _execute_sqlite(
        sqlite_command, database_path, argument_list=None,
        mode='read_only', execute='execute', fetch=None):
    """Execute SQLite command and attempt retries on a failure.

    Args:
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


@retrying.retry(
    wait_exponential_multiplier=1000, wait_exponential_max=5000,
    stop_max_attempt_number=5)
def do_rest_action(
        session_fn, host, suburl, data=None, json=None):
    """A wrapper around HTML functions to make for easy retry.

    Args:
        sesson_fn (function): takes a url, optional data parameter, and
            optional json parameter.

    Returns:
        result of `session_fn` on arguments.

    """
    try:
        return session_fn(
            urllib.parse.urljoin(host, suburl), data=data, json=json)
    except Exception:
        LOGGER.exception('error in function')
        raise


def publish_to_geoserver(
        geoserver_raster_path, local_raster_path, catalog, raster_id,
        mediatype):
    """Publish the layer to the geoserver.

    Args:
        geoserver_raster_path (str): path to the local file w/r/t the
            geoserver's data dir (i.e. the data dir is the root)
        local_raster_path (str): path to the raster on the local filesystem.
        catalog (str): STAC catalog to publish to
        raster_id (str): unique raster id to publish to.
        medatype (str): STAC mediatype for this raster.

    Returns:
        None

    """
    with open(PASSWORD_FILE_PATH, 'r') as password_file:
        master_geoserver_password = password_file.read()
    session = requests.Session()
    session.auth = (GEOSERVER_USER, master_geoserver_password)

    # make workspace
    LOGGER.debug('create workspace if it does not exist')
    workspace_exists_result = do_rest_action(
        session.get,
        f'http://localhost:{GEOSERVER_PORT}',
        f'geoserver/rest/workspaces/{catalog}')
    if not workspace_exists_result:
        LOGGER.debug(f'{catalog} does not exist, creating it')
        create_workspace_result = do_rest_action(
            session.post,
            f'http://localhost:{GEOSERVER_PORT}',
            'geoserver/rest/workspaces',
            json={'workspace': {'name': catalog}})
        if not create_workspace_result:
            # must be an error
            raise RuntimeError(create_workspace_result.text)

    # check if coverstore exists, if so delete it
    cover_id = f'{raster_id}_cover'
    coverstore_exists_result = do_rest_action(
        session.get,
        f'http://localhost:{GEOSERVER_PORT}',
        f'geoserver/rest/workspaces/{catalog}/coveragestores/{cover_id}')

    LOGGER.debug(
        f'coverstore_exists_result: {str(coverstore_exists_result)}')

    if coverstore_exists_result:
        LOGGER.warning(f'{catalog}:{cover_id}, so deleting it')
        # coverstore exists, delete it
        delete_coverstore_result = do_rest_action(
            session.delete,
            f'http://localhost:{GEOSERVER_PORT}',
            f'geoserver/rest/workspaces/{catalog}/'
            f'coveragestores/{cover_id}/?purge=all&recurse=true')
        if not delete_coverstore_result:
            LOGGER.error(delete_coverstore_result.text)
            raise RuntimeError(delete_coverstore_result.text)

    # create coverstore
    LOGGER.debug('create coverstore on geoserver')
    coveragestore_payload = {
      "coverageStore": {
        "name": cover_id,
        "type": mediatype,
        "workspace": catalog,
        "enabled": True,
        # this one is relative to the data_dir
        "url": f'file:{geoserver_raster_path}'
      }
    }

    create_coverstore_result = do_rest_action(
        session.post,
        f'http://localhost:{GEOSERVER_PORT}',
        f'geoserver/rest/workspaces/{catalog}/coveragestores',
        json=coveragestore_payload)
    if not create_coverstore_result:
        LOGGER.error(create_coverstore_result.text)
        raise RuntimeError(create_coverstore_result.text)

    LOGGER.debug('get local raster info')
    raster_info = pygeoprocessing.get_raster_info(local_raster_path)
    raster = gdal.OpenEx(local_raster_path, gdal.OF_RASTER)
    band = raster.GetRasterBand(1)
    raster_min, raster_max, raster_mean, raster_stdev = \
        band.GetStatistics(0, 1)
    gt = raster_info['geotransform']

    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_info['projection'])
    lat_lng_bounding_box = get_lat_lng_bounding_box(local_raster_path)

    epsg_crs = ':'.join(
        [raster_srs.GetAttrValue('AUTHORITY', i) for i in [0, 1]])

    LOGGER.debug('construct the cover_payload')

    external_ip = pickle.loads(
        _execute_sqlite(
            '''
            SELECT value
            FROM global_variables
            WHERE key='external_ip'
            ''', DATABASE_PATH, mode='read_only', execute='execute',
            argument_list=[], fetch='one')[0])

    cover_payload = {
        "coverage":
            {
                "name": raster_id,
                "nativeName": raster_id,
                "namespace":
                    {
                        "name": catalog,
                        "href": (
                            f"http://{external_ip}:8080/geoserver/"
                            f"rest/namespaces/{catalog}.json")
                    },
                "title": raster_id,
                "description": "description here",
                "abstract": "abstract here",
                "keywords": {
                    "string": [raster_id, "WCS", "GeoTIFF"]
                    },
                "nativeCRS": raster_info['projection'],
                "srs": epsg_crs,
                "nativeBoundingBox": {
                    "minx": raster_info['bounding_box'][0],
                    "maxx": raster_info['bounding_box'][2],
                    "miny": raster_info['bounding_box'][1],
                    "maxy": raster_info['bounding_box'][3],
                    "crs": raster_info['projection'],
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
                        "$": f"{cover_id}_{raster_id}"
                        }
                    },
                "store": {
                    "@class": "coverageStore",
                    "name": f"{catalog}:{raster_id}",
                    "href": (
                        f"http://{external_ip}:{GEOSERVER_PORT}/"
                        "geoserver/rest",
                        f"/workspaces/{catalog}/coveragestores/"
                        f"{urllib.parse.quote(raster_id)}.json")
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
                        "range": {"min": raster_min, "max": raster_max},
                        "nullValues": {"double": [
                            raster_info['nodata'][0]]},
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
                "nativeCoverageName": raster_id
            }
        }

    LOGGER.debug('send cover request to GeoServer')
    create_cover_result = do_rest_action(
        session.post,
        f'http://{external_ip}:{GEOSERVER_PORT}',
        f'geoserver/rest/workspaces/{catalog}/'
        f'coveragestores/{urllib.parse.quote(cover_id)}/coverages/',
        json=cover_payload)
    if not create_cover_result:
        LOGGER.error(create_cover_result.text)
        raise RuntimeError(create_cover_result.text)


def get_lat_lng_bounding_box(raster_path):
    """Calculate WGS84 projected bounding box for the raster."""
    raster_info = pygeoprocessing.get_raster_info(raster_path)
    wgs84_srs = osr.SpatialReference()
    wgs84_srs.ImportFromEPSG(4326)
    lat_lng_bounding_box = pygeoprocessing.transform_bounding_box(
        raster_info['bounding_box'],
        raster_info['projection'], wgs84_srs.ExportToWkt())
    return lat_lng_bounding_box


def add_raster_worker(
        uri_path, mediatype, catalog, raster_id, asset_description, job_id):
    """This is used to copy and update a coverage set asynchronously.

    Args:
        uri_path (str): path to base gs:// bucket to copy from.
        mediatype (str): raster mediatype, only GeoTIFF supported
        catalog (str): catalog for asset
        raster_id (str): raster id for asset
        asset_description (str): asset description to record
        job_id (str): used to identify entry in job_table

    Returns:
        None.

    """
    try:
        # geoserver raster path is for it's local data dir
        geoserver_raster_path = os.path.join(
            INTER_DATA_DIR, catalog, f'{raster_id}.tif')
        # local data dir is for path to copy to from working directory
        catalog_data_dir = os.path.join(FULL_DATA_DIR, catalog)
        try:
            os.makedirs(catalog_data_dir)
        except OSError:
            pass

        local_raster_path = os.path.join(
            catalog_data_dir, os.path.basename(geoserver_raster_path))

        _execute_sqlite(
            '''
            UPDATE job_table
            SET job_status='copying local', last_accessed_utc=?
            WHERE job_id=?;
            ''', DATABASE_PATH, argument_list=[utc_now(), job_id],
            mode='modify', execute='execute')

        LOGGER.debug('copy %s to %s', uri_path, local_raster_path)
        subprocess.run([
            f'gsutil cp "{uri_path}" "{local_raster_path}"'],
            shell=True, check=True)
        if not os.path.exists(local_raster_path):
            raise RuntimeError(f"{local_raster_path} didn't copy")

        raster = gdal.OpenEx(local_raster_path, gdal.OF_RASTER)
        compression_alg = raster.GetMetadata(
            'IMAGE_STRUCTURE').get('COMPRESSION', None)
        if compression_alg in [None, 'ZSTD']:
            _execute_sqlite(
                '''
                UPDATE job_table
                SET job_status=?, last_accessed_utc=?
                WHERE job_id=?;
                ''', DATABASE_PATH, argument_list=[
                    f'(re)compressing image from {compression_alg}, this can '
                    'take some time',
                    utc_now(), job_id],
                mode='modify', execute='execute')
            compressed_tmp_file = os.path.join(
                os.path.dirname(catalog_data_dir),
                f'COMPRESSION_{job_id}')
            os.rename(local_raster_path, compressed_tmp_file)
            ecoshard.compress_raster(
                compressed_tmp_file, local_raster_path,
                compression_algorithm='LZW', compression_predictor=None)

        _execute_sqlite(
            '''
            UPDATE job_table
            SET job_status='building overviews (can take some time)',
                last_accessed_utc=?
            WHERE job_id=?;
            ''', DATABASE_PATH, argument_list=[
                utc_now(), job_id],
            mode='modify', execute='execute')

        ecoshard.build_overviews(
            local_raster_path, interpolation_method='average',
            overview_type='internal', rebuild_if_exists=False)

        _execute_sqlite(
            '''
            UPDATE job_table
            SET job_status='publishing to geoserver', last_accessed_utc=?
            WHERE job_id=?;
            ''', DATABASE_PATH, argument_list=[utc_now(), job_id],
            mode='modify', execute='execute')

        publish_to_geoserver(
            geoserver_raster_path, local_raster_path, catalog, raster_id,
            mediatype)

        LOGGER.debug('update job_table with complete')
        _execute_sqlite(
            '''
            UPDATE job_table
            SET
                job_status='complete', last_accessed_utc=?,
                active=0
            WHERE job_id=?;
            ''', DATABASE_PATH, argument_list=[utc_now(), job_id],
            mode='modify', execute='execute')

        LOGGER.debug('update catalog_table with complete')
        lat_lng_bounding_box = get_lat_lng_bounding_box(local_raster_path)
        _execute_sqlite(
            '''
            INSERT OR REPLACE INTO catalog_table (
                asset_id, catalog, xmin, ymin, xmax, ymax,
                utc_datetime, mediatype, description, uri)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            ''', DATABASE_PATH, argument_list=[
                raster_id, catalog,
                lat_lng_bounding_box[0],
                lat_lng_bounding_box[1],
                lat_lng_bounding_box[2],
                lat_lng_bounding_box[3],
                utc_now(), mediatype, asset_description, uri_path],
            mode='modify', execute='execute')
        LOGGER.debug(f'successful publish of {catalog}:{raster_id}')

    except Exception as e:
        LOGGER.exception('something bad happened when doing raster worker')
        _execute_sqlite(
            '''
            UPDATE job_table
            SET job_status=?, last_accessed_utc=?, active=?
            WHERE job_id=?;
            ''', DATABASE_PATH, argument_list=[
                f'ERROR: {str(e)}', time.time(), 0, job_id],
            mode='modify', execute='execute')


@APP.route('/api/v1/search', methods=["POST"])
def search():
    """Search the catalog using STAC format.

    Args:
        query parameter:
            api_key, used to filter query results, must have READ:* or
                READ:[catalog] access to get results from that catalog.
        body parameters include:
            bbox = [xmin, ymin, xmax, ymax]
            catalogs = ['list', 'of', 'catalogs']
            ids = ['list', 'of', 'asset', 'ids']
            datetime =
                "exact time" | "low_time/high_time" | "../high time" |
                "low time/.."

    Responses:
        json:
            {
                'features': [
                    {
                        # 'id' can be used to fetch
                        'id': {catalog}:{id},
                        # bbox is overlap with query bbox
                        'bbox': [xmin, ymin, xmax, ymax],
                        'description': 'asset description'
                    }
                ]
            }

        400 if invalid api key

    Returns:
        None.

    """
    api_key = flask.request.args['api_key']

    allowed_permissions = _execute_sqlite(
        '''
        SELECT permissions
        FROM api_keys
        WHERE api_key=?
        ''', DATABASE_PATH, argument_list=[api_key],
        mode='read_only', execute='execute', fetch='one')

    if not allowed_permissions:
        return 'invalid api key', 400

    where_query_list = []
    argument_list = []
    search_data = json.loads(flask.request.json)
    if search_data['bounding_box']:
        s_xmin, s_ymin, s_xmax, s_ymax = [
            float(val) for val in search_data['bounding_box'].split(',')]
        where_query_list.append('(xmax>? and ymax>? and xmin<? and ymin<?)')
        argument_list.extend([s_xmin, s_ymin, s_xmax, s_ymax])

    if search_data['datetime']:
        min_time, max_time = search_data.split('/')
        if min_time != '..':
            where_query_list.append('(utc_datetime>=?)')
            argument_list.append(min_time)
        if max_time != '..':
            where_query_list.append('(utc_datetime<=?)')
            argument_list.append(max_time)

    allowed_catalog_set = set([
        permission.split(':')[1]
        for permission in allowed_permissions[0].split(' ')
        if permission.startswith('READ:')])
    all_catalogs_allowed = '*' in allowed_catalog_set

    if search_data['catalog_list']:
        catalog_set = set(search_data['catalog_list'].split(','))
        if not all_catalogs_allowed:
            # if not allowed to read everything, restrict query
            catalog_set = catalog_set.union(allowed_catalog_set)
        where_query_list.append(
            f"""(catalog IN ({','.join([f"'{x}'" for x in catalog_set])}))""")
    elif not all_catalogs_allowed:
        where_query_list.append(
            f"""(catalog IN ({
                ','.join([f"'{x}'" for x in allowed_catalog_set])}))""")

    if search_data['asset_id']:
        where_query_list.append('(asset_id LIKE ?)')
        argument_list.append(f"%{search_data['asset_id']}%")

    if search_data['description']:
        where_query_list.append('(description LIKE ?)')
        argument_list.append(f"%{search_data['description']}%")

    base_query_string = (
        'SELECT asset_id, catalog, utc_datetime, description, '
        'xmin, ymin, xmax, ymax '
        'FROM catalog_table')

    if where_query_list:
        base_query_string += f" WHERE {' AND '.join(where_query_list)}"

    bounding_box_search = _execute_sqlite(
        base_query_string,
        DATABASE_PATH, argument_list=argument_list,
        mode='read_only', execute='execute', fetch='all')

    feature_list = []
    for (asset_id, catalog, utc_datetime, description,
            xmin, ymin, xmax, ymax) in bounding_box_search:
        feature_list.append(
            {
                'id': f'{catalog}:{asset_id}',
                'bbox': [xmin, ymin, xmax, ymax],
                'utc_datetime': utc_datetime,
                'description': description,
            })
    return {'features': feature_list}


@APP.route('/api/v1/get_status/<job_id>')
def get_status(job_id):
    """Return the status of the session."""
    LOGGER.debug('getting status for %s', job_id)

    status = _execute_sqlite(
        '''
        SELECT job_status
        FROM job_table
        WHERE job_id=?;
        ''', DATABASE_PATH, argument_list=[job_id],
        mode='read_only', execute='execute', fetch='one')
    if status:
        return {
            'job_id': job_id,
            'status': status[0],
            }
    else:
        all_status = _execute_sqlite(
            '''SELECT * FROM job_table''', DATABASE_PATH, argument_list=[],
            mode='read_only', execute='execute', fetch='all')
        LOGGER.debug('all status: %s', all_status)
        return f'no status for {job_id}', 500


def validate_api(api_key, permission):
    """Take raw flask args and ensure 'api_key' exists and is valid.

    Args:
        api_key (str): an api key
        permission (str): one of READ:{catalog}, WRITE:{catalog}.

    Returns:
        str: 'valid' if api key is valid.
        tuple: ([error message str], 401) if invalid.

    """
    # ensure that the permission is well formed and doesn't contain
    if not re.match(r"^(READ:|WRITE:)([a-z0-9]+|\*)$", permission):
        return f'invalid permission: "{permission}"', 401

    allowed_permissions = _execute_sqlite(
        '''
        SELECT permissions
        FROM api_keys
        WHERE api_key=?
        ''', DATABASE_PATH, argument_list=[api_key],
        mode='read_only', execute='execute', fetch='one')

    if not allowed_permissions:
        return 'invalid api key', 400

    LOGGER.debug(
        f'allowed permissions for {api_key}: {str(allowed_permissions)}')
    # either permission is directly in there or a wildcard is allowed
    if permission in allowed_permissions[0] or \
            f'{permission.split(":")[0]}:*' in allowed_permissions[0]:
        return 'valid'
    return 'api key does not not have permission', 401


def build_job_hash(asset_args):
    """Build a unique job hash given the asset arguments.

    Args:
        asset_args (dict): dictionary of asset arguments valid for this schema
            contains at least:
                'catalog' -- catalog name
                'asset_id' -- unique id for the asset
    Returns:
        a unique hex hash that can be used to identify this job.

    """
    data = json.loads(flask.request.json)
    job_id_hash = hashlib.sha256()
    job_id_hash.update(data['catalog'].encode('utf-8'))
    job_id_hash.update(data['asset_id'].encode('utf-8'))
    return job_id_hash.hexdigest()


@APP.route('/api/v1/publish', methods=['POST'])
def publish():
    """Adds a raster to the GeoServer from a local storage.

    Request parameters:
        query parameters:
            api_key (str): api key that has WRITE:catalog access.

        body parameters in json format:
            catalog (str): catalog to publish to.
            id (str): raster ID, must be unique to the catalog.
            mediatype (str): mediatype of the raster. Currently only 'GeoTIFF'
                is supported.
            uri (str): uri to the asset that is accessible by this server.
                Currently supports only `gs://`.
            description (str): description of the asset
            force (bool): (optional) if True, will overwrite existing
                catalog:id asset

    Returns:
        {'callback_uri': ...}, 200 if successful. The `callback_uri` can be
            queried for when the asset is published.
        401 if api key is not authorized for this service

    """
    try:
        api_key = flask.request.args['api_key']
        asset_args = json.loads(flask.request.json)
        LOGGER.debug(f"asset args: {str(asset_args)}")
        valid_check = validate_api(
            api_key, f"WRITE:{asset_args['catalog']}")
        if valid_check != 'valid':
            return valid_check
        LOGGER.debug(f"{api_key} has access to WRITE:{asset_args['catalog']}")

        if asset_args['mediatype'] != 'GeoTIFF':
            return 'invalid mediatype, only "GeoTIFF" supported', 400

        if not asset_args['catalog'] or not asset_args['asset_id']:
            return (
                f'invalid catalog:asset_id: '
                f'{asset_args["catalog"]}:{asset_args["asset_id"]}'), 400

        # see if catalog/id are already in db
        #   if not force(d), then return 403
        catalog_id_present = _execute_sqlite(
            '''
            SELECT count(*)
            FROM catalog_table
            WHERE catalog=? AND asset_id=?
            ''', DATABASE_PATH, argument_list=[
                asset_args['catalog'], asset_args['asset_id']],
            mode='read_only', execute='execute', fetch='one')

        if catalog_id_present and catalog_id_present[0] > 0:
            if 'force' not in asset_args or not asset_args['force']:
                return (
                    f'{asset_args["catalog"]}:{asset_args["asset_id"]} '
                    'already published, use force:True to overwrite.'), 400

        # build job
        job_id = build_job_hash(asset_args)
        callback_url = flask.url_for(
            'get_status', job_id=job_id, api_key=api_key, _external=True)
        callback_payload = json.dumps({'callback_url': callback_url})

        # see if job already running
        job_payload = _execute_sqlite(
            '''
            SELECT active
            FROM job_table
            WHERE job_id=?
            ''', DATABASE_PATH, argument_list=[job_id],
            mode='read_only', execute='execute', fetch='one')

        # if there's job and it's active...
        if job_payload and job_payload[0]:
            return (
                f'{asset_args["catalog"]}:{asset_args["asset_id"]} actively '
                f'processing from {callback_url}, wait '
                f'until finished before sending new uri', 400)

        # new job
        _execute_sqlite(
            '''
            INSERT OR REPLACE INTO job_table
                (job_id, uri, job_status, active, last_accessed_utc)
            VALUES (?, ?, 'scheduled', 1, ?);
            ''', DATABASE_PATH, argument_list=[
                job_id, asset_args['uri'],
                utc_now()],
            mode='modify', execute='execute')

        raster_worker_thread = threading.Thread(
            target=add_raster_worker,
            args=(asset_args['uri'], asset_args['mediatype'],
                  asset_args['catalog'], asset_args['asset_id'],
                  asset_args['description'], job_id))
        raster_worker_thread.start()
        return callback_payload
    except Exception:
        LOGGER.exception('something bad happened on publish')
        _execute_sqlite(
            '''
            INSERT OR REPLACE INTO job_table
                (job_id, job_status, active, last_accessed_utc)
            VALUES (?, 'crashed on schedule', 0, ?);
            ''', DATABASE_PATH, argument_list=[job_id, utc_now()],
            mode='modify', execute='execute')
        raise


def build_schema(database_path):
    """Build the database schema to `database_path`."""
    LOGGER.debug(f'build schema for {database_path}')
    if os.path.exists(database_path):
        raise ValueError('database already exists: ' + database_path)

    create_database_sql = (
        """
        CREATE TABLE job_table (
            -- a unique hash of the job based on the raster id
            job_id TEXT NOT NULL PRIMARY KEY,
            uri TEXT NOT NULL,
            job_status TEXT NOT NULL,
            active INT NOT NULL, -- 0 if complete, error no not
            last_accessed_utc TEXT NOT NULL
            );

        CREATE INDEX last_accessed_index ON job_table(last_accessed_utc);
        CREATE INDEX job_id_index ON job_table(job_id);

        -- we may search by partial `id` so set NOCASE so we can use the index
        CREATE TABLE catalog_table (
            asset_id TEXT NOT NULL COLLATE NOCASE,
            catalog TEXT NOT NULL,
            xmin REAL NOT NULL,
            xmax REAL NOT NULL,
            ymin REAL NOT NULL,
            ymax REAL NOT NULL,
            utc_datetime TEXT NOT NULL,
            mediatype TEXT NOT NULL,
            description TEXT NOT NULL,
            uri TEXT NOT NULL,
            local_path TEXT NOT NULL,
            min_val REAL NOT NULL,
            max_val REAL NOT NULL,
            PRIMARY KEY (asset_id, catalog)
            );
        CREATE INDEX asset_id_index ON catalog_table(asset_id);
        CREATE INDEX catalog_index ON catalog_table(catalog);
        CREATE INDEX xmin_index ON catalog_table(xmin);
        CREATE INDEX xmax_index ON catalog_table(xmax);
        CREATE INDEX ymin_index ON catalog_table(ymin);
        CREATE INDEX ymax_index ON catalog_table(ymax);
        CREATE INDEX utctime_index ON catalog_table(utc_datetime);
        CREATE INDEX mediatype_index ON catalog_table(mediatype);

        CREATE TABLE api_keys (
            api_key TEXT NOT NULL PRIMARY KEY,
            /* permissions is string of READ:catalog WRITE:catalog CREATE
               where READ/WRITE:catalog allow access to read and write the
               catalog and CREATE allows creation of a new catalog.
            */
            permissions TEXT NOT NULL
            );

        CREATE TABLE global_variables (
            key TEXT NOT NULL PRIMARY KEY,
            value BLOB)
        """)

    _execute_sqlite(
        create_database_sql, database_path, argument_list=[],
        mode='modify', execute='script')


def get_geoserver_layers():
    """Return list of [workspace]:[layername] registered in the geoserver."""
    with open(PASSWORD_FILE_PATH, 'r') as password_file:
        master_geoserver_password = password_file.read()

    session = requests.Session()
    session.auth = (GEOSERVER_USER, master_geoserver_password)
    layers_result = do_rest_action(
        session.get,
        f'http://localhost:{GEOSERVER_PORT}',
        'geoserver/rest/layers.json').json()
    LOGGER.debug(layers_result)
    layer_name_list = [
        layer['name'] for layer in layers_result['layers']['layer']]
    return layer_name_list


def get_database_layers():
    """Return a list of [workspace]:[layername] register in database."""
    catalog_sql_result = _execute_sqlite(
        '''
        SELECT catalog, asset_id
        FROM catalog_table
        ''', DATABASE_PATH, argument_list=[],
        mode='read_only', execute='execute', fetch='all')
    return [
        f'{catalog}:{asset_id}' for catalog, asset_id in catalog_sql_result]


def initalize_geoserver(database_path):
    """Ensure database exists, set security, and set server initial stores."""
    try:
        os.makedirs(os.path.dirname(database_path))
    except OSError:
        pass

    # check if database exists, if it does, everything is already initialized
    # including master passwords so we can quit
    if not os.path.exists(database_path):
        build_schema(database_path)
    else:
        LOGGER.info('geoserver previously initialized')
        return

    # make new random password if one does not exist
    try:
        os.makedirs(os.path.dirname(PASSWORD_FILE_PATH))
    except OSError:
        pass
    with open(PASSWORD_FILE_PATH, 'w') as password_file:
        # i can't get this to work now so just do this
        geoserver_password = secrets.token_urlsafe(16)
        password_file.write(geoserver_password)

    session = requests.Session()
    # 'geoserver' is the default geoserver password, we'll need to be
    # authenticated to do the push
    session.auth = (GEOSERVER_USER, 'geoserver')
    password_update_request = do_rest_action(
        session.put,
        f'http://localhost:{GEOSERVER_PORT}',
        'geoserver/rest/security/self/password',
        json={
            'newPassword': geoserver_password
        })
    if not password_update_request:
        raise RuntimeError(
            'could not reset admin password: ' +
            password_update_request.text)

    # there's a bug in GeoServer 2.17 that requires a reload of the
    # configuration before the new password is used
    password_update_request = do_rest_action(
        session.post,
        f'http://localhost:{GEOSERVER_PORT}',
        'geoserver/rest/reload')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start GeoServer REST API server.')
    parser.add_argument(
        '--external_ip', type=str, required=True,
        help='external ip of this host')
    parser.add_argument(
        '--debug_api_key', type=str, help='a debug api key with full access')

    args = parser.parse_args()
    LOGGER.debug('starting up!')
    initalize_geoserver(DATABASE_PATH)

    # set the external IP so we can return correct contexts
    _execute_sqlite(
        '''
        INSERT OR REPLACE INTO global_variables (key, value)
        VALUES (?, ?)
        ''', DATABASE_PATH, argument_list=[
            'external_ip',
            pickle.dumps(args.external_ip)],
        mode='modify', execute='execute')

    # add a default API key if needed
    if args.debug_api_key:
        _execute_sqlite(
            '''
            INSERT OR REPLACE INTO api_keys (api_key, permissions)
            VALUES (?, 'READ:* WRITE:*')
            ''', DATABASE_PATH, argument_list=[args.debug_api_key],
            mode='modify', execute='execute')

    # wait for API calls
    APP.config.update(SERVER_NAME=f'{args.external_ip}:{MANAGER_PORT}')
    APP.run(host='0.0.0.0', port=MANAGER_PORT)
