#!/bin/bash
# first authenticate gsutil
/usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=${DISK_RESIZE_SERVICE_ACCOUNT_KEYFILE}
# launch the service
python ./expand_drive_service.py $@
