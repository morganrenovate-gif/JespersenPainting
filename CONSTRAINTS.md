# Jespersen Painting Intelligence Constraints

## Public repository boundary
This repository is public. Assume every committed byte can be copied permanently.

Never commit:
- passwords, secrets, API keys, OAuth/client secrets, access/refresh tokens, connection strings, session cookies, or private keys;
- raw QuickBooks exports;
- raw Gmail messages or attachments;
- payroll records, SSNs, bank information, tax information, employee PII, or customer PII;
- private customer/job addresses;
- private invoices;
- the 350+ real Jespersen Excel job-cost workbooks;
- production database exports;
- private Hedy data exports;
- screenshots containing private business/customer/employee data.

Use synthetic or irreversibly sanitized fixtures only. See `DATA_BOUNDARY.md`.

## Access / integration
- Use permitted and authorized provider access.
- Do not bypass authentication, provider controls, rate limits, or contractual restrictions.
- Gmail is read-only unless an exact later authorization says otherwise.
- QuickBooks is read/reconcile-first; writes require exact authorization when governed.
- Do not infer authority from tool availability.

## Accounting truth
QuickBooks remains the accounting source of truth for accounting records.

Jespersen Intelligence may normalize, reconcile, and derive intelligence, but must not silently rewrite accounting truth.

## Historical workbook truth
A workbook total is source evidence, not automatically canonical truth.

Preserve the source and independently recompute supported economics. Surface disagreement.

## Privacy
Collect the minimum data needed for the feature.

Do not use raw payroll, SSN, bank, or tax data for product-development convenience.

Do not move real client data into GitHub to simplify testing.

## Security
- Least privilege.
- Sealed/runtime secret storage only.
- No secret in source control.
- Explicit outbound host allowlists where runtime supports them.
- Authenticated routes for private operational surfaces.
- Material security/privacy failures block release.

## Environments
- Git branches and a safe development lane are preferred for feature work.
- Staging is for integrated acceptance.
- Production remains founder-controlled.
- Autonomous agents may not promote to production.
- Production changes require their own exact authorization.

## Deployment safety
- One deployment writer per Hedy project/environment.
- Capture pre-change revision.
- Use dry-run where supported.
- Use optimistic concurrency / expected revision guards.
- Verify deployed revision.
- Verify production did not move during staging work.
- Maintain rollback target.
- Do not blindly retry ambiguous consequential failures.

## Data quality
- Preserve provenance.
- Preserve raw-vs-normalized-vs-derived distinctions.
- Preserve history where behavior depends on time.
- Fail safely on uncertain entity mappings.
- Surface missing, stale, conflicting, and error states.

## Product scope
Do not expand into unrelated CRM, marketing, payroll-provider replacement, or generic ERP features until the current acceptance contract passes or an explicit decision changes scope.

## Engineering
- Idempotent imports/syncs where practical.
- Bounded retries.
- Observable failures.
- Reversible migrations.
- Deterministic calculations for financial recomputation where possible.
- AI interpretation must not silently become financial/accounting truth.
