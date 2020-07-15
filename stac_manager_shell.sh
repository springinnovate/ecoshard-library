#!/bin/bash
set -a
docker-compose -f stac_manager_shell.yml run --rm stac_manager_shell
