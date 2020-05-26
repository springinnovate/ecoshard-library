"""Service to monitor for new snapshots and create disk & flush if so."""
import argparse
import datetime
import logging
import os
import socket
import subprocess
import time
import uuid

import flask
import requests
import stac_spec

APP = flask.Flask(__name__)

DISK_ITERATION = 0
DISK_PATTERN = None
LAST_SNAPSHOT_NAME = None
HEALTHY = True
LAST_DISK_NAME = None

POSSIBLE_MOUNT_DEVS = ['/dev/sdb', 'dev/sdc']
LAST_MOUNT_DEV_INDEX = 0

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'))
LOGGER = logging.getLogger(__name__)
logger = logging.getLogger('waitress')
logger.setLevel(logging.DEBUG)


def swap_new_disk():
    """Try to swap in a new disk if one is available."""
    while True:
        try:
            global STATUS_STRING
            STATUS_STRING = 'search for new snapshot'
            LOGGER.info(STATUS_STRING)
            snapshot_query = subprocess.run([
                "gcloud", "compute", "snapshots", "list", "--limit=1",
                "--sort-by=~name", f"--filter=name:({DISK_PATTERN})",
                "--format=value(name)"], stdout=subprocess.PIPE)
            snapshot_name = snapshot_query.stdout.rstrip().decode('utf-8')

            global DISK_ITERATION
            global LAST_SNAPSHOT_NAME
            if (snapshot_name == LAST_SNAPSHOT_NAME and
                    LAST_SNAPSHOT_NAME is not None):
                # not a new snapshot
                LOGGER.info(STATUS_STRING)
                STATUS_STRING = f'last checked: {str(datetime.datetime.now())}'
                continue

            # create new disk
            hostname = socket.gethostname()
            disk_name = (f'{hostname}-data-{uuid.uuid4().hex}')[:59]
            LOGGER.info(STATUS_STRING)
            STATUS_STRING = f'creating disk {disk_name}'
            DISK_ITERATION += 1
            subprocess.run([
                "gcloud", "compute", "disks", "create", disk_name,
                f"--source-snapshot={snapshot_name}", "--zone=us-west1-b"])

            # attach the new disk to the current host
            LOGGER.info(STATUS_STRING)
            STATUS_STRING = f'attaching disk {disk_name}'
            subprocess.run([
                "gcloud", "compute", "instances", "attach-disk", hostname,
                f"--disk={disk_name}", "--zone=us-west1-b"])

            # unmount the current disk if any is mounted
            global MOUNT_POINT
            if LAST_SNAPSHOT_NAME:
                LOGGER.info(STATUS_STRING)
                STATUS_STRING = f'unmounting {MOUNT_POINT}'
                subprocess.run(["umount", MOUNT_POINT])

            LAST_SNAPSHOT_NAME = snapshot_name

            # mount the new disk at the mount point
            global LAST_MOUNT_DEV_INDEX
            mount_device = POSSIBLE_MOUNT_DEVS[LAST_MOUNT_DEV_INDEX]
            LAST_MOUNT_DEV_INDEX = (
                LAST_MOUNT_DEV_INDEX+1) % len(POSSIBLE_MOUNT_DEVS)
            LOGGER.info(STATUS_STRING)
            STATUS_STRING = f'mounting {mount_device} at {MOUNT_POINT}'
            subprocess.run(["mount", mount_device, MOUNT_POINT])

            # Detach and delete the old disk
            global LAST_DISK_NAME
            if LAST_DISK_NAME:
                LOGGER.info(STATUS_STRING)
                STATUS_STRING = f'detatch old {LAST_DISK_NAME}'
                subprocess.run([
                    "gcloud", "compute", "instances", "detach-disk",
                    hostname, f"--disk={LAST_DISK_NAME}", "--zone=us-west1-b"])

                LOGGER.info(STATUS_STRING)
                STATUS_STRING = f'deleting old {LAST_DISK_NAME}'
                subprocess.run([
                    f"yes|gcloud compute disks delete {LAST_DISK_NAME} "
                    "--zone=us-west1-b"])

            LAST_DISK_NAME = disk_name

            # refresh the GeoServer
            LOGGER.info(STATUS_STRING)
            STATUS_STRING = f'refreshing geoserver'
            with open(PASSWORD_FILE_PATH, 'r') as password_file:
                master_geoserver_password = password_file.read()
            session = requests.Session()
            session.auth = ('admin', master_geoserver_password)

            refresh_geoserver = stac_spec.do_rest_action(
                session.post,
                f'http://localhost:8080',
                'geoserver/rest/reload')
            if refresh_geoserver:
                LOGGER.info(STATUS_STRING)
                STATUS_STRING = f'on iteration {DISK_ITERATION}'
            else:
                raise RuntimeError(
                    f'update failed: {str(refresh_geoserver)}')
        except Exception as e:
            LOGGER.info(STATUS_STRING)
            STATUS_STRING = f'error: {str(e)}'
        time.sleep(60*5)


@APP.route('/', methods=['GET'])
def processing_status():
    """Return the state of processing."""
    if STATUS_STRING.startswith('error'):
        return STATUS_STRING, 500
    return STATUS_STRING, 200


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='disk remounter')
    parser.add_argument(
        '--app_port', type=int, required=True,
        help='port to respond to status queries')
    parser.add_argument(
        '--disk_pattern', type=str, required=True, help=(
            'pattern of disk snapshot to query for, ex '
            '"geoserver-data-disk*"'))
    parser.add_argument(
        '--mount_point', type=str, required=True, help=(
            'mount point location ex /mnt/geoserver_data'))
    args = parser.parse_args()
    DISK_PATTERN = args.disk_pattern
    MOUNT_POINT = args.mount_point
    DISK_ITERATION = 0
    STATUS_STRING = "startup"
    PASSWORD_FILE_PATH = os.path.join(args.mount_point, 'secrets', 'adminpass')
    swap_new_disk()

    APP.run(
        host='0.0.0.0',
        port=args.app_port)
