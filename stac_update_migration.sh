#!/bin/bash
set -a
source stac_envs &&
    docker-compose -f docker-compose.yml -f migrate.yml up db stac_manager --build --remove-orphans