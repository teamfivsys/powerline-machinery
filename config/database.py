"""Strict, non-logging PostgreSQL URL configuration; never prints credentials."""
import os
import ssl
from urllib.parse import urlsplit, parse_qs, unquote
from django.core.exceptions import ImproperlyConfigured


def postgres_database(url, *, allow_local_insecure=False):
    try:
        parsed = urlsplit(url)
        query = parse_qs(parsed.query, strict_parsing=True)
        host = parsed.hostname
        port = parsed.port or 5432
        name = unquote(parsed.path.removeprefix('/'))
        if parsed.scheme not in ('postgres', 'postgresql') or not host or not name or '/' in name:
            raise ValueError
        if not parsed.username or parsed.password is None or parsed.fragment:
            raise ValueError
        if set(query) - {'sslmode', 'channel_binding'} or any(len(values) != 1 for values in query.values()):
            raise ValueError
        sslmode = query.get('sslmode', ['verify-full'])[0]
        local = host in ('localhost', '127.0.0.1', '::1')
        if sslmode not in ('require', 'verify-full') and not (allow_local_insecure and local and sslmode == 'disable'):
            raise ValueError
    except (ValueError, TypeError):
        raise ImproperlyConfigured('DATABASE_URL must be a PostgreSQL URL with credentials, a database name and TLS (sslmode=require or verify-full). Only sslmode and channel_binding are accepted as URL options.') from None
    options = {'sslmode': sslmode, 'connect_timeout': 5}
    binding = query.get('channel_binding', ['prefer'])[0]
    if binding not in ('prefer', 'require'):
        raise ImproperlyConfigured('channel_binding must be prefer or require.')
    options['channel_binding'] = binding
    ca = os.environ.get('DJANGO_DATABASE_SSLROOTCERT')
    if not ca and sslmode == 'verify-full':
        ca = ssl.get_default_verify_paths().cafile
    if ca:
        options['sslrootcert'] = ca
    return {'ENGINE': 'django.db.backends.postgresql', 'NAME': name,
            'USER': unquote(parsed.username), 'PASSWORD': unquote(parsed.password),
            'HOST': host, 'PORT': port, 'CONN_MAX_AGE': 0,
            'CONN_HEALTH_CHECKS': True, 'DISABLE_SERVER_SIDE_CURSORS': True, 'OPTIONS': options}
