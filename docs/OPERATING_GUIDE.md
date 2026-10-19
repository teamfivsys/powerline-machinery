# Historical operating guide — v0.1

For current v0.3 instructions see OPERATING_GUIDE_v0.3.md and the top-level README. The content below is preserved history, not current feature status.

# Initial operating guide

This guide matches build 0.1. It is not training for unfinished CRM/Maintenance workflows.

## Administrator

1. Open the local test URL from README and sign in using the account provisioned at the terminal.
2. Choose **Employee records → Add employee**. Enter a fictional staff name, joining date, salary amount, currency code and descriptive salary basis. Fields marked with an asterisk are required.
3. Click **Save record**. If an error appears, correct the highlighted field and save again. If saved, the staff list appears with a confirmation.
4. Choose **Edit** to reopen the record. Change the test value and save to check persistence.
5. Choose **Work allocation → Allocate work**. Choose the employee, enter a title and optional instructions, then save.
6. Reload or reopen Edit to verify the same allocation. This records responsibility only; it does not send a staff notification or mark work completed.
7. Use **Password** to change your own password. **Sign out** ends the browser session. There is no emailed reset/activation route in this initial build.

## Restricted operator

Can list staff names, view allocations and create/edit allocations. Cannot open staff creation/edit screens or see salary/joining details. This shared workspace permission model is provisional and must be approved before real use.

## What not to treat as complete

CRM, Maintenance and Field Tracking screens explicitly say they are not built. No automatic activation/notification is sent. No employee accounts or payroll calculations exist. The overview counts saved records, not completed jobs or accepted requirements.

## Troubleshooting

- No employee in assignment dropdown: an administrator must add a test staff record first.
- Access denied: sign in with the correct administrator account for staff editing; do not share passwords.
- Too many login attempts: wait 15 minutes. An administrator can investigate the staging service's rate-limit policy; do not repeatedly retry.
- Server won't start: check Python/uv and setup steps in README. Keep the secret and database files private. `DJANGO_SECRET_KEY` is mandatory outside the helper.
- Missing table error: migrations and `createcachetable` must run before use.
- Loading problem on a real phone: local `127.0.0.1` points to that phone, not the development computer. This build has not been hosted; do not expose the development server as a workaround. A properly configured authorised staging deployment is still needed.

Only fictional test data is approved for this build. Store real staff and salary data only after privacy, access, recovery and hosting review and the client's authorised go-ahead.
