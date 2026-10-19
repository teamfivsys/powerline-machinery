#!/usr/bin/env bash
# Reference loopback-only WSGI start. Not a hosting choice or internet deployment.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
export DJANGO_SETTINGS_MODULE=config.production
: "${DJANGO_SECRET_KEY:?Supply a strong secret via protected environment}"
: "${DJANGO_ALLOWED_HOSTS:?Supply exact hostnames}"
if [ -z "${DATABASE_URL:-}" ]; then
  : "${DJANGO_DB_PATH:?Supply an absolute private persistent database path or external PostgreSQL DATABASE_URL}"
fi
uv run --frozen --no-dev python manage.py check --deploy --fail-level ERROR
exec uv run --frozen --no-dev gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 1 --timeout 30 --access-logfile /dev/null --error-logfile - --forwarded-allow-ips ''
