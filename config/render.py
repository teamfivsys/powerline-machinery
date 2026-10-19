"""Render demonstration deployment: no ephemeral SQLite fallback."""
from .production import *
if os.environ.get('RENDER') not in ('true', '1'):
    raise ImproperlyConfigured('config.render requires the Render environment marker.')
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Render requires external TLS PostgreSQL; SQLite on ephemeral disk is forbidden.')
# Only use behind Render's managed ingress, which sets x-forwarded-proto.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = False
