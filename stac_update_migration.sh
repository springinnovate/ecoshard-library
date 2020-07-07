#!/bin/bash
set -a
source stac_envs &&
    docker-compose build
    docker run --rm -it --entrypoint ./update_migration.sh -v `pwd`/docker_contexts/stac-api-docker:/usr/local/stac_manager/ stac_manager
