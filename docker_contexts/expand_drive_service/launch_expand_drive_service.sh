#!/bin/bash
# first authenticate gsutil
/usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=/run/secrets/disk_resize_service_account_key
# launch the service
python ./expand_drive_service.py $@
