# Powerline | Free demonstration route
## v0.5 | Prepared 19 October 2026

Render Free web service + Neon Free PostgreSQL is a practical candidate for a fictional-data demonstration without rewriting Django. This package is local preparation, not a deployed service or production handover. No account, project, repository, subscription or payment was created. Earlier application, roles, salary restrictions and foreground GPS behavior are preserved.

### What $0 means
Render provides free Python web services, private-GitHub deployment and managed HTTPS. No card is required for its free route. Leave payment methods absent: exceeding bandwidth suspends free services, and exhausting build minutes stops new builds instead of billing. The workspace has 750 free instance-hours monthly. These are shared workspace quotas, not a promise of unlimited traffic.

The service sleeps after 15 minutes without inbound traffic. The next visitor can wait about a minute for startup. Its filesystem is ephemeral, so neither SQLite records nor local backups belong there. Render explicitly says not to use Free instances for production applications. Its free PostgreSQL expires after 30 days; this blueprint intentionally creates no Render database.

Neon describes Free as permanent, not a trial, with no credit card required. Current allowances are 1 GB PostgreSQL storage per project, 100 CU-hours per project per month and 5 GB monthly egress. At 0.25 CU, 100 CU-hours covers roughly 400 active hours, not continuous month-long use. Compute sleeps after five minutes of inactivity. Exhausted compute/egress quota suspends access; storage persists but is not a substitute for an independent backup. Instant restore is limited to up to six hours or 1 GB of data changes, not a long-term disaster recovery guarantee. Check the actual signup plan before proceeding; do not upgrade automatically.

### Commercial-policy finding
Render's general terms expressly contemplate commercial use in their dispute provisions. Its general license is for the account's own use, subject to available features. The inspected Free documentation does not provide a separate affirmative commercial-client-hosting grant and explicitly warns against production. Therefore this report does not certify Free as suitable or contractually approved for Powerline's live business.

Neon's current product schedule covers individual and company customers and incorporates the Databricks Master Cloud Services Agreement. Its pricing describes Free for prototypes, side projects and small teams. The incorporated agreement was also retrieved. An explicit Free-plan commercial-production entitlement and account-specific eligibility remain unresolved. Lack of a discovered prohibition is not proof of permission.

For a zero-cost fictional-data demonstration this is a candidate to validate, not a recommendation to entrust live salaries or employee coordinates to an unapproved production setup. Resolve client ownership/authorization and provider eligibility before account creation or publication.

### Prepared configuration
The new config.render profile requires Render's environment marker, exact hosts, strong secret, debug off and external TLS PostgreSQL. It refuses ephemeral SQLite. Sessions and login throttling continue to use PostgreSQL. Render's managed TLS ingress is trusted only in this profile. Do not expose it behind an untrusted proxy.

render.yaml declares only one free Python web service; automatic deployments are off. It creates no database, disk, cron job or paid resource. scripts/build-render.sh installs hash-locked dependencies, runs Django checks and collects static files. It does not migrate, seed, create users or schedule jobs. scripts/start-render.sh starts one Gunicorn worker on Render's PORT. .env.render.example contains placeholders only; never commit actual secrets.

Local checks passed: 12 new configuration/package tests, 63 existing customer/service/location protection tests, shell syntax, production-profile static collection and a Gunicorn login-page startup check (HTTP 200, no-store). These do not validate a hosted Render build, real TLS or Neon database connectivity. Earlier v0.4 evidence remains separately labelled.

### Later deployment sequence - not performed
1. Confirm this demonstration-only scope, provider eligibility and which owner controls the accounts. Select an exact private GitHub repository and approve its push/publication separately. Do not reuse unrelated client projects.
2. Select Render Free and Neon Free without a payment method or trial upgrade. Match available database/compute regions where possible. Verify quotas, terms and actual signup conditions; stop if a card, hold or future charge is required.
3. Privately set DATABASE_URL, DJANGO_SECRET_KEY, exact DJANGO_ALLOWED_HOSTS and HTTPS CSRF origins. Use the provider's supported TLS URL. No secrets go into chat, source, logs or this guide.
4. On a trusted operator machine, use the Neon direct connection for schema release. Set RENDER=true and DJANGO_SETTINGS_MODULE=config.render in that environment. Run the guarded release command below first without --apply. Inspect the actual target, backup/recovery requirements and migration plan. Then explicitly authorize the single release operator to apply it. No migrations run at web startup.

    python scripts/release_database.py \
      --confirm-host EXACT_DB_HOST \
      --confirm-database EXACT_DB_NAME

With approved application of that same plan, add --apply. This also creates the database login-throttle cache table. Never use scripts/manage.sh against hosted PostgreSQL: it deliberately selects local SQLite development.

5. Create a demo administrator interactively with manage.py createsuperuser in the same trusted release environment; never embed a password in an argument or fixture. Use fictional customer, employee and machine records only. Connect the repo and build/start the free service only after publication is approved. Validate actual HTTPS, static assets, login, permissions, hosted persistence and cold-start behavior before showing it.

### Location cleanup and recovery limits
No free scheduled Render cron is available, and no external scheduler has been installed or invented. Expired shares are purged on relevant location/dispatcher requests or by the existing purge_locations management command. The dispatcher stops showing expired samples while its JavaScript runs. Stopping sharing deletes its current share; a closed browser may leave an expired row until the next cleanup request. Display expiry is not guaranteed wall-clock physical deletion, and backups/restore history may retain deleted samples.

Do not configure anti-sleep pings. They waste free compute and do not turn this into a production service. Minute-by-minute database cleanup can prevent Neon sleeping and exhaust free compute. Preserve the existing two-minute sharing expiry; do not silently relax retention to fit a free host. The demo uses simulated coordinates only until privacy/retention agreement, cleanup scheduling, real-phone HTTPS testing and recovery controls are resolved.

A free web filesystem is not off-host backup storage. Existing SQLite snapshot tooling is not a PostgreSQL backup. PostgreSQL logical backup/restore needs a private operator environment, securely managed database credentials, encrypted separate durable storage and a tested recovery process. Provider instant restore alone is insufficient for live handover. None has been configured here. Manual demo reset/reseed is acceptable only for fictional disposable data, not real client data.

### Other candidates and remaining gates
PythonAnywhere Free cannot connect to external PostgreSQL; its own PostgreSQL also needs payment. Koyeb requires card verification with a hold and documents a selected-plan charge at signup; its Free compute also warns against production. Neither improves this strict no-card demonstration route based on reviewed pages.

Remaining: provider commercial eligibility/account ownership; repo and publication approval; actual free signup availability; hosted build/TLS/database/persistence validation; onboarding/password recovery; approved operational roles/timezone; privacy and physical-retention controls; real Android permission/lifecycle testing; independent encrypted backups and restore; load/security review and final client acceptance. Foreground browser GPS cannot guarantee updates while a phone is locked or backgrounded.

### Official references
https://render.com/docs/free
https://render.com/terms
https://render.com/docs/deploy-django
https://render.com/docs/web-services
https://render.com/docs/your-first-deploy
https://neon.com/pricing
https://neon.com/terms-of-service
https://www.databricks.com/legal/mcsa
https://help.pythonanywhere.com/pages/Postgres/
https://www.koyeb.com/docs/faqs/pricing

Sources were retrieved on 19 October 2026. Plans and entitlements can change; recheck before signup. Exact observed source extracts are included in evidence/v0.5-*.txt.
