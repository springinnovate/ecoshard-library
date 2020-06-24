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

    docker run --rm -d -it -v /mnt/geoserver_data/:/usr/local/geoserver/data_dir -p 8888:8888 --name geoserver_node us.gcr.io/salo-api/stac-geoserver-container:latest API_HOST GEOSERVER_HOST:GEOSERVER_PORT MAX_RAM AUTH_DATABASE_PASSWORD AUTH_DATABASE_HOST


Authentication
---------------

This Flask application makes use of an imported blueprint for authentication
purposes. In addition to providing API endpoints for creating users and
authenticating, it also includes a decorator(`@jwt_required`) for endpoints that require
authenticauthentication for access. An example:

    @app.route('/a/protected/endpoint')
    @jwt_required
    def protected_endpoint():
        ...

The authentication blueprint uses a `users` table is managed by [Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/). When changes are made to the database schema, [use the flask db commands](https://flask-migrate.readthedocs.io/en/latest/#example) to create new migrations (`flask db migrate -m "What was changed"`), and apply them in production (`flask db upgrade`).
