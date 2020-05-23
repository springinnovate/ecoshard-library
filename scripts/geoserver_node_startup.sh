#!/bin/bash

# Startup script for GeoServer Node

# create new disk from snapshot, name it geoserver-data-disk-*instance name*
gcloud compute disks create `hostname`-geoserver-data --source-snapshot=geoserver-data-snapshot --zone=us-west1-b
# attach new disk to *instance name*
gcloud compute instances attach-disk `hostname` --disk=`hostname`-geoserver-data --zone=us-west1-b
# set to auto delete
gcloud compute instances set-disk-auto-delete `hostname` --disk=`hostname`-geoserver-data --zone=us-west1-b
# create dir at /mnt/geoserver_data
mkdir -p /mnt/geoserver_data
# mount at /mnt/geoserver_data
mount /dev/sdb /mnt/geoserver_data

# pull latest container and start it
docker pull us.gcr.io/salo-api/stac-geoserver-container:latest
# geoserver instance, map port 8080 and assume 15gb total ram -- give 12gb to JVM
docker run --rm -d -it -v /mnt/geoserver_data/:/usr/local/geoserver/data_dir -p 8080:8080 us.gcr.io/salo-api/stac-geoserver-container:latest api.salo.ai 8888 maps.salo.ai 8080 12g
