> Historical initial-build report (v0.1). Current incremental verification is in docs/DEPLOYMENT_NOTES_v0.2.md and evidence/v0.2-*.

# Build 0.1 — verification and release status

Prepared 19 October 2026. Status: runnable local first slice, not production or complete client scope.

## Completed checks

- Read the actual PRD v0.2 DOCX text before implementation.
- Locked dependency resolution: Django 5.2.18 and WhiteNoise 6.12.0; `uv.lock` included.
- Fresh local setup executed: migrations, database cache table, static-file collection.
- Source ZIP was CRC-checked, extracted separately, and set up from scratch; the extracted copy passed all 25 tests, system check and migration-drift check. Python ZIP extraction dropped executable bits; documented chmod restored them before setup.
- `manage.py makemigrations --check --dry-run`: **No changes detected**.
- `manage.py check`: **No issues**.
- Django test suite: **25 tests passed**, in an isolated test database.
- Browser smoke: **7 checks passed** using a local server, normal SQLite/cache backend and Chromium. Disposable random credentials and fictional data only.
- Desktop overview and mobile employee-entry screenshots visually inspected; no clipped main forms observed.
- `pip-audit -r requirements.txt --disable-pip --no-deps --format json`: no known vulnerabilities reported for the pinned runtime dependencies. This is a database-backed dependency check, not a penetration test; see `evidence/dependency-audit.json`.

## What the automated suite covers

Login protection on business routes; admin employee create/edit/reopen; currency normalisation; decimal salary persistence; invalid salary/date/currency/assignee and missing-field rejection; operator salary suppression and route denial; allocation save/edit; CSRF rejection; password hashing; login/logout behaviour; bad credentials; login throttle counters; unsafe redirect rejection; HTML escaping; unimplemented-module labels; private response/security headers; disabled account; absent deletion route.

The browser smoke signs in through the form, saves/reloads staff salary/joining details, saves/reloads a work allocation, checks the Maintenance pending screen, checks mobile overview/form width, verifies operator HTML omits salary and employee editing returns 403, and observes no page errors. This is Chromium mobile emulation, **not physical Android acceptance**.

See `evidence/unit-tests.txt` and `evidence/browser-smoke.json` for captured output. Static collection happened after the first unit-test run; its harmless initial missing-static-directory warning was not an application failure.

## Security controls present

Django PBKDF2 password hashes, server sessions, CSRF protection, server-side role checks, server validation/ORM, template escaping, restrictive no-script Content Security Policy, no-store private pages, clickjacking protection and secure-cookie/HTTPS defaults outside development. Minimal write-audit events do not record salary values or passwords. No production credential or real person record is included.

Login throttling is a basic database-cache counter keyed on hashed IP and username, 10 failed attempts per 15-minute window. Cache counter increments are not an assurance of atomic distributed rate limiting; edge/service-level limiting and concurrency tests remain a production gate. IP handling deliberately uses REMOTE_ADDR and does not trust arbitrary forwarded headers.

`check --deploy` ran with production defaults and a random strong secret. It reported **2 warnings**: W005 HSTS include-subdomains and W021 HSTS preload. Both are intentionally unset until the actual domain/TLS ownership is confirmed. No production deployment or domain configuration was tested.

## Not verified / not complete

- CRM, Maintenance and Field Tracking implementation; actual assignment receipt/completion and any staff accounts.
- Client-approved role matrix, full employee fields, currency/period, retention and main/backup identity/recovery.
- Activation email, email delivery, third-party integrations or messaging.
- Actual hosting/TLS/proxy/database choice and Internet accessibility.
- Real laptop/Android browser, accessibility audit, load/concurrent edits, penetration test, backup/restore or disaster recovery.
- Multi-organisation tenancy. This is one company workspace; all authorised operators see all allocations. Do not share it among unrelated clients.
- Database/disk encryption. SQLite contains plaintext application data; file access and encrypted host storage/backup must be established before real salaries.
- Concurrent changes use last-write-wins; optimistic conflict handling has not been implemented.
- No production WSGI server deployment configuration. Development runserver is local only.

## Release gate before live staff data

1. Resolve the required business journeys and fields; implement/test CRM and Maintenance or obtain explicit accepted deferral, not silent exclusion.
2. Approve roles, main/backup accounts and onboarding route; provision actual accounts securely.
3. Select and validate staging/production database, host, HTTPS/proxy, secret handling, backups and restoration.
4. Test actual critical flows on client devices with fictional data; fix blockers and assess security/privilege boundaries and concurrency.
5. Provide matching full instructions/training, have the client review the identified release and record acceptance/remaining obligations.

No external deployment, signup, Git push, communication or paid commitment occurred. October 26, 17:00 IST remains a target, not a verified completion commitment.
