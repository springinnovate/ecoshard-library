#!/bin/bash -x
# Authenticate the gcloud SDK so it can read from buckets
/usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=${BUCKET_READ_SERVICE_ACCOUNT_KEYFILE}

echo "upgrade db"
set FLASK_INITALIZE_ONLY=1
flask db upgrade

echo "launching app"
set FLASK_INITALIZE_ONLY=0
waitress-serve --expose-tracebacks --listen=0.0.0.0:8888 --call stac_api:create_app 2>&1
