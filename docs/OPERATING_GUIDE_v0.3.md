# Powerline Machinery
## v0.3 local build · operating and verification guide
19 October 2026 · Prepared for FIVSYS

### 1. What this version gives you
A runnable standalone application for employee records, work allocation, customer enquiries, maintenance jobs and technician service updates. The business context supplied by Felix is spare parts and maintenance for forklifts and similar machinery.

Felix accepted the initial customer-enquiry and maintenance flows and requested both service-job updates and GPS. This build implements the bounded foreground-GPS interpretation, not continuous background surveillance. It has not been deployed or approved for live staff/customer data. The October 26 at 17:00 IST target remains conditional.

### 2. Start and keep your local data
Install Python 3.12+ and uv. Extract the source, open the powerline-v0.3 folder in a terminal and run:

    chmod +x scripts/*.sh
    ./scripts/setup-local.sh
    ./scripts/manage.sh createsuperuser
    ./scripts/manage.sh runserver 127.0.0.1:8000

Open http://127.0.0.1:8000/ and sign in. Create your own password privately at the prompt. There are no preset accounts or sample records in the delivered package. Use fictional data for testing. This local development server must not be exposed publicly.

The .local folder contains the private local secret and database. Keep it to preserve your records between restarts; do not commit it or send it with source code. Ctrl-C stops the server. Running the same runserver command resumes it. The source ZIP excludes secrets, databases, certificates, virtual environments and generated static files.

### 3. Employee records and work allocation
As administrator, open Employee records and add a fictional employee. Save name, joining date, salary amount, explicit currency and pay basis. Reopen the edit form to confirm persistence. Currency and basis are descriptive; no payroll calculation is performed.

Open Work allocation to add a title, existing employee and instructions. Save and reopen it. These original generic allocations remain shared among regular operators under the provisional earlier model. They are not the restricted technician-maintenance workflow. Do not put sensitive customer/service details into generic allocation instructions while the role matrix is unsettled.

Only administrators can view salary/joining details or change employee records. Technician and ordinary operator views do not load salary fields. No staff notification is sent by saving an allocation.

### 4. Customer enquiries (administrator only)
Open Customer enquiries → New enquiry. Enter customer, optional contact, type (Spare parts or Service), summary and details. Save, reopen and add follow-up notes. Status options are Open, In progress and Closed. Closing requires an actual outcome; closing an enquiry does not mean a sale, payment or service completion.

An enquiry can be reopened by changing status and saving. Notes/outcome remain editable rather than acting as an immutable communication timeline. A Service enquiry may be linked to a maintenance job. A linked enquiry cannot be changed to Spare parts. Closing one record never silently closes its linked record.

These fields and simple statuses are minimal engineering choices supporting the accepted flow. They are not confirmed client-specific sales stages. Inventory, prices, quotes, invoicing, messaging and payments are not included.

### 5. Maintenance and assigned technician access
As administrator, open Maintenance jobs → New service job. Enter customer, optional Service enquiry link, machine identifying description and reported fault. Choose a technician from existing employee records; no fake assignee list is used. Save the job and reopen it. Status options are Open, In progress and Completed. Completion requires recorded work done. Administrators can reopen/edit a completed job.

For technician self-service, an administrator with local system access must explicitly map a login to the employee. Read its numeric employee ID from /employees/ID/edit/ and run:

    ./scripts/manage.sh create_technician technician_name EMPLOYEE_ID

The command privately asks for the new password. For an existing active non-superuser login use:

    ./scripts/manage.sh link_technician username EMPLOYEE_ID

Each employee and login has one mapping. No identity is inferred from names, and linking grants no administrator rights. To revoke mapped service access and clear location sessions:

    ./scripts/manage.sh unlink_technician username

Unlinking does not disable the login or remove its existing ordinary-operator permissions. Password changes use the standard local changepassword command. No activation email or recovery-email flow is implemented.

A linked technician signs in, opens My service jobs and can view only assigned maintenance jobs. They can change status and work-done notes, not customer, machine, fault, enquiry link or assignee. Another technician's job URL is rejected. Completing a job clears its location share and removes the sharing controls. Administrator job edits also clear sharing; a technician must explicitly start again.

### 6. Optional foreground location sharing
On an assigned, incomplete service job, the technician taps Start location sharing and chooses whether to allow browser location access. No automatic location query happens merely by opening the page. The interface visibly shows waiting, sharing, denied, unavailable or stopped state. Start/Stop requests are CSRF-protected and authenticated to that technician and job.

Only an administrator can open Live job locations. Refresh retrieves current latest samples, including capture time, age and approximate accuracy. There is no paid map dependency or external map request; this initial view displays coordinates and the linked job. There is no route history or attendance inference.

A sample more than 30 seconds old is marked stale. Samples expire from a newly fetched view within 120 seconds without updates. The browser stops its location watch when hidden, left or explicitly stopped, and attempts to clear the server share. Network loss can prevent that request reaching the server; expiry limits the remaining visible sample. An already open dispatcher page does not erase itself automatically: use Refresh. Do not rely on this system for safety-critical tracking.

HTTPS is required on ordinary devices; localhost is the development exception. A web page cannot guarantee continuous background GPS while a phone is locked, a tab is hidden or the operating system suspends it. Actual device permissions, GPS accuracy, network behavior and employer/worker privacy requirements still need real-world testing and agreement. The browser position is client-reported, not tamper-proof evidence.

The database stores only the latest sample per sharing session/job. Requests delete expired sessions; for timely storage cleanup schedule purge_locations every minute on the eventual host. This package does not install that schedule. Coordinates are not duplicated in application audit events. The provided snapshot tool strips location sessions and vacuums the snapshot. That is not a guarantee against host logging, external backups or physical SQLite remnants; production needs encryption and a reviewed retention policy.

### 7. Practical acceptance exercise with fictional data
1. Create an employee, save joining/salary data and reopen it. Create and reopen a generic allocation.
2. Add a Service enquiry, save a follow-up, try closing without an outcome (must fail), then close with an outcome. Reopen it.
3. Create a service job linked to that enquiry and assigned to the employee. Completion without work done must fail.
4. Create/map a technician login. Sign in as that technician; only their assigned service job should be available. Changing another job ID must not reveal its data. CRM, dispatcher and salary edit URLs must be forbidden.
5. Record service progress and reopen it. In an approved HTTPS staging environment on a real Android phone, test optional Start, browser permission denial, allowed sharing, accuracy/time display, Stop, tab hiding, lock screen, connection loss and expiry. Do not collect a real person's position without their consent.
6. Complete the service job with work done. Verify the record persists and any sharing stops. Verify its enquiry did not silently close.

The shipped browser tests use fictional records and explicitly simulated coordinates, not a real phone or person. They do not satisfy step 5's device/HTTPS acceptance check.

### 8. Verification performed on this build
117 automated Django tests passed. They include the preserved original suite plus CRM and service validation/persistence, closure/reopening, salary/access controls, explicit mapping, forged fields, CSRF, per-assigned-job location access, invalid/non-finite and stale samples, expiry, stopping/reassignment/completion and location-free snapshots.

14 Chromium browser-smoke checks passed through real local forms. They cover enquiry and job creation/editing, closure validation, technician progress/completion, server restrictions, synthetic sharing/Stop/permission denial, persistence and narrow-layout checks. Desktop CRM/dispatcher and a 390px technician screen were inspected. This is browser simulation, not physical Android verification.

11 local production/recovery checks passed with Gunicorn and a self-signed TLS proxy. The restored database retained account login, employee, work allocation, enquiry, job and technician mapping, but no location coordinates. There were no production-check errors. HSTS warnings W005/W021 are deliberately retained until domain/subdomain TLS policy is confirmed. No missing migrations were detected.

Full commands and raw outputs are in README.md and evidence/v0.3-*. The source package is independently extracted and tested before delivery; see BUILD_REPORT.md for the final package result. Dependency scanning is a point-in-time advisory check, not a security certification.

### 9. Release work still required
Settle the actual client role matrix, customer/service field details and handover checks. Ordinary operators still share generic work allocation. Complete real Android/HTTPS location tests and consent/privacy agreement; background GPS needs a different deliberately scoped platform if it becomes mandatory.

Choose hosting, persistent database, real TLS/proxy configuration, encrypted off-host backups, recovery schedules, monitoring and load/security review. The production settings reject dangerous configuration and do not replace infrastructure setup. SQLite here is a durable local database, not a serverless persistent database.

Felix selected a future GitHub-to-Vercel route, explicitly for later. No repository push, deployment, account creation or paid service occurred. Vercel's ephemeral filesystem cannot safely hold this SQLite database: a persistent database and deployment adaptation are prerequisites before any public release.

Excluded unless separately agreed: stock/accounting, parts purchasing, prices/tax/invoices, payments, payroll calculations, automated notifications, automatic background GPS, route playback and production guarantees.
