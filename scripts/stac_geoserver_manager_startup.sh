#!/bin/bash

# Startup script for STAC GeoServer API Manager

# attach the existing geosever-data-disk to *instance name*
gcloud compute instances attach-disk `hostname` --disk=geoserver-data-disk --zone=us-west1-b
# create dir at /mnt/geoserver_data
mkdir -p /mnt/geoserver_data
# mount at /mnt/geoserver_data
mount /dev/sdb /mnt/geoserver_data

cd /home/rich/stac-geoserver-api/
nohup python3 expand_drive_service.py --app_port 8080 --disk_name geoserver-data-disk --device_name /dev/sdb --zone us-west1-b --max_size 256 --project salo-api > expand_drive_service_log.txt &

# pull latest container and start it
docker pull us.gcr.io/salo-api/stac-geoserver-container:latest
# api manager instance only map port 8888, geoserver not used for production -- give 4gb to JVM
docker run --rm -d -it -v /mnt/geoserver_data/:/usr/local/geoserver/data_dir -p 8888:8888  us.gcr.io/salo-api/stac-geoserver-container:latest api.salo.ai 8888 maps.salo.ai 8080 4g
