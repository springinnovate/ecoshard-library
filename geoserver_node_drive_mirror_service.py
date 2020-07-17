"""Service to monitor for new snapshots and create disk & flush if so."""
import argparse
import datetime
import logging
import os
import socket
import subprocess
import sys
import time
import threading
import urllib
import uuid

import flask
import retrying

APP = flask.Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'),
    stream=sys.stdout)
LOGGER = logging.getLogger(__name__)
logger = logging.getLogger('waitress')
logger.setLevel(logging.DEBUG)

LAST_SNAPSHOT_NAME = None
LAST_DISK_NAME = None
HEALTHY = False


@retrying.retry(
    wait_exponential_multiplier=1000, wait_exponential_max=5000,
    stop_max_attempt_number=5)
def do_rest_action(
        session_fn, host, suburl, data=None, json=None, headers=None):
    """A wrapper around HTML functions to make for easy retry.

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


def new_disk_monitor_docker_manager(
        snapshot_pattern, mount_point, check_time, service_name,
        mem_size):
    """Monitor for new snapshots matching pattern. Create copy if one appears.

    Args:
        snapshot_pattern (str): the string to match for a new snapshot
        mount_point (str): system location to mount the drive
        check_time (float): how many seconds to wait between snapshot checks
        service_name (str): name to use for docker-compose restart
        mem_size (str): Java formatted max memory string i.e. "12G"

    Returns:
        None

    """
    global HEALTHY
    global STATUS_STRING
    global LAST_SNAPSHOT_NAME
    global LAST_DISK_NAME
    disk_iteration = 0
    container_running = False
    while True:
        try:
            # get existing devices
            lsblk_result = subprocess.run(
                ["lsblk"], stdout=subprocess.PIPE,
                check=True).stdout.rstrip().decode('utf-8')
            existing_dev_names = set([
                line.split(' ')[0] for line in lsblk_result.split('\n')])

            STATUS_STRING = 'search for new snapshot'
            LOGGER.info(STATUS_STRING)
            snapshot_query = subprocess.run([
                "gcloud", "compute", "snapshots", "list", "--limit=1",
                "--sort-by=~name", f"--filter=name:({snapshot_pattern})",
                "--format=value(name)"], stdout=subprocess.PIPE,
                check=True)
            snapshot_name = snapshot_query.stdout.rstrip().decode('utf-8')
            LOGGER.debug(f"this is the latest snapshot: {snapshot_name}")
            if (snapshot_name == LAST_SNAPSHOT_NAME and
                    LAST_SNAPSHOT_NAME is not None):
                # not a new snapshot
                STATUS_STRING = f'last checked: {str(datetime.datetime.now())}'
                LOGGER.info(STATUS_STRING)
                continue
            STATUS_STRING = f'creating new disk from snapshot {snapshot_name}'
            LOGGER.info(STATUS_STRING)

            # create new disk
            hostname = socket.gethostname()
            disk_name = (f'{hostname}-data-{uuid.uuid4().hex}')[:59]
            STATUS_STRING = f'creating disk {disk_name}'
            LOGGER.info(STATUS_STRING)
            disk_iteration += 1
            subprocess.run([
                "gcloud", "compute", "disks", "create", disk_name,
                f"--source-snapshot={snapshot_name}", "--type=pd-ssd",
                "--zone=us-west1-b"], check=True)

            # attach the new disk to the current host, sometimes it takes a bit
            # for the disk to become available to attach after it's been
            # created, be tolerant of that
            attach_attempts = 0
            STATUS_STRING = f'attaching disk {disk_name}, inital attempt'
            LOGGER.info(STATUS_STRING)
            while True:
                # give it 5 seconds to come online
                time.sleep(5)
                try:
                    attach_attempts += 1
                    subprocess.run([
                        "gcloud", "compute", "instances", "attach-disk",
                        hostname, f"--disk={disk_name}", "--zone=us-west1-b"],
                        check=True)
                    STATUS_STRING = \
                        f'attached {disk_name}, {attach_attempts} attempts'
                    LOGGER.info(STATUS_STRING)
                    break
                except subprocess.CalledProcessError:
                    STATUS_STRING = f'attach attempt {attach_attempts} failed'
                    LOGGER.exception(STATUS_STRING)
                    if attach_attempts > 10:
                        HEALTHY = False
                        raise RuntimeError(
                            f'{attach_attempts} for disk {disk_name} failed')

            STATUS_STRING = f'setting disk {disk_name} to autodelete'
            LOGGER.info(STATUS_STRING)
            subprocess.run([
                "gcloud", "compute", "instances", "set-disk-auto-delete",
                hostname, f"--disk={disk_name}", "--zone=us-west1-b"],
                check=True)

            # unmount the current disk if any is mounted
            try:
                STATUS_STRING = f'unmounting {mount_point}'
                LOGGER.info(STATUS_STRING)
                subprocess.run(["umount", mount_point], check=True)
            except Exception:
                LOGGER.exception(f'exception when unmounting {mount_point}')

            STATUS_STRING = f'ensuring {mount_point} exists'
            LOGGER.info(STATUS_STRING)
            subprocess.run(["mkdir", "-p", mount_point])

            LAST_SNAPSHOT_NAME = snapshot_name

            # mount the new disk at the mount point
            lsblk_result = subprocess.run(
                ["lsblk"], stdout=subprocess.PIPE,
                check=True).stdout.rstrip().decode('utf-8')
            new_dev_names = set([
                lsblk_result.split(' ')[0]
                for lsblk_result in lsblk_result.split('\n')])
            mount_device = list(new_dev_names.difference(
                existing_dev_names))[0]
            device_location = f'/dev/{mount_device}'
            STATUS_STRING = f'mounting {device_location} at {MOUNT_POINT}'
            LOGGER.info(STATUS_STRING)
            try:
                subprocess.run(
                    ["mount", device_location, MOUNT_POINT], check=True)
            except Exception:
                LOGGER.exception("mount failed")
                HEALTHY = False
                raise

            try:
                if container_running:
                    STATUS_STRING = f'stopping docker container'
                    LOGGER.info(STATUS_STRING)
                    subprocess.run(
                        ["docker-compose", "down"], check=True)
                    container_running = False

                STATUS_STRING = f'starting docker container'
                LOGGER.info(STATUS_STRING)
                subprocess.run([
                    "docker-compose", "up", "-d", "--remove-orphans",
                    "--build", service_name], check=True)
                container_running = True
                HEALTHY = True
            except Exception:
                LOGGER.exception('stopping or starting failed')
                HEALTHY = False

            # Detach and delete the old disk
            if LAST_DISK_NAME:
                STATUS_STRING = f'detatch old {LAST_DISK_NAME}'
                LOGGER.info(STATUS_STRING)
                subprocess.run([
                    "gcloud", "compute", "instances", "detach-disk",
                    hostname, f"--disk={LAST_DISK_NAME}", "--zone=us-west1-b"],
                    check=True)

                STATUS_STRING = f'deleting old {LAST_DISK_NAME}'
                LOGGER.info(STATUS_STRING)
                subprocess.run([
                    f"yes|gcloud compute disks delete {LAST_DISK_NAME} "
                    f"--zone={google_cloud_zone}"], check=True, shell=True)

            LAST_DISK_NAME = disk_name
            STATUS_STRING = f'last checked: {str(datetime.datetime.now())}'

        except Exception as e:
            STATUS_STRING = f'error: {str(e)}'
            LOGGER.exception(STATUS_STRING)
        LOGGER.debug(f'sleeping {check_time} seconds')
        time.sleep(check_time)


@APP.route('/', methods=['GET'])
def processing_status():
    """Return the state of processing."""
    if HEALTHY:
        return (
            f'last snapshot: {LAST_SNAPSHOT_NAME}\n'
            f'last disk: {LAST_DISK_NAME}\nstatus: {STATUS_STRING}', 200)
    return STATUS_STRING, 500


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='disk remounter')
    parser.add_argument(
        '--app_port', type=int, required=True,
        help='port to respond to status queries')
    parser.add_argument(
        '--snapshot_pattern', type=str, required=True, help=(
            'pattern of disk snapshot to query for, ex '
            '"geoserver-data-disk*"'))
    parser.add_argument(
        '--mount_point', type=str, required=True, help=(
            'mount point location ex /mnt/geoserver_data'))
    parser.add_argument(
        '--check_time', type=float, default=5*60, help=(
            'how many seconds to wait between checking for a new disk'))
    parser.add_argument(
        '--container_name', type=str, required=True, help=(
            'desired name of docker container running the geoserver node'))
    parser.add_argument(
        '--image_name', type=str, required=True, help=(
            'docker image name to run'))
    parser.add_argument(
        '--mem_size', type=str, required=True, help=(
            'java formatted max mem size string eg "12G"'))
    parser.add_argument(
        '--google_cloud_zone', type=str, required=True, help=(
            'google cloud zone that holds the disk "eg us-west1-b"'))

    args = parser.parse_args()
    snapshot_PATTERN = args.snapshot_pattern
    MOUNT_POINT = args.mount_point
    DISK_ITERATION = 0
    STATUS_STRING = "startup"
    PASSWORD_FILE_PATH = os.path.join(
        args.mount_point, 'data', 'secrets', 'adminpass')
    swap_thread = threading.Thread(
        target=new_disk_monitor_docker_manager,
        args=(args.snapshot_pattern, args.mount_point, args.check_time,
              args.service_name, args.mem_size))
    swap_thread.start()

    APP.run(
        host='0.0.0.0',
        port=args.app_port)
