#!/bin/bash -x
# Authenticate the gcloud SDK so it can read from buckets
/usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=/run/secrets/bucket_read_service_account_key

touch stac_api/config.py
echo "GEOSERVER_MANAGER_HOST = '${GEOSERVER_MANAGER_HOST}'" >> stac_api/config.py
echo "SECRET_KEY = '${API_FLASK_SECRET_KEY}'" >> stac_api/config.py
echo "SQLALCHEMY_DATABASE_URI = '${SQLALCHEMY_DATABASE_URI}" >> stac_api/config.py
waitress-serve --listen=0.0.0.0:${API_HOST_PORT} --call stac_api:create_app 2>&1
