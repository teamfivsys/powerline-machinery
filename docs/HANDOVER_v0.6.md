# Powerline Machinery
## v0.6 — tested local build and release gates

Prepared October 19, 2026. This is an updated runnable Django application, not a deployed service or a declaration of client acceptance. Earlier versions are preserved. The existing GitHub repository still contains v0.5; this local task does not push v0.6.

### What changed

New operator and technician accounts now require replacement of their temporary password before opening records or using operational endpoints. The replacement form rejects the current password, preserves the successful browser session and invalidates other authenticated sessions through Django's password session hash. Existing accounts are not silently gated by the migration.

Operator-assisted recovery is available on a trusted server terminal. It requires independent identity verification, never sends email, does not change roles or reactivate disabled users, and requires a fresh personal password at next sign-in. Password input is not echoed. This is not self-service email recovery or automatic activation.

Password changes, terminal recovery and POST logout clear that login's location-sharing rows. Operational allocation queries no longer load salary fields. Empty employee/allocation/service submissions display validation errors. Conditional location updates reject late samples after completion and prevent older concurrent samples overwriting newer ones. No permission or location expiry was weakened.

### Run the source

Python 3.12+ and uv are required. Open the extracted powerline-v0.6 folder and run the following. Use fictional records. Keep the local development server bound to loopback.

    chmod +x scripts/*.sh
    ./scripts/setup-local.sh
    ./scripts/manage.sh createsuperuser
    ./scripts/manage.sh runserver 127.0.0.1:8000

The setup creates private local runtime files and applies all migrations, including 0004_accountsecurity. It supplies no default credentials. Do not commit or share .local, databases, keys or backups. Upgrade an existing installation only after an independently tested backup, then apply migrations explicitly; they never run during a web request.

### Provision and recover access

Create an employee as administrator, then use its numeric employee ID. Use unique temporary credentials privately and deliver them to the verified holder through an approved secure channel. A terminal operator's identity-verification flag records an assertion; software cannot itself establish the recipient's identity.

    ./scripts/manage.sh create_operator operator_name
    ./scripts/manage.sh create_technician technician_name EMPLOYEE_ID
    ./scripts/manage.sh recover_account existing_username --identity-verified

The last command must only be used after independent identity verification. New/recovered users sign in, replace the temporary password, then access their existing role. The trusted terminal is an administrative boundary: anyone with server/database control can change accounts. No recovery password, token or identity-verification document belongs in source or ordinary logs. Django's generic changepassword command does not enforce this application's temporary-password gate; use recover_account for the assisted procedure.

### Verification completed

168 automated tests passed on SQLite and separately on local TLS PostgreSQL. Fourteen end-to-end browser workflow checks, six password-replacement browser checks, three display-expiry checks, eight PostgreSQL persistence/recovery checks and eleven local TLS/SQLite recovery checks passed. The dependency audit reported no known vulnerabilities. The accompanying build report and evidence folder record exact runs and their limits. Full application regression covers HR joining/salary records, allocations, CRM closure validation, maintenance and assigned-technician access, opt-in GPS, expiry, authentication, configuration and snapshots. The browser exercises use fictional records and simulated coordinates only.

Local PostgreSQL is not Neon: hosted pooler, credentials, certificate trust, quotas and provider recovery remain untested. Local self-signed TLS proves test-connection encryption, not provider certificate validation. Chromium mobile emulation is not an actual Android phone. Test success is not a penetration test, a load guarantee or client acceptance.

### Free demonstration route

The prepared Render Free web service plus external Neon Free PostgreSQL remains a candidate for a fictional-data demo only. Render sleeps after 15 idle minutes and cold starts can take about a minute. Render warns against using its free service for production. Its free PostgreSQL expires after 30 days, so the configuration does not use that database.

Previous official-source review described Neon Free as ongoing/no-card, with 1 GB storage, 100 CU-hours/month, 5 GB egress and limited instant restore. Refresh actual eligibility and quotas before signup; these are not a reserved entitlement or an all-in production service. Explicit Free-plan commercial-client production entitlement remains unresolved. No signup, deployment, provider account or payment was made here.

The blueprint selects a free web service and disables automatic deployments; it provisions no database, disk or cleanup schedule. Follow docs/FREE_DEMO_v0.5.md for the prepared host settings and explicit migrations. All historical setup notes are subordinate to the current release gates here.

### Location and recovery limits

Location sharing is voluntary, assigned-job only, foreground web GPS with visible Start/Stop. Coordinates can be spoofed and do not prove attendance. Locked-phone/background tracking is not guaranteed. An unreachable server can delay a Stop request. Display expiry is not scheduled physical deletion: the free route has no cloud cleanup schedule, and provider backups may retain deleted samples. Do not enter real employee salaries or locations into this demonstration candidate.

Local SQLite snapshots exclude location samples but retain browser sessions, password hashes and salary data, so protect them as sensitive backups. The PostgreSQL rehearsal excludes both location samples and browser sessions. Both methods retain account-security flags. Production still needs encrypted off-host recovery, tested restore, controlled backup access and an agreed retention/deletion policy. Restored passwords retain their hashes, so production recovery should include a deliberate account/session incident procedure.

### Remaining release gates

1. Hosting: approve the exact free-demo account/project and publication only after checking current provider eligibility, terms and charges. No-card/no-paid commitment remains the constraint. A suitable live-production service is a separate decision.

2. Hosted verification: deploy only when authorized, then test actual HTTPS, PostgreSQL persistence across restarts/deploys, migrations, pooler/TLS, cold starts, cleanup and restore. Do not mark the app delivered merely because a deployment starts.

3. Physical Android: on the eventual HTTPS site, test permission allow/deny/revoke, explicit Stop, offline/reconnect, hidden tab, screen lock, reassignment, completion and dispatcher expiry using a consenting test user. Only a real device can settle this gate.

4. Client decisions: approve final roles (generic allocations are still shared between regular operators), operational timezone, named administrator/recovery identity process, privacy/retention, onboarding and the detailed acceptance checklist. No automated activation/recovery email is configured; that would require a selected verified mail service and sender identity.

5. Handover: targeted security/load review, encrypted recovery and actual client acceptance remain. October 26 at 17:00 IST is the working target, not a delivery guarantee.

### Official references from the preceding hosting review

https://render.com/docs/free
https://render.com/terms
https://render.com/docs/deploy-django
https://neon.com/pricing
https://neon.com/terms-of-service

No current commercial entitlement is inferred from the absence of a prohibition in retrieved text.
