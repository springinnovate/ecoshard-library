#!/usr/bin/env sh
set -eu

envsubst '${NGINX_HOST}' < /etc/nginx/conf.d/conf_file.conf.template > /etc/nginx/conf.d/conf_file.conf

exec "$@"
