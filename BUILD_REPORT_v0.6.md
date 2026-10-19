# Powerline v0.6 — local completion report

This update preserves v0.5 functionality and prior source. It does not deploy or replace the GitHub version.

## Implemented fixes

- Added AccountSecurity migration, temporary-password replacement gate, secure password-change and logout views.
- New operators/technicians and terminal-recovered users must replace temporary passwords. Current-password reuse cannot clear the gate. Existing accounts retain their current access unless explicitly recovered.
- Added trusted-terminal recover_account requiring an independently verified identity assertion. It validates a non-echoed temporary password, preserves roles/active status, invalidates old authenticated sessions through Django's password-session hash and clears sharing. No email activation/recovery is implemented.
- Password changes and POST logout revoke the user's location-sharing rows.
- Conditional sample update rejects completed-job writes and concurrent out-of-order samples without recreating stopped shares.
- Operational allocation queries defer confidential salary columns.
- Empty submitted employee/allocation/service forms remain bound and expose required-field errors.
- SQLite snapshot table reporting includes AccountSecurity; tests prove mandatory replacement flags survive snapshots.

## Successful verification

- Full Django suite: 168 tests passed on SQLite (evidence/v0.6-tests.txt).
- Full Django suite: 168 tests passed on local TLS PostgreSQL (evidence/v0.6/postgresql-tests.txt).
- 14 Chromium end-to-end workflow checks: HR/salary, allocation, CRM, maintenance, technician permissions, synthetic opt-in GPS, stop/permission denial and mobile layout (evidence/v0.6-browser.txt).
- Six additional real-browser password replacement checks, including same-password rejection and 390px layout (evidence/v0.6/account-browser.json).
- Three dispatcher stale/expiry DOM checks with accelerated browser clock (evidence/v0.6-expiry.txt).
- Eight PostgreSQL checks: migration from existing employee/allocation data, independent-process data/session persistence, guarded explicit release, suite, pg_dump/restore and negotiated local TLS (evidence/v0.6/postgresql-rehearsal.json). Restored AccountSecurity record verified; location samples and browser sessions excluded.
- Eleven local production-profile/Gunicorn/self-signed-TLS/SQLite recovery checks passed (evidence/v0.6-production-rehearsal.json). Tracked row counts match; locations excluded. SQLite snapshots retain sessions and confidential data and must be protected. All 12 tracked table counts match.
- Migration consistency and shell syntax passed. Static collection ran in browser and production rehearsals.
- Locked dependency audit reported no known vulnerabilities (evidence/v0.6-dependency-audit.txt); not proof of no vulnerability or an independent security audit.

## Scope of confidence

Fictional records, random disposable test passwords and simulated coordinates only. Tests use local SQLite, a local PostgreSQL cluster and desktop/mobile-emulated Chromium. No external hosted database, real Android GPS lifecycle, actual client device, external email, cloud build, load test or independent penetration test was performed. Two deliberate HSTS subdomain/preload warnings remain until domain ownership/TLS policy is settled.

## Unfinished handover gates

See docs/HANDOVER_v0.6.md for the exact provider/account/publication, physical-device, final-permissions, timezone, identity/recovery, retention/privacy, encrypted off-host backup and client-acceptance gates. Render/Neon Free remains only a fictional-data demo candidate; commercial-client production eligibility is unresolved. There is no cloud cleanup schedule or background/locked-phone GPS guarantee.

No GitHub mutation, provider signup, deployment, paid commitment or external message occurred. The private GitHub main branch remains the previously verified v0.5 commit fcbf61d2645cb4e4bee2c16c4da86bb65858214f.
