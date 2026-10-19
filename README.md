# Powerline v0.6 local build

Read docs/HANDOVER_v0.6.md and BUILD_REPORT_v0.6.md first. This source includes first-use password replacement, verified-identity terminal recovery and local security fixes. It has not been pushed to GitHub or deployed. Fictional-data demo only; hosting and actual-device tests remain. Historical instructions below describe earlier builds; current limits and verified runs are in the v0.6 documents.

# Powerline Machinery — standalone local build v0.6

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
- 168 automated tests passed independently on SQLite and local TLS PostgreSQL, plus workflow, account-security, expiry and recovery checks. See BUILD_REPORT_v0.6.md and evidence/v0.6*.

## Start locally

Prerequisites: Python 3.12+ and `uv`. Extract the archive, open its `powerline-v0.6` folder and run:

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

One login maps to one employee and vice versa. Unlinking clears sharing and assigned-service access but leaves that login's existing operator permissions unchanged. Use `./scripts/manage.sh recover_account username --identity-verified` only after independently verifying the account holder. It privately collects a temporary replacement, invalidates old authenticated sessions, clears sharing and enforces password replacement at next sign-in. Regular operator provisioning remains `create_operator username`; both new-account commands now require first-use password replacement. No email is sent.

Assign a service job to that employee. The technician then opens My service jobs, records progress/work done and can optionally share location while the page remains foregrounded. Administrators open Live job locations and refresh to see the latest voluntarily shared position.

## Scope and privacy limits

Minimal fields/statuses are engineering choices implementing the accepted broad flows, not a quotation-derived complete feature agreement. No inventory movements, parts stock, quotations, prices, taxes, invoices, payments, payroll, automated notifications or route history is implemented.

Location starts only after an explicit tap and browser permission. Browsers normally require HTTPS (localhost is the development exception). Hiding/leaving the page stops its watch and attempts a server stop. A lost network can prevent immediate server deletion; the previous position disappears from a newly fetched dispatcher view at expiry within two minutes; the application also removes expired coordinate cards from an already-rendered dispatcher while its JavaScript runs and rechecks when the tab returns. Samples are stale after 30 seconds. There is no background tracking guarantee, location cannot prove attendance, and browser data can be spoofed. No real person/location was collected in testing.

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

Read `docs/HANDOVER_v0.6.md` for current release gates, `docs/REQUIREMENTS.md` for engineering scope and `BUILD_REPORT_v0.6.md` for actual evidence. Earlier version reports are historical.

Render Free plus external Neon Free remains a fictional-data demonstration candidate only. The prepared settings are in `docs/FREE_DEMO_v0.5.md`; actual hosted runtime, provider eligibility, commercial entitlement, persistence/TLS, cleanup and recovery remain unverified. No cloud cleanup schedule is installed. No provider signup, deployment or paid commitment occurred.

The owner’s inspected Vercel team uses Hobby, unsuitable for this commercial client deployment. Earlier Vercel preparation is retained as an alternative, not the selected free route.

Still required: final role matrix (regular operators share generic allocations), operational timezone, administrator/recovery identity process, privacy/retention, actual Android/HTTPS lifecycle testing, encrypted off-host recovery, security/load review and client acceptance. Foreground web GPS does not guarantee locked-phone/background tracking. No automatic activation/recovery email is configured. Two deliberate HSTS subdomain/preload warnings remain until domain/TLS ownership is settled.

The private GitHub repository contains the prior v0.5 commit `fcbf61d2645cb4e4bee2c16c4da86bb65858214f`. This v0.6 source has not been pushed. No external messages or real client records were used.
