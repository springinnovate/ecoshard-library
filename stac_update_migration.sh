#!/bin/bash
set -a
source stac_envs &&
    docker-compose -f docker-compose.yml -f migrate.yml up --build --remove-orphans db stac_manager
