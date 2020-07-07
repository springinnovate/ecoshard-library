#!/bin/bash
export FLASK_APP=stac_api
flask db migrate
flask db upgrade
