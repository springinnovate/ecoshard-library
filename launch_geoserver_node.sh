#!/bin/bash
set -a
source stac_envs
docker-compose -f compose-geoserver-node.yml up --remove-orphans --build
