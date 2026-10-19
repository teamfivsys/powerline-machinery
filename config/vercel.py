"""Explicit Vercel production profile. No ephemeral-filesystem database fallback."""
from .production import *
if os.environ.get('VERCEL') != '1':
    raise ImproperlyConfigured('config.vercel requires the Vercel environment marker. For local rehearsal set VERCEL=1 explicitly.')
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Vercel requires an external PostgreSQL DATABASE_URL; SQLite is not supported on ephemeral storage.')
# Vercel terminates TLS and supplies x-forwarded-proto. Never expose this profile
# behind a direct public WSGI server that accepts client-supplied forwarding headers.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = False
