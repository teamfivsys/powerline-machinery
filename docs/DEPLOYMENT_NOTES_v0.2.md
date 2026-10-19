> v0.3 note: production configuration guidance below remains applicable. CRM/Maintenance and foreground location were added after this historical report. Follow OPERATING_GUIDE_v0.3.md for current permissions, purge_locations cleanup, location-free snapshots and real-device/privacy limits.

# Powerline Machinery — security & deployment preparation v0.2

19 October 2026. Incremental extension of the local v0.1 application, not a restart.
Original workspace `/home/user/workspace/powerline-fresh` is unchanged; working incremental source is `/home/user/workspace/powerline-v0.2`.

## What changed

- Added `config.production`: refuses debug mode, a weak or missing secret, missing/wildcard host configuration, non-HTTPS trusted CSRF origins, and relative/in-source database paths. Uses explicit private persistent SQLite storage; no hosting/database platform is presumed.
- Added a locked Gunicorn dependency and loopback-only, single-worker reference start script. No default account, deployment secret or public service was created.
- Fixed private-response caching on logout and anonymous redirects: all dynamic responses now use `Cache-Control: no-store, private`. Static assets retain ordinary caching.
- Added 28 tests to the original 25. They cover staff-flag versus administrator access, salary exposure on allocation object pages, anonymous/direct-object writes, forged allocation fields, CSRF, missing objects, session rotation, other-session invalidation after password change, disabled accounts, throttling, production guardrails and safe SQLite recovery.
- Added a SQLite backup and restore-to-new-file tool. It uses SQLite's online backup API, runs integrity/schema checks, creates mode-600 files in a private directory, and refuses overwrite, same-file destinations and destination symlinks. It never replaces the active database.
- Added an executable loopback-only production rehearsal: real Gunicorn, self-signed local TLS proxy with sanitized scheme headers, production cookies/CSRF/host validation, collected static assets and restart against a restored database.

## Verified results

- All 53 automated tests passed on Linux / CPython 3.14.7 / Django 5.2.18.
- All 10 production/recovery rehearsal checks passed. The restored database retained 2 fictional accounts, 1 fictional employee and 1 fictional allocation; login and both lists worked after WSGI restart. Seven table counts and integrity checks matched.
- Production deployment checks had no errors. W005 and W021 remain deliberately: subdomain HSTS and preload require a real domain/TLS ownership decision. Do not enable blindly to make a warning disappear.
- Locked runtime dependency audit reported no known vulnerabilities at this check. This is not a penetration test or a future vulnerability guarantee.
- The original seven v0.1 browser checks remain historical evidence. No additional physical-Android test or full Chromium replay is claimed in v0.2. Current production rehearsal uses real HTTP/TLS requests to the running service.

## Repeat locally

Use fictional data only until real release approval. From the extracted project:

```bash
uv sync --frozen
# A random temporary key for automated tests only; not a deployment secret.
export DJANGO_SECRET_KEY="$(uv run --frozen python -c 'import secrets;print(secrets.token_urlsafe(64))')"
uv run --frozen python manage.py test --settings=config.test_settings --verbosity=2
uv run --frozen python scripts/rehearse_production.py
```

The rehearsal needs `openssl` and Linux. It binds ephemeral ports only on loopback, uses a temporary private directory, generates disposable credentials/certificate, stops both servers and removes the database/certificate on exit. It never reads the development `.local` database. The test-only proxy is not a deployable reverse proxy.

## Reference deployment preparation — not a hosting decision

1. Choose host, actual hostname, HTTPS/TLS boundary, persistent private storage, operating jurisdiction, backup destination/retention and operator accounts. Confirm the permission matrix before provisioning client users. Do not expose regular operators as employee self-service accounts: they currently share allocation access.
2. On the selected host, install from the locked source. Provision a strong generated secret in the host's protected environment/secret manager. Keep it stable and backed up securely; changing it invalidates sessions. Do not place it in source, documentation or a shell command saved in history.
3. Set these environment variables in that protected service configuration:
   - `DJANGO_SETTINGS_MODULE=config.production`
   - `DJANGO_DEBUG=0`
   - `DJANGO_SECRET_KEY`: at least 50 unpredictable characters (strong generator).
   - `DJANGO_ALLOWED_HOSTS`: exact actual hostnames, comma-separated; no schemes, ports or `*`.
   - `DJANGO_DB_PATH`: absolute persistent private file outside application/public directories. Protect the parent directory with mode 700, restrict the service identity, and ensure disk encryption/backup encryption are suitable for salary data. Production settings do not configure storage encryption for you.
   - `DJANGO_CSRF_TRUSTED_ORIGINS`: leave empty unless needed; if set, explicit actual HTTPS origins only.
   - `DJANGO_TRUST_HTTPS_PROXY=1` only when the chosen TLS proxy overwrites the incoming `X-Forwarded-Proto` header and the WSGI port is inaccessible to untrusted clients. Otherwise leave 0 and establish the actual HTTPS scheme through a trusted server boundary.
4. In that same protected environment, run:

```bash
uv sync --frozen --no-dev
uv run --frozen --no-dev python manage.py migrate --noinput
uv run --frozen --no-dev python manage.py createcachetable
uv run --frozen --no-dev python manage.py collectstatic --noinput
uv run --frozen --no-dev python manage.py check --deploy --fail-level ERROR
uv run --frozen --no-dev python manage.py createsuperuser
bash scripts/start-production.sh
```

The reference start script binds Gunicorn only to `127.0.0.1:8000`, one worker, no request access logs. The real host must provide service supervision, trusted HTTPS proxy, firewall/private upstream, log scrubbing/retention, resource limits and monitoring. Do not point a public listener at Django's development server.

The database cache throttles by username and `REMOTE_ADDR`. With a reverse proxy, `REMOTE_ADDR` may be the proxy address, causing shared-IP lockouts. Do not trust arbitrary forwarded client-IP headers as a shortcut; validate a provider-specific trusted client-IP/rate-limit design in staging. The local rehearsal does not establish real-client-IP handling or resistance to distributed attacks.

## SQLite backup and safe recovery

The tool is SQLite-only. It does not migrate to PostgreSQL and does not back up source, external files or secrets. It includes all database records, account hashes, sessions, salaries and cache entries; treat backups as sensitive and encrypt before off-host transfer. No off-host transfer is performed by the tool.

With existing authorized paths substituted, prepare a private backup directory outside the application tree (`mkdir -m 700 /private/backup-directory`), then:

```bash
uv run --frozen --no-dev python scripts/sqlite_snapshot.py backup \
  /private/persistent/data.sqlite3 /private/backup-directory/snapshot-unique.sqlite3
```

Use a new filename each time. The command refuses to overwrite anything. Choose the actual directory first: `/private/...` here is a placeholder, not a created or recommended host path. Take a snapshot before migrations. Schedule backup and expiry/retention on the actual host; no scheduled backups exist yet.

For recovery, first stop every app instance/writer and retain the existing database and SQLite sidecars. Then restore into a NEW path, never over the live file:

```bash
uv run --frozen --no-dev python scripts/sqlite_snapshot.py restore-new \
  /private/backup-directory/snapshot-unique.sqlite3 /private/persistent/recovered-new.sqlite3
```

Check integrity/counts returned, point the stopped service's `DJANGO_DB_PATH` at the new file, run `manage.py check`, and restart the matching source release. Verify admin login, employee/allocation records and operator restrictions before allowing writes. Do not apply later migrations to an older backup without a reviewed upgrade plan. Keep the old files until recovery is accepted. Avoid copying a live SQLite file with `cp`; this can miss active WAL content.

A snapshot restores existing sessions too. For security incidents or lost backups, revoke sessions after recovery through `manage.py shell` by deleting Django `Session` rows; this signs everyone out. Operational recovery did not perform such a revocation against any real account.

## Remaining release blockers

- Actual CRM and Maintenance workflows and whether Maintenance is distinct from Field Tracking. No new module or role was invented to fill those gaps.
- Client approval of scope/acceptance checks and the provisional administrator/operator rights. Regular operators can view/edit all work allocations; they are not limited to their own employee records. Employee self-service and notifications are still absent.
- Hosting/domain/HTTPS/storage choice, actual production configuration, account recovery/backup-email flow, real device checks, concurrency/load assessment, independent security review and encrypted off-host backup recovery.
- Client-ready module implementation, full end-to-end acceptance, actual live deployment, training and handover.

October 26 at 17:00 IST remains the target, not a guarantee. These local checks improve readiness; they do not make an incomplete application ready for client staff or certify production security.
