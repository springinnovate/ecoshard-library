#!/bin/bash
set -a
source stac_envs &&
    docker-compose restart $@
