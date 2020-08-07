#!/bin/bash
set -a
source stac_envs &&
    docker-compose down --remove-orphans $@
