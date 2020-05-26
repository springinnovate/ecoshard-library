#!/bin/bash

# Startup script for GeoServer Node


# create dir at /mnt/geoserver_data
mkdir -p /mnt/geoserver_data
# mount at /mnt/geoserver_data
mount /dev/sdb /mnt/geoserver_data

pushd /home/rich/stac-geoserver-api/
git pull
python3 resize_and_flush_service.py --initalize --app_port 8081 --disk_pattern geoserver-data-disk* --mount_point /mnt/geoserver_data > /home/rich/resize_and_flush_service_log.txt

# pull latest container and start it
docker pull us.gcr.io/salo-api/stac-geoserver-container:latest
# geoserver instance, map port 8080 and assume 15gb total ram -- give 12gb to JVM
docker run --rm -d -it -v /mnt/geoserver_data/:/usr/local/geoserver/data_dir -p 8080:8080 us.gcr.io/salo-api/stac-geoserver-container:latest api.salo.ai 8888 maps.salo.ai 8080 12g

nohup python3 stac-geoserver-api/resize_and_flush_service.py --app_port 8081 --disk_pattern geoserver-data-disk* --mount_point /mnt/geoserver_data > /home/rich/resize_and_flush_service_log.txt &
popd
