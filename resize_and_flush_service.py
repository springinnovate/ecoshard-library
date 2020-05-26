"""Service to monitor for new snapshots and create disk & flush if so."""
import argparse
import socket
import subprocess

import flask

APP = flask.Flask(__name__)

DISK_ITERATION = 0
DISK_PATTERN = None
LAST_SNAPSHOT_NAME = None
HEALTHY = True
LAST_DISK_NAME = None

POSSIBLE_MOUNT_DEVS = ['/dev/sdb', 'dev/sdc']
LAST_MOUNT_DEV_INDEX = 0


def swap_new_disk():
    """Try to swap in a new disk if one is available."""
    try:
        STATUS_STRING = 'search for new snapshot'
        snapshot_query = subprocess.run([
            "gcloud", "compute", "snapshots", "list", "--limit=1",
            "--sort-by=~name", f"--filter=name:({DISK_PATTERN})",
            "--format=value(name)"], stdout=subprocess.PIPE)
        snapshot_name = snapshot_query.stdout.rstrip().decode('utf-8')

        global DISK_ITERATION
        if (snapshot_name == LAST_SNAPSHOT_NAME and
                LAST_SNAPSHOT_NAME is not None):
            # not a new snapshot
            STATUS_STRING = f'on iteration {DISK_ITERATION}'
            return

        hostname = socket.gethostname()
        disk_name = f'{hostname}-data-{DISK_ITERATION}'
        DISK_ITERATION += 1

        STATUS_STRING = f'creating disk {disk_name}'
        subprocess.run([
            "gcloud", "compute", "disks", "create", disk_name,
            f"--source-snapshot={snapshot_name}", "--zone=us-west1-b"])

        global STATUS_STRING
        STATUS_STRING = f'attaching disk {disk_name}'

        subprocess.run([
            "gcloud", "compute", "instances", "attach-disk", hostname,
            f"--disk={disk_name}", "--zone=us-west1-b"])

        if LAST_SNAPSHOT_NAME:
            STATUS_STRING = f'unmounting {MOUNT_POINT}'
            subprocess.run(["umount", MOUNT_POINT])

        mount_device = POSSIBLE_MOUNT_DEVS[LAST_MOUNT_DEV_INDEX]
        LAST_MOUNT_DEV_INDEX = (
            LAST_MOUNT_DEV_INDEX+1) % len(POSSIBLE_MOUNT_DEVS)
        STATUS_STRING = f'mounting {mount_device} at {MOUNT_POINT}'
        subprocess.run(["mount", mount_device, MOUNT_POINT])

        LAST_SNAPSHOT_NAME = snapshot_name



        # TODO: detach the old disk
        # gcloud compute instances detach-disk `hostname` --disk=stac-geoserver-manager-data-3 --zone=us-west1-b

        global LAST_DISK_NAME
        if LAST_DISK_NAME:
            STATUS_STRING = f'detaching {LAST_DISK_NAME}'


            STATUS_STRING = f'deleting {LAST_DISK_NAME}'
            subprocess.run([
                "gcloud", "compute", "disks", "delete", LAST_DISK_NAME,
                "--zone=us-west1-b"])
        LAST_DISK_NAME = disk_name

        # TOOD: refresh the GeoServer
        # 'geoserver' is the default geoserver password, we'll need to be
        # authenticated to do the push
        STATUS_STRING = f'refreshing geoserver'
        with open(PASSWORD_FILE_PATH, 'r') as password_file:
            master_geoserver_password = password_file.read()
        session = requests.Session()
        session.auth = ('admin', master_geoserver_password)

        password_update_request = do_rest_action(
            session.post,
            f'http://{LOCAL_GEOSERVER}',
            'geoserver/rest/reload')
        STATUS_STRING = f'on iteration {DISK_ITERATION}'

    except Exception as e:
        STATUS_STRING = f'error: {STATUS_STRING}'


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
