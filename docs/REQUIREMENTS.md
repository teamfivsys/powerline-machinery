# Requirements mapping — v0.4

Baseline: client-requirements PRD v0.2; later owner-accepted initial CRM/Maintenance flows and both job progress + GPS. This implementation is not a declaration of complete client acceptance.

| Need / accepted implementation | Current implementation | Boundary |
|---|---|---|
| Employee details, joining dates, salaries | Persistent employee create/edit, explicit currency/basis, admin-only salary | Not payroll calculation |
| Allocate work to staff | Existing persistent generic allocations | Regular operators still share these; final permission matrix open |
| CRM customer spare-parts/service enquiry through closure | Admin enquiry records, follow-up, outcome-required closure/reopen | Minimal fields/statuses are engineering choices; no stock, prices or invoices |
| Machine/fault, assign technician, work/completion | Admin service job linked to existing employee, optional Service enquiry | Work done required at completion; not complete asset/inventory register |
| Technician service updates | Explicit employee/login mapping; assigned-job status/work-done only | No arbitrary job/CRM/dispatcher/salary access |
| Both field-job updates and GPS | Above service updates + opt-in foreground browser GPS, Start/Stop, latest sample, accuracy/age/expiry; admin dispatch view | Not continuous background GPS; real Android/HTTPS testing pending |
| Usable access and correct Powerline identity | Server-side sign-in/password changes; responsive Powerline Machinery UI | No activation/recovery email, notifications or branded domain |
| Laptop/Android usability | Desktop/narrow Chromium inspection and smoke tests | Physical Android/device permission/lifecycle checks pending |
| Working final system and guided handover | Runnable source, setup guide, PostgreSQL/Vercel preparation and local recovery evidence | Not publicly deployed or client-ready handover |

CRM and Maintenance are no longer placeholder modules. The owner accepted broad practical flows; the exact client-specific fields, permissions and any additional August scope remain unresolved. The original quotation and reliable voice-note content were not recovered in the preceding evidence review. Requirements not found are unknown, not silently excluded from the client contract.

No inventory accounting, automated notifications, payment/invoicing, payroll or route-history features were inferred from the business type. No new external services or account changes.

Hosting preparation does not close hosted onboarding, domain, retention, real-device, production restore or final acceptance gaps. See VERCEL_PREPARATION_v0.4.md.
