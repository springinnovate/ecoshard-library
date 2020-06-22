#!/bin/bash -x
touch stac_api/config.py
echo "GEOSERVER_MANAGER_HOST = '${GEOSERVER_MANAGER_HOST}'" >> stac_api/config.py
echo "SECRET_KEY = '${SECRET_KEY}'" >> stac_api/config.py
echo "SQLALCHEMY_DATABASE_URI = '${SQLALCHEMY_DATABASE_URI}" >> stac_api/config.py
waitress-serve --listen=0.0.0.0:$2 --call stac_api:create_app 2>&1
