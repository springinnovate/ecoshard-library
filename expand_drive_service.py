"""Service to expand a particular drive."""
import argparse
import logging
import json
import subprocess
import sys

import flask

APP = flask.Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s (%(relativeCreated)d) %(processName)s %(levelname)s '
        '%(name)s [%(funcName)s:%(lineno)d] %(message)s'),
    stream=sys.stdout)
LOGGER = logging.getLogger(__name__)


@APP.route('/resize', methods=['POST'])
def resize():
    """Resize the disk."""
    gb_to_add = json.loads(flask.request.get_data())['gb_to_add']

    gsutil_ls_result = subprocess.run([
        'gcloud', 'compute', 'disks', 'describe', DISK_NAME, f'--zone={ZONE}',
        '--flatten', 'sizeGb', '--project=salo-api'], stdout=subprocess.PIPE,
       check=True)
    disk_size_gb = int(gsutil_ls_result.stdout.decode(
        'utf-8').rstrip().split('\n')[-1].split("'")[1])

    if disk_size_gb+gb_to_add > MAX_SIZE_GB:
        raise ValueError(
            f'adding {gb_to_add}G to an already {disk_size_gb}G big disk '
            f'would exceed the max size of {MAX_SIZE_GB}G')

    # resize the google disk
    subprocess.run([
        f'yes|gcloud compute disks resize {DISK_NAME} --size '
        f'{disk_size_gb+gb_to_add} --zone={ZONE}'], check=True, shell=True)

    # resize the file system
    subprocess.run(['resize2fs', DEVICE_NAME], check=True)

    return 'success', 200


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='disk resize service')
    parser.add_argument(
        '--app_port', type=int, required=True,
        help='port to respond to status queries')
    parser.add_argument(
        '--disk_name', type=str, required=True, help='name of google disk')
    parser.add_argument(
        '--device_name', type=str, required=True, help=(
            'name of disk device on the OS'))
    parser.add_argument(
        '--zone', type=str, required=True,
        help='zone the disk is in eg. us-west1-b')
    parser.add_argument(
        '--max_size_gb', type=int, required=True, help=(
            'maximum allowed size of the disk in integer GB'))

    args = parser.parse_args()

    MAX_SIZE_GB = args.max_size_gb
    DEVICE_NAME = args.device_name
    DISK_NAME = args.disk_name
    ZONE = args.zone

    APP.run(
        host='0.0.0.0',
        port=args.app_port)
