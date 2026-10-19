#!/usr/bin/env bash
# Local development only; never source this file in a production service.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local
chmod 700 .local
if [ ! -f .local/secret.key ]; then
  uv run --frozen python -c 'import secrets; print(secrets.token_urlsafe(64))' > .local/secret.key
  chmod 600 .local/secret.key
fi
export DJANGO_SECRET_KEY="$(cat .local/secret.key)"
unset DATABASE_URL VERCEL
export DJANGO_SETTINGS_MODULE=config.settings
export DJANGO_DEBUG=1
export DJANGO_DB_PATH="$PWD/.local/data.sqlite3"
exec uv run --frozen python manage.py "$@"
