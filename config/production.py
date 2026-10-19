"""Explicit production profile: requires real host/secret/storage choices, never defaults."""
import ipaddress
import re
from .settings import *

if DEBUG:
    raise ImproperlyConfigured("Production forbids DJANGO_DEBUG=1.")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Production requires a strong random DJANGO_SECRET_KEY of at least 50 characters.")
raw_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production requires exact DJANGO_ALLOWED_HOSTS.")
for host in ALLOWED_HOSTS:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host) or ".." in host:
            raise ImproperlyConfigured("Production hosts must be exact hostnames or IP addresses; no wildcards, schemes or ports.")
if any(not x.startswith("https://") or "*" in x for x in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Production trusted CSRF origins must be explicit HTTPS origins.")
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    path = Path(os.environ.get("DJANGO_DB_PATH", ""))
    if not path.is_absolute():
        raise ImproperlyConfigured("Production requires an absolute private persistent DJANGO_DB_PATH.")
    if path.resolve().is_relative_to(BASE_DIR.resolve()):
        raise ImproperlyConfigured("Production database must be outside the application/source/static directory.")
# Opt in only behind a loopback/private upstream whose proxy overwrites this header.
proxy_mode = os.environ.get("DJANGO_TRUST_HTTPS_PROXY", "0")
if proxy_mode not in ("0", "1"):
    raise ImproperlyConfigured("DJANGO_TRUST_HTTPS_PROXY must be 0 or 1.")
if proxy_mode == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
SESSION_COOKIE_NAME = "powerline_sessionid"
CSRF_COOKIE_NAME = "powerline_csrftoken"
