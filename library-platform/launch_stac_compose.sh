#!/bin/bash
set -a
source stac_envs &&
    docker-compose up --remove-orphans --build $@
