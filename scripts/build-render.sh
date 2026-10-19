#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DJANGO_SETTINGS_MODULE=config.render
python -m pip install --require-hashes -r requirements.txt
python manage.py check --deploy --fail-level ERROR
python manage.py collectstatic --noinput
# No migrations, admin creation, seeded data, or external scheduler in builds.
