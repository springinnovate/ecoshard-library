"""Flask APP to manage the GeoServer."""
import datetime
import hashlib
import json
import logging
import math
import os
import re
import subprocess
import threading
import time
import traceback
import urllib.parse

from flask import Blueprint
from flask import current_app
from google.oauth2 import service_account
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from urllib.parse import quote
import binascii
import collections
import ecoshard
import flask
import numpy
import pygeoprocessing
import requests
import retrying

# SQLAlchamy
from ..db import db
from . import models
from . import queries
from . import services

EXPIRATION_MONITOR_DELAY = 300  # check for expiration every 300s
DOWNLOAD_HEADERS = {"Content-Disposition": "attachment"}

LOGGER = logging.getLogger("stac")

stac_bp = Blueprint(
    "stac", __name__, template_folder='templates', static_folder='static')


@stac_bp.route('/pixel_pick', methods=["POST"])
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
        picker_data = json.loads(flask.request.get_data())
        LOGGER.debug(str(picker_data))
        catalog_entry = queries.find_catalog_by_id(
            picker_data["catalog"], picker_data["asset_id"])
        r = gdal.OpenEx(catalog_entry.local_path, gdal.OF_RASTER)
        b = r.GetRasterBand(1)
        gt = r.GetGeoTransform()
        inv_gt = gdal.InvGeoTransform(gt)

        # transform lat/lng to raster coordinate space
        wgs84_srs = osr.SpatialReference()
        wgs84_srs.ImportFromEPSG(4326)
        raster_srs = osr.SpatialReference()
        raster_srs.ImportFromWkt(r.GetProjection())
        # put in x/y order
        raster_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        wgs84_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        # Create a coordinate transformation
        wgs84_to_raster_trans = osr.CoordinateTransformation(
            wgs84_srs, raster_srs)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(picker_data['lng'], picker_data['lat'])
        error_code = point.Transform(wgs84_to_raster_trans)
        if error_code != 0:  # error
            return "error on transform", 500

        # convert to raster space
        x_coord, y_coord = [
            int(p) for p in gdal.ApplyGeoTransform(
                inv_gt, point.GetX(), point.GetY())]
        if (x_coord < 0 or y_coord < 0 or
                x_coord >= b.XSize or y_coord >= b.YSize):
            response_dict = {
                'val': 'out of range',
                'x': x_coord,
                'y': y_coord
            }

        # must cast the right type for json
        val = r.ReadAsArray(x_coord, y_coord, 1, 1)[0, 0]
        if numpy.issubdtype(val, numpy.integer):
            val = int(val)
        else:
            val = float(val)
        nodata = b.GetNoDataValue()
        if numpy.isclose(val, nodata):
            response_dict = {
                'val': 'nodata',
                'x': x_coord,
                'y': y_coord
            }
        else:
            response_dict = {
                'val': val,
                'x': x_coord,
                'y': y_coord
            }

        response = flask.jsonify(response_dict)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        LOGGER.exception('something bad happened')
        return str(e), 500


@stac_bp.route('/fetch', methods=["POST"])
def fetch():
    """Search the catalog using STAC format.

    Fetch a link from the catalog

    Args:
        query parameter:
            api_key, used to filter query results, must have READ:* or
                READ:[catalog] access to get results from that catalog.
        body parameters include:
            catalog (str): catalog the asset is located in
            asset_id (str): asset it of the asset in the given catalog.
            type (str): can be one of "wms"|"uri"|"preview" where
                "preview": gives a link for a public WMS preview layer.
                "uri": gives a URI that is the direct link to the dataset,
                    this may be a gs:// or https:// or other url. The
                    caller will infer this from context.
                "url": returns a url to download the requested file.
                "wms": just the WMS link.

    Responses:
        json:
            {
                type (str): "WMS" or "uri" depending on body type passed
                link (str): url for the specified type
                raster_min (float): min stats
                raster_max (float): max stats
                raster_mean (float): mean stats
                raster_stdev (float):  stdev stats
            }

        400 if invalid api key or catalog:asset_id not found

    Returns:
        None.

    """
    if not isinstance(flask.request.json, dict):
        fetch_data = json.loads(flask.request.json)
    else:
        fetch_data = flask.request.json
    api_key = flask.request.args['api_key']
    valid_check = validate_api(api_key, f'READ:{fetch_data["catalog"]}')
    if valid_check != 'valid':
        return valid_check
    fetch_catalog = queries.find_catalog_by_id(
        fetch_data['catalog'], fetch_data['asset_id'])

    if not fetch_catalog:
        return (
            f'{fetch_data["asset_id"]}:{fetch_data["catalog"]} not found',
            400)
    LOGGER.debug(fetch_catalog)

    fetch_type = fetch_data['type'].lower()
    if fetch_type == 'uri':
        link = fetch_catalog.uri
    elif fetch_data['type'] == 'url':
        # google storage links of the form gs://[VALUE] have https
        # equivalents of https://storage.cloud.google.com/[VALUE]
        link = os.path.join(
            'https://storage.cloud.google.com',
            fetch_catalog.uri.split('gs://')[1])
    elif fetch_data['type'] == 'signed_url':
        # split the bucket path into the bucket name and full object path
        bucket_path = fetch_catalog.uri.split('gs://')[1]
        bucket_end = bucket_path.find('/')
        bucket_name = bucket_path[:bucket_end]
        object_name = bucket_path[bucket_end+1:]

        # handle catalog-specific authentication
        if fetch_data['catalog'].lower() == 'cfo':
            link = generate_signed_url(
                bucket_name, object_name,
                current_app.config['SIGN_URL_PUBLIC_KEY_PATH'])
        else:
            return (
                f"Signed URLS only available for CFO catalog. Entered; "
                f"{fetch_data['catalog']}", 400)
    elif fetch_type == 'wms_preview':
        link = flask.url_for(
            'stac.viewer', catalog=fetch_data['catalog'],
            asset_id=fetch_data['asset_id'], api_key=api_key,
            _external=True)
    elif fetch_type == 'wms':
        percent_thresholds = [0, 2, 25, 30, 50, 60, 75, 90, 98, 100]
        scaled_value_strings = [
            f'''p{percent_threshold}={
                fetch_catalog.raster_min + percent_threshold / 100.0 * (
                    fetch_catalog.raster_max -
                    fetch_catalog.raster_min)}'''
            for percent_threshold in percent_thresholds]

        link = (
            f"http://{current_app.config['GEOSERVER_HOST']}/geoserver/"
            f"{fetch_data['catalog']}/wms"
            f"?layers={fetch_data['catalog']}:{fetch_data['asset_id']}"
            f'&format="image/png"'
            f'&styles={fetch_catalog.default_style}&'
            f'{"&".join(scaled_value_strings)}')

    response = flask.Response({
         'type': fetch_data['type'],
         'link': link,
         'raster_min': fetch_catalog.raster_min,
         'raster_max': fetch_catalog.raster_max,
         'raster_mean': fetch_catalog.raster_mean,
         'raster_stdev': fetch_catalog.raster_stdev,
    })

    # handle browser compatibility problem where safari default reads
    # bucket links inline instead of downloading the file
    if fetch_data['type'] in ['url', 'signed_url']:
        keys = list(DOWNLOAD_HEADERS.keys())
        for key in keys:
            response.headers[key] = DOWNLOAD_HEADERS[key]

    return response


@stac_bp.route('/styles')
def styles():
    """Return available styles."""
    with open(current_app.config['GEOSERVER_PASSWORD_FILE'], 'r') as password_file:
        master_geoserver_password = password_file.read()
    session = requests.Session()
    session.auth = (current_app.config['GEOSERVER_USER'], master_geoserver_password)
    available_styles = do_rest_action(
        session.get,
        f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
        f'geoserver/rest/styles.json').json()

    return {'styles': [
        style['name']
        for style in available_styles['styles']['style']
        if style['name'] not in ['generic', 'line', 'point', 'polygon']]}


@stac_bp.route('/list')
def render_list():
    """Render a listing webpage."""
    try:
        api_key = flask.request.args['api_key']
        return flask.render_template('list.html', **{
            'search_url': flask.url_for(
                'stac.search', api_key=api_key, _external=True),
            'fetch_url': flask.url_for(
                'stac.fetch', api_key=api_key, _external=True),
        }, _external=True)
    except Exception:
        LOGGER.exception('error on render list')
        raise


@stac_bp.route('/viewer')
def viewer():
    """Render a viewer webpage."""
    catalog = flask.request.args['catalog']
    asset_id = flask.request.args['asset_id']

    catalog_entry = queries.find_catalog_by_id(catalog, asset_id)

    if catalog_entry is None:
        return (
            f'{asset_id}:{catalog} not found', 400)

    nodata = pygeoprocessing.get_raster_info(
        catalog_entry.local_path)['nodata'][0]

    x_center = (catalog_entry.bb_xmax+catalog_entry.bb_xmin)/2
    y_center = (catalog_entry.bb_ymax+catalog_entry.bb_ymin)/2

    return flask.render_template('viewer.html', **{
        'catalog': catalog,
        'asset_id': asset_id,
        'geoserver_url': (
            f"http://{current_app.config['GEOSERVER_HOST']}/"
            f"geoserver/{catalog}/wms"),
        'original_style': catalog_entry.default_style,
        'p0': catalog_entry.raster_min,
        'p100': catalog_entry.raster_max,
        'pixel_pick_url': flask.url_for('stac.pixel_pick', _external=True),
        'x_center': x_center,
        'y_center': y_center,
        'min_lat': catalog_entry.bb_ymin,
        'min_lng': catalog_entry.bb_xmin,
        'max_lat': catalog_entry.bb_ymax,
        'max_lng': catalog_entry.bb_xmax,
        'geoserver_style_url': flask.url_for('stac.styles', _external=True),
        'nodata': nodata,
    }, _external=True)


@stac_bp.route('/search', methods=["POST"])
def search():
    """Search the catalog using STAC format.

    Args:
        query parameter:
            api_key, used to filter query results, must have READ:* or
                READ:[catalog] access to get results from that catalog.
        body parameters include:
            bounding_box = xmin, ymin, xmax, ymax
            catalog_list = 'list', 'of', 'catalogs'
            asset_id = complete or partial asset id
            datetime =
                "exact time" | "low_time/high_time" | "../high time" |
                "low time/.."
            description --- partial match

    Responses:
        json:
            {
                'features': [
                    {
                        # 'id' can be used to fetch
                        'id': {catalog}:{id},
                        # bbox is overlap with query bbox
                        'bbox': [xmin, ymin, xmax, ymax],
                        'description': 'asset description',
                        'utc_datetime': UTC datetime associated with asset,
                            either defined at publish or is the publis
                            time.
                        'expiration_utc_datetime': UTC datetime in which
                            this asset will expire.
                        'attribute_dict':
                            dictionary of additional attributes
                        'utc_now': utc datetime at the time of the search
                    }
                ],
                'utc_now': "string of the UTC time of search"
            }

        400 if invalid api key

    Returns:
        None.

    """
    try:
        api_key = flask.request.args['api_key']
        allowed_permissions = queries.get_allowed_permissions_map(api_key)

        if not allowed_permissions:
            return 'invalid api key', 400

        if not allowed_permissions['READ']:
            # No allowed catalogs so no results.
            return {
                'features': [],
                'utc_now': utc_now()}

        if not isinstance(flask.request.json, dict):
            search_data = json.loads(flask.request.json)
        else:
            search_data = flask.request.json
        LOGGER.debug(f'incoming search data: {search_data}')

        bounding_box_list = None
        if search_data['bounding_box']:
            bounding_box_list = [
                float(val) for val in search_data['bounding_box'].split(',')]

        asset_id = search_data.get('asset_id', None)
        description = search_data.get('description', None)

        asset_list = queries.get_assets_query.query(
            allowed_permissions['READ'], bounding_box_list=bounding_box_list,
            datetime_str=search_data['datetime'], asset_id=asset_id,
            description=description).all()

        feature_list = []
        for asset in asset_list:
            # search for additional attributes
            attribute_dict = queries.get_asset_attributes(
                asset.asset_id, asset.catalog)
            feature_list.append(
                {
                    'id': f'{asset.catalog}:{asset.asset_id}',
                    'bbox': [
                        asset.bb_xmin, asset.bb_ymin,
                        asset.bb_xmax, asset.bb_ymax],
                    'utc_datetime': asset.utc_datetime,
                    'expiration_utc_datetime': asset.expiration_utc_datetime,
                    'description': asset.description,
                    'attribute_dict': attribute_dict,
                })
        return {
            'features': feature_list,
            'utc_now': utc_now()}
    except Exception as e:
        LOGGER.exception('something went wrong')
        return str(e), 500


@stac_bp.route('/get_status/<job_id>')
def get_status(job_id):
    """Return the status of the session."""
    LOGGER.debug('getting status for %s', job_id)

    job_status = queries.get_job_status(job_id)
    if job_status:
        return {
            'job_id': job_status.job_id,
            'status': job_status.job_status,
            }
    else:
        return f'no status for {job_id}', 500


@stac_bp.route('/publish', methods=['POST'])
def publish():
    """Add a raster to GeoServer from local storage.

    Request parameters:
        query parameters:
            api_key (str): api key that has WRITE:catalog access.

        body parameters in json format:
            catalog (str): catalog to publish to.
            id (str): raster ID, must be unique to the catalog.
            mediatype (str): mediatype of the raster. Currently only
                'GeoTIFF' is supported.
            uri (str): uri to the asset that is accessible by this server.
                Currently supports only `gs://`.
            description (str): description of the asset
            force (bool): (optional) if True, will overwrite existing
                catalog:id asset
            utc_datetime (str): if present sets the datetime to this
                string, if absent sets the datetime of the asset to the UTC
                time at publishing. String must be formatted as
                "Y-m-d H:M:S TZ", ex: '2018-06-29 17:08:00 UTC'.
            default_style (str): if present sets the default style when
                "fetch"ed by a future REST API call.
            attribute_dict (dict): an arbitrary set of key/value pairs to
                associate with this asset.

    Returns:
        {'callback_url': ...}, 200 if successful. The `callback_url` can be
            queried for when the asset is published.
        401 if api key is not authorized for this service

    """
    try:
        api_key = flask.request.args['api_key']
        asset_args = json.loads(flask.request.json)

        if 'utc_datetime' in asset_args:
            utc_datetime = str(datetime.datetime.strptime(
                asset_args['utc_datetime'], '%Y-%m-%d %H:%M:%S %Z'))
        else:
            utc_datetime = utc_now()

        expiration_utc_datetime = asset_args.get(
            'expiration_utc_datetime', None)

        default_style = asset_args.get(
            'default_style', current_app.config['DEFAULT_STYLE'])

        LOGGER.debug(f"asset args: {str(asset_args)}")
        valid_check = validate_api(
            api_key, f"WRITE:{asset_args['catalog']}")
        if valid_check != 'valid':
            return valid_check
        LOGGER.debug(
            f"{api_key} has access to WRITE:{asset_args['catalog']}")

        if asset_args['mediatype'] != 'GeoTIFF':
            return 'invalid mediatype, only "GeoTIFF" supported', 400

        if not asset_args['catalog'] or not asset_args['asset_id']:
            return (
                f'invalid catalog:asset_id: '
                f'{asset_args["catalog"]}:{asset_args["asset_id"]}'), 400

        # see if catalog/id are already in db
        #   if not force(d), then return 403
        asset_count = queries.get_assets_query(
            [asset_args['catalog']], asset_id=asset_args['asset_id']).count()

        force = 'force' in asset_args and asset_args['force']
        if asset_count > 0 and not force:
            return (
                f'{asset_args["catalog"]}:{asset_args["asset_id"]} '
                'already published, use force:True to overwrite.'), 400

        # build job
        job_id = build_job_hash(asset_args)
        callback_url = flask.url_for(
            'stac.get_status', job_id=job_id, api_key=api_key, _external=True)
        callback_payload = json.dumps({'callback_url': callback_url})

        # see if job already running and hasn't previously errored
        job_status = queries.get_job_status(job_id)
        if job_status and 'ERROR' not in job_status.job_status:
            return (
                f'{asset_args["catalog"]}:{asset_args["asset_id"]} '
                f'actively processing from {callback_url}, wait '
                f'until finished before sending new uri', 400)

        # new job
        _ = services.create_job(job_id, asset_args['uri'], 'scheduled')

        if 'attribute_dict' in asset_args:
            attribute_dict = asset_args['attribute_dict']
        else:
            attribute_dict = None
        raster_worker_thread = threading.Thread(
            target=add_raster_worker,
            args=(asset_args['uri'], asset_args['mediatype'],
                  asset_args['catalog'], asset_args['asset_id'],
                  asset_args['description'],
                  utc_datetime, default_style, job_id, attribute_dict,
                  expiration_utc_datetime,
                  current_app.config['INTER_GEOSERVER_DATA_DIR'],
                  current_app.config['GEOSERVER_DATA_DIR']),
            kwargs={'force': force})
        raster_worker_thread.start()

        models.db.session.commit()
        return callback_payload
    except Exception:
        LOGGER.exception('something bad happened on publish')
        services.update_job_status(job_id, traceback.format_exc())
        models.db.session.commit()
        raise


@stac_bp.route('/delete', methods=['POST'])
def delete():
    """Remove from the GeoServer.

    Request parameters:
        query parameters:
            api_key (str): api key that has WRITE:catalog access.

        body parameters in json format:
            catalog (str): catalog to delete from
            id (str): raster ID, must be unique to the catalog.

    Returns:
        200 if successful
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
        LOGGER.debug(
            f"{api_key} has access to WRITE:{asset_args['catalog']}")

        if not asset_args['catalog'] or not asset_args['asset_id']:
            return (
                f'invalid catalog:asset_id: '
                f'{asset_args["catalog"]}:{asset_args["asset_id"]}'), 401

        # see if catalog/id are already in db if not, return 403
        catalog_entry = queries.find_catalog_by_id(
            asset_args['catalog'], asset_args['asset_id'])

        if catalog_entry is None:
            return (
                f'{asset_args["catalog"]}:{asset_args["asset_id"]} '
                'is not in the catalog, nothing to delete.'), 400

        delete_raster(catalog_entry)
        models.db.session.delete(catalog_entry)
        models.db.session.commit()

        return (
            f'{asset_args["catalog"]}:{asset_args["asset_id"]} deleted',
            200)
    except Exception:
        LOGGER.exception('something bad happened on delete')
        raise


def delete_raster(catalog_entry):
    """Delete a given asset from the geoserver and local stoarge.

    Args:
        catalog_entry (models.CatalogEntry): asset object that refers to a
            raster to be deleted.

    Returns:
        None.

    """
    with open(current_app.config['GEOSERVER_PASSWORD_FILE'], 'r') as password_file:
        master_geoserver_password = password_file.read()
    session = requests.Session()
    session.auth = (
        current_app.config['GEOSERVER_USER'], master_geoserver_password)

    cover_id = f'{catalog_entry.asset_id}_cover'
    delete_coverstore_result = do_rest_action(
        session.delete,
        f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
        f'geoserver/rest/workspaces/{catalog_entry.catalog}/'
        f'coveragestores/{cover_id}/?purge=all&recurse=true')
    if not delete_coverstore_result:
        raise RuntimeError(f"Unable to delete {cover_id}")

    # Don't wait for the remove to happen before returning, it could
    # take a bit of time.
    remove_thread = threading.Thread(
        target=os.remove,
        args=(catalog_entry.local_path,))
    remove_thread.start()


@retrying.retry(
    wait_exponential_multiplier=1000, wait_exponential_max=5000,
    stop_max_attempt_number=5)
def do_rest_action(
        session_fn, host, suburl, data=None, json=None, headers=None):
    """Wrapper around REST functions to make for easy retry.

    Args:
        sesson_fn (function): takes a url, optional data parameter, and
            optional json parameter.

    Returns:
        result of `session_fn` on arguments.

    """
    try:
        return session_fn(
            urllib.parse.urljoin(host, suburl), data=data, json=json,
            headers=headers)
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
    with current_app.app_context():
        with open(current_app.config['GEOSERVER_PASSWORD_FILE'], 'r') as password_file:
            master_geoserver_password = password_file.read()
        session = requests.Session()
        session.auth = (
            current_app.config['GEOSERVER_USER'], master_geoserver_password)

        # make workspace
        LOGGER.debug('create workspace if it does not exist')
        workspace_exists_result = do_rest_action(
            session.get,
            f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
            f'geoserver/rest/workspaces/{catalog}')
        if not workspace_exists_result:
            LOGGER.debug(f'{catalog} does not exist, creating it')
            create_workspace_result = do_rest_action(
                session.post,
                f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
                'geoserver/rest/workspaces',
                json={'workspace': {'name': catalog}})
            if not create_workspace_result:
                # must be an error
                raise RuntimeError(create_workspace_result.text)

        # check if coverstore exists, if so delete it
        cover_id = f'{raster_id}_cover'
        coverstore_exists_result = do_rest_action(
            session.get,
            f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
            f'geoserver/rest/workspaces/{catalog}/coveragestores/{cover_id}')

        LOGGER.debug(
            f'coverstore_exists_result: {str(coverstore_exists_result)}')

        if coverstore_exists_result:
            LOGGER.warning(f'{catalog}:{cover_id}, so deleting it')
            # coverstore exists, delete it
            delete_coverstore_result = do_rest_action(
                session.delete,
                f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
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
            f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
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
        raster_srs.ImportFromWkt(raster_info['projection_wkt'])
        lat_lng_bounding_box = get_lat_lng_bounding_box(local_raster_path)

        epsg_crs = ':'.join(
            [raster_srs.GetAttrValue('AUTHORITY', i) for i in [0, 1]])

        LOGGER.debug('construct the cover_payload')

        cover_payload = {
            "coverage":
                {
                    "name": raster_id,
                    "nativeName": raster_id,
                    "namespace":
                        {
                            "name": catalog,
                            "href": (
                                f"""{current_app.config[
                                    'GEOSERVER_MANAGER_HOST']}/"""
                                f"geoserver/rest/namespaces/{catalog}.json")
                        },
                    "title": raster_id,
                    "description": "description here",
                    "abstract": "abstract here",
                    "keywords": {
                        "string": [raster_id, "WCS", "GeoTIFF"]
                        },
                    "nativeCRS": raster_info['projection_wkt'],
                    "srs": epsg_crs,
                    "nativeBoundingBox": {
                        "minx": raster_info['bounding_box'][0],
                        "maxx": raster_info['bounding_box'][2],
                        "miny": raster_info['bounding_box'][1],
                        "maxy": raster_info['bounding_box'][3],
                        "crs": raster_info['projection_wkt'],
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
                            f"""{
                                current_app.config['GEOSERVER_MANAGER_HOST']}/"""
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
                        "crs": raster_info['projection_wkt']
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
            f'{current_app.config["GEOSERVER_MANAGER_HOST"]}',
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
        raster_info['projection_wkt'], wgs84_srs.ExportToWkt())
    return lat_lng_bounding_box


def add_raster_worker(
        uri_path, mediatype, catalog, asset_id, asset_description,
        utc_datetime, default_style, job_id, attribute_dict,
        expiration_utc_datetime, inter_data_dir, root_data_dir,
        force=False, keep_existing=True):
    """Copy and update a coverage set asynchronously.

    Args:
        uri_path (str): path to base gs:// bucket to copy from.
        mediatype (str): raster mediatype, only GeoTIFF supported
        catalog (str): catalog for asset
        asset_id (str): raster id for asset
        asset_description (str): asset description to record
        utc_datetime (str): an ISO standard UTC utc_datetime
        default_style (str): default style to record with this asset
        job_id (str): used to identify entry in job_table
        attribute_dict (dict): a key/value pair mapping of arbitrary attributes
            for this asset, can be None.
        expiration_utc_datetime (str): either None or UTC formatted string
            indicating when this raster should be automatically removed from
            database and local storage.
        inter_data_dir (str): directory path to prefix for the geoserver's
            internal raster path relative to its own data directory.
        root_data_dir (str): directory in which to copy this raster.
            `inter_data_dir` must be a suffix of this string.
        force (bool): if True will overwrite existing local data, otherwise
            does not re-copy data.

    Returns:
        None.

    """
    with db.app.app_context():
        try:
            local_catalog_asset_path = os.path.join(catalog, f'{asset_id}.tif')
            LOGGER.debug(
                f'local_catalog_asset_path: {local_catalog_asset_path}\n'
                f'inter_data_dir: {inter_data_dir}\n'
                f'root_data_dir: {root_data_dir}')
            inter_geoserver_raster_path = os.path.join(
                inter_data_dir, local_catalog_asset_path)
            # local data dir is for path to copy to from working directory
            target_raster_path = os.path.join(
                root_data_dir, inter_data_dir, local_catalog_asset_path)

            try:
                os.makedirs(os.path.dirname(target_raster_path))
            except OSError:
                pass

            services.update_job_status(job_id, 'copying local')
            db.session.commit()

            LOGGER.debug('copy %s to %s', uri_path, target_raster_path)
            if os.path.exists(target_raster_path):
                # check the size of any existing file first
                existing_ls_line_result = subprocess.run(
                   ['ls', '-l', target_raster_path], stdout=subprocess.PIPE,
                   check=True)
                existing_ls_line = existing_ls_line_result.stdout.decode(
                    'utf-8').rstrip().split('\n')[-1].split()
                existing_object_size = int(existing_ls_line[4])
            else:
                existing_object_size = 0

            # get the object size
            gsutil_ls_result = subprocess.run(
               [f'gsutil ls -l "{uri_path}"'], stdout=subprocess.PIPE,
               check=True, shell=True)
            LOGGER.debug(f"raw output: {gsutil_ls_result.stdout}")
            last_gsutil_ls_line = gsutil_ls_result.stdout.decode(
                'utf-8').rstrip().split('\n')[-1].split()
            LOGGER.debug(f"last line: {last_gsutil_ls_line}")
            # say we need four times that because we might need to duplicate the
            # file and also build overviews for it. That shoud be ~3 times,
            # so might as well be safe and make it 4.
            gs_object_size = 4*int(last_gsutil_ls_line[
                last_gsutil_ls_line.index('bytes')-1])

            # get the file system size
            df_result = subprocess.run(
                ['df', os.path.dirname(target_raster_path)],
                stdout=subprocess.PIPE, check=True)
            fs, blocks, used, available_k, use_p, mount = (
                df_result.stdout.decode('utf-8').rstrip().split('\n')[-1].split())

            # turn kb to b
            available_b = int(available_k) * 2**10

            additional_b_needed = (
                (gs_object_size-existing_object_size) - available_b)
            LOGGER.debug(
                f'gs_object_size: {gs_object_size}, '
                f'existing_object_size: {existing_object_size} '
                f'available_b: {available_b}f'
                f'additional_b needed: {additional_b_needed}')
            if additional_b_needed > 0:
                # calculate additional GB needed
                additional_gb = int(math.ceil(additional_b_needed/2**30))
                LOGGER.warning(f'need an additional {additional_gb}G')
                session = requests.Session()
                resize_disk_request = do_rest_action(
                    session.post,
                    f'http://{current_app.config["DISK_RESIZE_SERVICE_HOST"]}',
                    f'resize',
                    json={'gb_to_add': additional_gb})

                if not resize_disk_request:
                    raise RuntimeError(
                        f'not enough space left on drive and unable to resize '
                        f'need {gs_object_size-existing_object_size} '
                        f'but have {available_b}.')

            if not keep_existing and os.path.exists(target_raster_path):
                # remove the file first
                os.remove(target_raster_path)

            subprocess.run([
                f'gsutil cp -n "{uri_path}" "{target_raster_path}"'],
                shell=True, check=True)

            if not os.path.exists(target_raster_path):
                raise RuntimeError(f"{target_raster_path} didn't copy")

            raster = gdal.OpenEx(target_raster_path, gdal.OF_RASTER)
            compression_alg = raster.GetMetadata(
                'IMAGE_STRUCTURE').get('COMPRESSION', None)
            if compression_alg in [None, 'ZSTD']:
                services.update_job_status(
                    job_id,
                    f'(re)compressing image from {compression_alg}, '
                    'this can take some time')
                db.session.commit()
                needs_compression_tmp_file = os.path.join(
                    os.path.dirname(target_raster_path),
                    f'NEEDS_COMPRESSION_{job_id}.tif')
                os.rename(target_raster_path, needs_compression_tmp_file)
                ecoshard.compress_raster(
                    needs_compression_tmp_file, target_raster_path,
                    compression_algorithm='LZW', compression_predictor=None)
                os.remove(needs_compression_tmp_file)

            services.update_job_status(
                job_id, 'building overviews (can take some time)')
            db.session.commit()

            ecoshard.build_overviews(
                target_raster_path, interpolation_method='average',
                overview_type='internal', rebuild_if_exists=False)

            services.update_job_status(job_id, 'publishing to geoserver')
            db.session.commit()

            publish_to_geoserver(
                inter_geoserver_raster_path, target_raster_path, catalog, asset_id,
                mediatype)

            LOGGER.debug('update job_table with complete')

            services.update_job_status(job_id, 'update catlog database geoserver')
            db.session.commit()
            LOGGER.debug('update catalog_table with final values')
            lat_lng_bounding_box = get_lat_lng_bounding_box(target_raster_path)
            band = raster.GetRasterBand(1)
            raster_min, raster_max, raster_mean, raster_stdev = \
                band.GetStatistics(0, 1)
            _ = services.create_or_update_catalog_entry(
                asset_id, catalog,
                lat_lng_bounding_box[0],
                lat_lng_bounding_box[1],
                lat_lng_bounding_box[2],
                lat_lng_bounding_box[3],
                utc_datetime, mediatype, asset_description, uri_path,
                target_raster_path, raster_min, raster_max, raster_mean,
                raster_stdev, default_style, expiration_utc_datetime)

            if attribute_dict:
                LOGGER.debug('updating additional attributes')
                services.update_attributes(asset_id, catalog, attribute_dict)

            services.update_job_status(job_id, 'complete')
            db.session.commit()
            LOGGER.debug(f'successful publish of {catalog}:{asset_id}')

        except Exception as e:
            LOGGER.exception('something bad happened when doing raster worker')
            services.update_job_status(job_id, f'ERROR: {str(e)}')
            db.session.commit()
            if target_raster_path:
                # try to delete the local file in case it errored
                try:
                    os.remove(target_raster_path)
                except OSError:
                    LOGGER.exception(f'unable to remove {target_raster_path}')


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

    allowed_permissions = queries.get_allowed_permissions_map(api_key)

    if not allowed_permissions:
        return 'invalid api key', 400

    permission_type, catalog_id = permission.split(':')

    if catalog_id in allowed_permissions[permission_type]:
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


def utc_now():
    """Return string of current time in UTC."""
    return str(datetime.datetime.now(datetime.timezone.utc))


def expiration_monitor(base_app):
    """Monitor database for any entries that have expired and delete them.

    Args:
        base_app (flask.App): the base app so we can get context.

    Returns:
        None (never)

    """
    try:
        while True:
            current_time = utc_now()
            LOGGER.debug(f'checking for expired data at {current_time}')
            with base_app.app_context():
                expired_entries = queries.get_expired_catalog_entries(
                    current_time)

                for expired_catalog_entry in expired_entries:
                    LOGGER.info(
                        f'{expired_catalog_entry.asset_id}:'
                        f'{expired_catalog_entry.catalog} expired on '
                        f'{expired_catalog_entry.expiration_utc_datetime} '
                        f'current time is {current_time}. Deleting...')
                    delete_raster(
                        expired_catalog_entry.local_path,
                        expired_catalog_entry.asset_id,
                        expired_catalog_entry.catalog)

                    models.db.session.delete(expired_catalog_entry)
                if expired_entries:
                    models.db.session.commit()
            time.sleep(EXPIRATION_MONITOR_DELAY)
    except Exception:
        LOGGER.exception('something bad happened in expiration_monitor')


def generate_signed_url(
        bucket_name, object_name, service_account_file,
        subresource=None, expiration=604800, http_method='GET',
        query_parameters=None, headers=None):
    """Uses google authentication to sign URL for direct bucket downloads.

    Args:
        bucket_name (str): the cloud storage bucket storing the object
        object_name (str): the path to the storage object
        service_account_file (str): path to a google credentials file with
            bucket permissions
        expiration (int): time to link expiration in seconds
        http_method (str): anticipated request protocol
        query_parameters (dict): custom query parameters. leave as None for
            google defaults
        headers (dict): headers to return

    Returns:
        signed_url (str): an RSA-signed URL to the cloud storage object
    """
    # set limits on the expiration time (max is 7 days)
    if expiration > 604800:
        expiration = 604800

    escaped_object_name = quote(str.encode(object_name), safe=b'/~')
    canonical_uri = '/{}'.format(escaped_object_name)

    # specify active datetime
    datetime_now = datetime.datetime.utcnow()
    request_timestamp = datetime_now.strftime('%Y%m%dT%H%M%SZ')
    datestamp = datetime_now.strftime('%Y%m%d')

    # read the credentials used to format the url
    google_credentials = service_account.Credentials.from_service_account_file(
        service_account_file)
    client_email = google_credentials.service_account_email
    credential_scope = '{}/auto/storage/goog4_request'.format(datestamp)
    credential = '{}/{}'.format(client_email, credential_scope)

    # create the google-format headers
    if headers is None:
        headers = dict()
    host = '{}.storage.googleapis.com'.format(bucket_name)
    headers['host'] = host

    canonical_headers = ''
    ordered_headers = collections.OrderedDict(sorted(headers.items()))
    for k, v in ordered_headers.items():
        lower_k = str(k).lower()
        strip_v = str(v).lower()
        canonical_headers += '{}:{}\n'.format(lower_k, strip_v)

    signed_headers = ''
    for k, _ in ordered_headers.items():
        lower_k = str(k).lower()
        signed_headers += '{};'.format(lower_k)
    signed_headers = signed_headers[:-1]  # remove trailing ';'

    # set google default url params
    if query_parameters is None:
        query_parameters = dict()
    query_parameters['X-Goog-Algorithm'] = 'GOOG4-RSA-SHA256'
    query_parameters['X-Goog-Credential'] = credential
    query_parameters['X-Goog-Date'] = request_timestamp
    query_parameters['X-Goog-Expires'] = expiration
    query_parameters['X-Goog-SignedHeaders'] = signed_headers
    if subresource:
        query_parameters[subresource] = ''

    # join the shit
    canonical_query_string = ''
    ordered_query_parameters = collections.OrderedDict(
        sorted(query_parameters.items()))
    for k, v in ordered_query_parameters.items():
        encoded_k = quote(str(k), safe='')
        encoded_v = quote(str(v), safe='')
        canonical_query_string += '{}={}&'.format(encoded_k, encoded_v)
    canonical_query_string = canonical_query_string[:-1]  # remove trailing '&'

    canonical_request = '\n'.join([http_method,
                                   canonical_uri,
                                   canonical_query_string,
                                   canonical_headers,
                                   signed_headers,
                                   'UNSIGNED-PAYLOAD'])

    # hash it out
    canonical_request_hash = hashlib.sha256(
        canonical_request.encode()).hexdigest()

    string_to_sign = '\n'.join(['GOOG4-RSA-SHA256',
                                request_timestamp,
                                credential_scope,
                                canonical_request_hash])

    # signer.sign() signs using RSA-SHA256 with PKCS1v15 padding
    signature = binascii.hexlify(
        google_credentials.signer.sign(string_to_sign)
    ).decode()

    scheme_and_host = '{}://{}'.format('https', host)
    signed_url = '{}{}?{}&x-goog-signature={}'.format(
        scheme_and_host, canonical_uri, canonical_query_string, signature)

    return signed_url
