#!/usr/bin/env sh
set -eu

envsubst '${NGINX_HOST}' < /etc/nginx/conf.d/stac_manager.conf.template > /etc/nginx/conf.d/stac_manager.conf

exec "$@"
