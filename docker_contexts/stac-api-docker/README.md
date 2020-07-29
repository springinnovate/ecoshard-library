Geoserver
=========

Development
-----------

Tests can be run within the docker container, using pytest:

    pytest

    # run with code coverage
    pytest --cov stac_api
    pytest --cov-report=html --cov stac_api


Authentication
---------------

This Flask application makes use of an imported blueprint for authentication
purposes. In addition to providing API endpoints for creating users and
authenticating, it also includes a decorator(`@jwt_required`) for endpoints that require
authenticauthentication for access. An example:

    @app.route('/a/protected/endpoint')
    @jwt_required()
    def protected_endpoint():
        ...

The authentication blueprint uses a `users` table is managed by [Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/). When changes are made to the database schema, [use the flask db commands](https://flask-migrate.readthedocs.io/en/latest/#example) to create new migrations (`flask db migrate -m "What was changed"`), and apply them in production (`flask db upgrade`).
