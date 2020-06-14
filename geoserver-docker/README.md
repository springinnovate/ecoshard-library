Geoserver
=========

Development
-----------

One can run the flask app for the geoserver-docker image, configured for
development by passing `FLASK_ENV` environmental variable, and mounting the
geoserver-docker directory into the image:

    # build
    docker build geoserver-docker -t us.gcr.io/salo-api/stac-geoserver-container:latest

    # run
    docker run --rm -it -v $PWD/geoserver_data/:/usr/local/geoserver/data_dir -v $PWD/geoserver-docker:/usr/local/geoserver/bin:delegated -p 8888:8888 -e FLASK_APP=stac_api:create_app -e FLASK_ENV=development --entrypoint /usr/bin/bash us.gcr.io/salo-api/stac-geoserver-container:latest

    # a bash prompt is presented:
    cd bin
    flask run --host 0.0.0.0 -p 8888

    # visit http://127.0.0.1:8888

Tests can be run within the docker container, using pytest:

    pytest

    # run with code coverage
    pytest --cov stac_api
    pytest --cov-report=html --cov stac_api


Production
----------

To build the docker image:

    docker build geoserver-docker -t us.gcr.io/salo-api/stac-geoserver-container:latest

The docker image uses `start_geoserver.sh` as the entrypoint, which takes
several configuration paramaters (illustrated in ALL CAPS here):

    docker run --rm -d -it -v /mnt/geoserver_data/:/usr/local/geoserver/data_dir -p 8888:8888 --name geoserver_node us.gcr.io/salo-api/stac-geoserver-container:latest API_HOST API_PORT GEOSERVER_HOST GEOSERVER_PORT AUTH_DATABASE_PASSWORD AUTH_DATABASE_HOST
