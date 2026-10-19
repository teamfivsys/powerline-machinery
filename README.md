# v0.5 free demonstration preparation

See docs/FREE_DEMO_v0.5.md before using render.yaml. Fictional data only; not a production release. Prior instructions remain below.

# Powerline Machinery — standalone local build v0.4

A runnable Django system for the owner's accepted initial customer-enquiry, maintenance and foreground field-update flows. This is local development progress, not a finished client release. October 26, 2026 at 17:00 IST remains a target, not a guarantee or client acceptance.

## Implemented

- Server-side login, POST logout, password changes and login throttling.
- Administrator-only employee creation/editing: joining date, salary, explicit currency and pay basis; no payroll calculations.
- Existing persistent work allocation (regular operators still share allocation access under the provisional v0.1 model).
- Administrator-only CRM: spare-parts/service enquiries, customer/contact, follow-up notes, Open/In progress/Closed; outcome required to close, reopen/edit supported.
- Administrator-managed Maintenance: customer, optional service-enquiry link, machine, fault, existing-employee technician assignment, progress/work done; work done required to complete.
- Explicit login-to-employee mapping: technicians see and update only their own assigned maintenance jobs, not CRM, dispatch, others' service records or salary.
- Opt-in foreground browser GPS per assigned job: Start/Stop, visible sharing state, permission/error handling, latest timestamp/accuracy, stale/expired labels; no trail. Dispatcher view is administrator-only and manually refreshed.
- SQLite local fallback plus TLS PostgreSQL support, shared database sessions, versioned migrations and fail-closed Vercel production configuration.
- 135 automated tests on SQLite and local TLS PostgreSQL, 14 Chromium workflow checks, dispatcher-expiry checks and local production/recovery rehearsals; see evidence/v0.4/. Prior version evidence is historical.

## Start locally

Prerequisites: Python 3.12+ and `uv`. Extract the archive, open its `powerline-v0.4` folder and run:

```bash
chmod +x scripts/*.sh
./scripts/setup-local.sh
./scripts/manage.sh createsuperuser
./scripts/manage.sh runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/`. No default password is supplied: enter it privately when prompted. Use fictional data only. Keep this development server bound to loopback; do not expose it to the internet.

The helper creates `.local/secret.key` (private), `.local/data.sqlite3`, cache table, migrations and collected static assets. These runtime files are excluded from the source package. Resume with the same runserver command; do not delete `.local` unless deliberately discarding local data/accounts. Ctrl-C stops the server.

## Technician setup

Create an employee as administrator, obtain its numeric ID from the employee edit URL (`/employees/ID/edit/`), then in a second local terminal:

```bash
./scripts/manage.sh create_technician technician_name EMPLOYEE_ID
```

The command privately prompts for a password and explicitly maps that login to the employee. No administrator rights or notification is created. Alternatively, for an existing active non-administrator login:

```bash
./scripts/manage.sh link_technician existing_username EMPLOYEE_ID
./scripts/manage.sh unlink_technician existing_username
```

One login maps to one employee and vice versa. Unlinking clears sharing and assigned-service access but leaves that login's existing operator permissions unchanged. `./scripts/manage.sh changepassword username` privately changes a password. Regular operator provisioning remains `create_operator username`.

Assign a service job to that employee. The technician then opens My service jobs, records progress/work done and can optionally share location while the page remains foregrounded. Administrators open Live job locations and refresh to see the latest voluntarily shared position.

## Scope and privacy limits

Minimal fields/statuses are engineering choices implementing the accepted broad flows, not a quotation-derived complete feature agreement. No inventory movements, parts stock, quotations, prices, taxes, invoices, payments, payroll, automated notifications or route history is implemented.

Location starts only after an explicit tap and browser permission. Browsers normally require HTTPS (localhost is the development exception). Hiding/leaving the page stops its watch and attempts a server stop. A lost network can prevent immediate server deletion; the previous position disappears from a newly fetched dispatcher view at expiry within two minutes, ; v0.4 also removes expired coordinate cards from an already-rendered dispatcher while its JavaScript runs and rechecks when the tab returns. Samples are stale after 30 seconds. There is no background tracking guarantee, location cannot prove attendance, and browser data can be spoofed. No real person/location was collected in testing.

Expired rows are purged on tracking/dispatcher requests; for timely database cleanup on a selected host schedule `manage.py purge_locations` every minute. This is not scheduled by this source package. No location history is maintained in the model. The included snapshot tool strips location sessions and vacuums the snapshot; it does not erase arbitrary host backups/logs or forensic remnants in live SQLite. A real deployment needs storage encryption, request/log review and an agreed retention/privacy policy.

## Tests and evidence

```bash
./scripts/manage.sh test --settings=config.test_settings --verbosity=2
./scripts/manage.sh makemigrations --check --dry-run
uv run --frozen playwright install chromium
uv run --frozen python scripts/browser_smoke.py
uv run --frozen python scripts/rehearse_production.py
```

Browser/recovery scripts use isolated temporary databases, generated disposable credentials and fictional records; geolocation is simulated. Browser script needs free port 8765 and writes artifacts locally. Recovery rehearsal requires OpenSSL and uses a local self-signed TLS proxy with Gunicorn; it makes no public deployment.

## Before release

See `docs/OPERATING_GUIDE_v0.3.md`, `docs/REQUIREMENTS.md`, `BUILD_REPORT.md` and evidence/v0.3-* for actual scope and verification. The v0.1/v0.2/v0.3 reports are historical. Current hosting and PostgreSQL preparation, official plan/pricing caveats, exact release steps and remaining decisions are in `docs/VERCEL_PREPARATION_v0.4.md`. Read it before any publication or paid service.

Still required: agreed role matrix (operators currently share generic work allocations), actual Android/HTTPS permission and lifecycle tests, hosting/database/TLS selection, off-host encrypted backup/restore, load/security review, final client acceptance and handover. Two deliberate HSTS subdomain/preload warnings remain until domain/TLS ownership is settled. GitHub-to-Vercel was requested for later; nothing has been pushed or deployed. A filesystem SQLite database is not suitable for Vercel's ephemeral serverless filesystem: v0.4 supplies an external PostgreSQL adapter and Vercel profile, locally rehearsed only. Actual provider setup, pooler/TLS validation, Vercel cloud build and release/recovery tests remain. The owner's existing Vercel plan has not been inspected; a suitable existing paid team may suffice. Hobby is non-commercial only. No new subscription is assumed.

No paid service, external account, repository push or message was created.
