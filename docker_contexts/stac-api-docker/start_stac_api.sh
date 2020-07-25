#!/bin/bash -x
# Authenticate the gcloud SDK so it can read from buckets
/usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=${BUCKET_READ_SERVICE_ACCOUNT_KEYFILE}

echo "upgrade db"
export FLASK_INITALIZE_ONLY=1
echo "value of flask $FLASK_INITALIZE_ONLY"
flask db upgrade

echo "launching app"
export FLASK_INITALIZE_ONLY=0
waitress-serve --expose-tracebacks --listen=0.0.0.0:8888 --call stac_api:create_app 2>&1
