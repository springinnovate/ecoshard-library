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

import flask
import requests
import retrying


APP = flask.Flask(__name__)
DEFAULT_WORKSPACE = 'default_workspace'
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
def do_rest_action(session_fn, host, suburl, data=None):
    """Do a 'get' for the host/suburl."""
    try:
        return session_fn(urllib.parse.urljoin(host, suburl), data=None)
    except Exception:
        LOGGER.exception('error in function')
        raise


def add_raster_worker(session_id, name, uri_path):
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
            ['gsutil', 'cp', uri_path, local_path], shell=True, check=True)

        _execute_sqlite(
            '''
            UPDATE work_status_table
            SET work_status='updating geoserver', last_accessed=?
            WHERE session_id=?;
            ''', DATABASE_PATH, argument_list=[time.time(), session_id],
            mode='modify', execute='execute')

        session = requests.Session()
        session.auth = ('admin', 'geoserver')
        coveragestore_payload = {
          "coverageStore": {
            "name": name,
            "url": local_path
          }
        }
        do_rest_action(
            session.post,
            'http://localhost:8080',
            f'geoserver/rest/workspaces/{DEFAULT_WORKSPACE}/coveragestores',
            data=coveragestore_payload)
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

    APP.config.update(SERVER_NAME='localhost:8888')
    APP.run(host='0.0.0.0', port=8888)

    parser = argparse.ArgumentParser(description='GeoServer manager')
    parser.add_argument(
        'geoserver_host', type=str, help='geoserver host/port to connect to')
    parser.add_argument(
        'geoserver_admin_password', type=str, help='geoserver admin password')
    args = parser.parse_args()

    session = requests.Session()
    session.auth = ('admin', args.geoserver_admin_password)

    r = do_rest_action(
        session.get, args.geoserver_host, 'geoserver/rest/workspaces.json')
    result = r.json()

    for workspace in result['workspaces']['workspace']:
        workspace_name = workspace['name']
        r = do_rest_action(
            session.delete, args.geoserver_host,
            'geoserver/rest/workspaces/%s?recurse=true' % workspace_name)
        LOGGER.debug("delete result for %s: %s", workspace_name, str(r.json()))

    # Create empty workspace
    do_rest_action(
        session.post, args.geoserver_host,
        'geoserver/rest/workspaces?default=true',
        data={'name': DEFAULT_WORKSPACE})

