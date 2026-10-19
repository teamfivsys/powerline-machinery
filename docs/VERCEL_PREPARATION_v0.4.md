# Powerline v0.4 — deployment preparation

Prepared 19 October 2026. Local source and rehearsals only; no repository push, account creation, subscription or hosted deployment. October 26 at 17:00 IST remains the owner’s target, not a guarantee or client approval.

## Recommendation and account decision

Keep Django; a stack rewrite is unnecessary. Current official Vercel documentation supports Django WSGI/ASGI, explicit entrypoints and automatic static collection. Use an external managed PostgreSQL database; never put business data, sessions or uploads in the Vercel function filesystem.

First inspect the owner's existing Vercel team and billing plan. An existing active Pro or suitable Enterprise team may already cover the hosting requirement; no new subscription should be assumed. This build has not inspected the account plan or verified available budget/seat entitlements. Vercel Hobby is explicitly limited to non-commercial personal use and is not suitable for this commercial client project.

If no suitable paid plan exists, Pro currently has a USD 20/month platform fee, including one deploying seat and USD 20 usage credit. Extra deploying seats are USD 20/month each; usage, optional features and applicable taxes can add cost. These are provider prices checked 19 October, not an all-in quote or purchase approval. Set and verify spend controls before live use; read their actual pause/notification behavior. Do not start a trial with future charges as a workaround.

A concrete database candidate is Neon managed PostgreSQL. Use its pooled connection URL for the app, direct URL for migrations and backups, and align the Vercel function region with the database region. Neon documents Singapore; Vercel supports sin1. Singapore is a candidate, not an approved data-residency choice. Region availability can depend on the Neon organization. Do not assume Mumbai database availability or move employee/location data across borders without the owner's agreement.

For production, prefer a paid database plan with agreed restore retention, limits and support rather than assuming a free tier is enough. Neon's Launch currently has no monthly minimum; compute is USD 0.106/CU-hour and storage USD 0.35/GB-month, with other usage/restore charges possible. Free currently includes 100 CU-hours/project and 1 GB/project, but is resource-limited. A minute-by-minute cleanup query can keep the database awake: 0.25 CU continuously for 730 hours is 182.5 CU-hours, or approximately USD 19.35 in Launch compute alone, before storage/restore/transfer/taxes. This is a scenario, not a monthly quote. A free database could exhaust its 100 CU-hours under that pattern. No paid account or database was selected or created.

## What changed

- PostgreSQL URL configuration with TLS; verify-full by default, health checks, no persistent per-process connections, and server-side cursors disabled for transaction poolers.
- Vercel production profile fails closed if the database is missing, SQLite is selected, DEBUG is enabled, hosts are wildcarded or the signing secret is weak. Vercel-marked processes cannot use a development or generic production profile.
- WSGI/ASGI/manage entrypoints select the Vercel profile when VERCEL=1. Explicit production environment configuration is still required.
- Existing SQLite local development stays available. The local helper deliberately clears DATABASE_URL/VERCEL to avoid accidentally writing to a production database.
- Python 3.14 selection, locked dependencies, Vercel entrypoint/function configuration and deployment exclusions. Static collection does not run migrations.
- DB-backed sessions and existing database-backed login throttling survive independent app processes.
- Dispatcher hides expired coordinate cards without a refresh, and rechecks when the tab returns. It still needs refresh to fetch new positions.
- A bearer-authenticated, no-store cleanup endpoint is ready; it is not scheduled by the supplied configuration.

The existing HR records, salary restrictions, generic allocation, CRM, Maintenance, technician assignment and explicit foreground Start/Stop GPS are preserved. No new inventory, invoicing, payroll, notifications or background tracking rules were invented.

## Required configuration — securely, not in chat

Use `.env.vercel.example` as a reference only; it is not automatically loaded. Set separate Production and Preview values in Vercel's protected environment settings. Preview must use a separate non-production database and synthetic records.

| Variable | Required value |
| --- | --- |
| DJANGO_SETTINGS_MODULE | config.vercel |
| DJANGO_DEBUG | 0 |
| DJANGO_SECRET_KEY | Unique high-entropy secret, at least 50 characters |
| DJANGO_ALLOWED_HOSTS | Exact approved hosts, comma separated; no schemes/ports/wildcards |
| DJANGO_CSRF_TRUSTED_ORIGINS | Exact HTTPS origins for the same approved site |
| DATABASE_URL | Provider's pooled PostgreSQL URL with TLS |
| CRON_SECRET | Separate random secret of at least 32 characters; only for approved cleanup |
| DJANGO_DATABASE_SSLROOTCERT | Optional trusted provider CA path if needed |

URL-encode credentials. The parser accepts only sslmode and channel_binding query options. Prefer verify-full; require is accepted for provider-supported encrypted connections but does not promise full hostname identity verification. Never downgrade to disable/prefer in production. Do not commit env files, DB dumps, private keys or credentials. Rotate real values privately if exposed. Provider connection, certificate and network access still need testing against the actual selected service.

## Controlled release sequence — not executed

1. Confirm exact private GitHub repository/owner, Vercel team/project, existing paid plan and approval to push/deploy. Publication was deferred; this package does not change that.
2. Approve database provider/region, usage limits and restore retention; create separate preview and production databases only when authorized. Use least-privilege app and release roles where supported. Verify encryption, connection limits, logging and any IP/network restrictions on the chosen plan.
3. Configure secrets, exact hosts, function/database region and deployment protection. `vercel.json` intentionally contains neither a region choice nor a cron schedule. Add the agreed region in settings or configuration; otherwise Vercel's documented default is iad1, not Singapore.
4. With a direct database URL loaded privately into DATABASE_URL, VERCEL=1 and the other required settings, review the migration plan. Never run the local helper on the hosted database:

   `uv run --frozen --no-dev python scripts/release_database.py --confirm-host EXACT_DIRECT_HOST --confirm-database EXACT_DB_NAME`

   After a tested backup/recovery point and single-operator signoff, repeat the exact confirmed command with `--apply`. The script creates the shared throttle cache table. It does not publish. Do not run competing schema migrations or migrate on each request/build.
5. Create the first administrator via a private terminal `uv run --frozen --no-dev python manage.py createsuperuser` with the same protected production environment. Provision named technician/operator accounts with the documented mapping commands. No default password or automatic signup email exists. Revert DATABASE_URL to the pooled app URL in Vercel.
6. Connect/push the approved repository and import it into the selected Vercel project only after publication approval. Official Django zero-config handles WSGI and collectstatic; do not add a migration build command. Keep the app root at the folder containing manage.py. Vercel documentation lists CLI 50.38+ if CLI is used. Actual cloud build/bundle size and runtime behavior remain unverified.
7. Enable and verify cleanup only after the plan and privacy policy are agreed. On an appropriate Pro/Enterprise project, add `crons: [{path: /internal/cron/purge-locations/, schedule: '* * * * *'}]` as JSON with quoted keys/values. Production Cron sends the configured CRON_SECRET bearer token. The precise JSON example is below. Verify an unauthorized request is rejected, a scheduled invocation succeeds, and expired rows are removed during inactivity. This source does not install a schedule, enforce a cloud SLA or prove deletion timing.
8. Verify the hosted release using the checklist below, then invite client testing. Do not declare the October 26 handover complete merely because deployment builds successfully.

After approval, merge the following property into vercel.json; do not replace its existing functions configuration:

```json
"crons": [{"path": "/internal/cron/purge-locations/", "schedule": "* * * * *"}]
```

Vercel Hobby Cron is only once daily and may run anywhere within the chosen hour. Pro/Enterprise support minute-level schedules, but a schedule is not a hard deletion guarantee. Monitor failures. A deleted row can still remain in provider logs, physical backups or point-in-time recovery history. Set and disclose their retention separately.

## Privacy and GPS boundaries

Technicians share only after explicit Start and browser permission and can Stop. The browser watch stops on hiding/leaving the page and attempts a server stop; network loss can prevent immediate deletion. The app retains only a latest sample per active session, never a route trail. Samples are stale after 30 seconds and excluded from views after at most 120 seconds without an accepted update. The v0.4 dispatcher also removes already-rendered expired cards while its JavaScript runs and checks again when visible; suspended/browser-disabled code cannot give a real-time guarantee.

Foreground web GPS cannot promise updates while the phone is locked or the browser is backgrounded. The browser position can be inaccurate or spoofed; it does not prove attendance or physical safety. Tests used simulated coordinates, never a technician's real location. Real Android HTTPS Start/Stop, denial, network loss, hidden/locked lifecycle, account revocation and dispatcher behavior must be tested before operational use.

For privacy-aware manual PostgreSQL backups, use a direct URL and omit transient table data:

```
pg_dump --format=custom --no-owner --no-acl \
  --exclude-table-data=operations_locationshare \
  --exclude-table-data=django_session \
  --exclude-table-data=login_throttle \
  --file=PRIVATE_BACKUP_FILE
```

Supply PGHOST/PGUSER/PGDATABASE/TLS and authentication through a protected environment or correctly permissioned password file; never paste credentials into a shared command log. Encrypt the backup, restrict access and restore it to a new database before relying on it. This dump is not a complete GPS-erasure guarantee: managed provider snapshots/PITR and logs need their own approved retention policy. The included SQLite snapshot tool is for SQLite only.

## Local verification and honest scope

The package includes reproducible local test/recovery scripts and raw results under evidence/v0.4. PostgreSQL was a disposable local TLS-enabled cluster, not Neon or another hosted service. It proved existing migration data survives, independent processes share business data/sessions, the release plan/apply path works and a dump restores business records without live GPS/session data. It did not test provider poolers, Vercel's cloud builder, real TLS/domain routing, real accounts, cloud backups or production load.

Local commands: `./scripts/setup-local.sh`; then `./scripts/manage.sh createsuperuser` and `./scripts/manage.sh runserver 127.0.0.1:8000`. Local SQLite data stays under .local. For regression: `./scripts/manage.sh test --settings=config.test_settings`; for browser fixtures: `uv run --frozen --group dev python scripts/browser_smoke.py`. PostgreSQL rehearsal requires local PostgreSQL binaries/OpenSSL and runs `uv run --frozen python scripts/rehearse_postgresql.py`; do not point it at a real provider.

## Release checklist and remaining essentials

- Owner-approved scope/fields and role matrix; regular operators still share generic allocations. Confirm operational timezone; current timestamps are UTC, not an inferred client timezone.
- Reliable onboarding/recovery route, actual administrator and backup account plan, and client training. Current private account provisioning/password change works; activation/recovery email is not implemented or verified. Do not silently call that requirement finished.
- Client-specific August/quotation/voice-note requirements remain unavailable. Existing CRM/Maintenance flows implement owner-accepted broad workflows, not proof of a complete client-approved contract.
- Inventory/spares stock movement, billing, payroll, GPS history and background tracking are not implemented or promised; business type alone did not authorize those modules.
- Hosted migrations, persistence across deploys, backup/restore drill, selected provider pooler/TLS, password/account separation, rate limits, roles, CSRF, static assets and log redaction tested on the actual host.
- Physical Android/laptop test, accessibility/usefulness review, realistic concurrency/load and independent security review. Local test passes are not a production certification.
- Actual cleanup schedule, privacy/retention policy, provider snapshot/log access and encryption, downtime/rollback/restore instructions and named operator.
- Stable domain and HTTPS, final handover guide/training, client acceptance. Intentional HSTS includeSubDomains/preload warnings remain until domain ownership/TLS implications are agreed.

Smallest hosting inputs: exact repository and Vercel team/project; confirmation of existing paid plan or separately approved spending; database/region and recovery-retention decision; exact domain/host. Secrets belong in protected provider settings, not chat. The unresolved role/onboarding and real-device acceptance decisions remain separate release signoffs.

## Official references checked 19 October 2026

- https://vercel.com/docs/frameworks/full-stack/django
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/plans/hobby
- https://vercel.com/docs/plans/pro-plan
- https://vercel.com/docs/cron-jobs/usage-and-pricing
- https://vercel.com/docs/cron-jobs/manage-cron-jobs
- https://vercel.com/docs/regions
- https://vercel.com/docs/functions/configuring-functions/region
- https://neon.com/docs/guides/django
- https://neon.com/docs/guides/django-migrations
- https://neon.com/docs/guides/serverless-connection-pooling
- https://neon.com/docs/introduction/regions
- https://neon.com/pricing

Recheck prices, limits and actual account entitlements before approving any paid plan or deployment.
