#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
uv sync --frozen
./scripts/manage.sh migrate --noinput
./scripts/manage.sh createcachetable
./scripts/manage.sh collectstatic --noinput
printf '\nNext: ./scripts/manage.sh createsuperuser\nThen: ./scripts/manage.sh runserver 127.0.0.1:8000\nUse fictional data only. This setup intentionally uses development mode on loopback.\n'
