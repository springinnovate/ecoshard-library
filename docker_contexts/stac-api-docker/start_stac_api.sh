#!/bin/bash -x
# Authenticate the gcloud SDK so it can read from buckets
/usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=${BUCKET_READ_SERVICE_ACCOUNT_KEYFILE}

touch config.py
echo "GEOSERVER_MANAGER_HOST = '${GEOSERVER_MANAGER_HOST}'" >> config.py
echo "SECRET_KEY = '${API_FLASK_SECRET_KEY}'" >> config.py
echo "SQLALCHEMY_DATABASE_URI = '${SQLALCHEMY_DATABASE_URI}" >> config.py
waitress-serve --listen=0.0.0.0:${API_HOST_PORT} --call stac_api:create_app 2>&1
