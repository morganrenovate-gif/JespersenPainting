# Jespersen Painting Intelligence Acceptance Contract

Founder review should be requested only when required criteria are PASS or explicitly BLOCKED-EXTERNAL with evidence that independent work continued.

## Required: control plane
- [ ] GitHub project contracts are current and internally consistent.
- [ ] Backlog items map to acceptance criteria.
- [ ] Build Director can continue work without routine founder prompts.
- [ ] Implementation and final material QA are separated.
- [ ] STATUS.md reflects deployed reality, not planned capability.
- [ ] FOUNDER_ACTIONS.md contains only true founder-only work.

## Required: public-repository safety
- [ ] No secret, token, API key, OAuth credential, connection string, private key, or session material is committed.
- [ ] No raw QuickBooks export is committed.
- [ ] No raw Gmail message or attachment is committed.
- [ ] No payroll, SSN, bank, tax, employee PII, or customer PII is committed.
- [ ] No private invoice is committed.
- [ ] None of the 350+ real Jespersen job-cost workbooks are committed.
- [ ] Test data in GitHub is synthetic or irreversibly sanitized.
- [ ] Pre-commit / pre-PR sensitive-data checks exist before autonomous implementation is considered ready.
- [ ] QA treats any sensitive-data exposure as a release-blocking failure.

## Required: QuickBooks / identity
- [ ] Fresh authorized QuickBooks customer/job reads work in the non-production lane.
- [ ] Fresh authorized QuickBooks employee reads work in the non-production lane.
- [ ] Provider/cache/staleness state is visible.
- [ ] Employee identity mapping supports reviewable suggestions.
- [ ] Job identity mapping supports reviewable suggestions.
- [ ] Uncertain identity matches fail safely.
- [ ] No unauthorized QuickBooks write occurs.

## Required: field time
- [ ] One-assignment morning flow is open app -> one-tap Clock In.
- [ ] Multi-assignment morning flow is open app -> choose job -> Clock In.
- [ ] Active clock shows timer, job, start time, and obvious Clock Out.
- [ ] QuickBooks/accounting internals are hidden from field employees.
- [ ] Required location events are captured without continuous-tracking dependency.
- [ ] Suspicious location creates review state instead of unnecessary hard blocking.
- [ ] Poor connectivity can preserve a pending time event.
- [ ] Duplicate clock-in is handled safely.
- [ ] Forgotten clock-out is reviewable.
- [ ] Cross-midnight time is handled.
- [ ] Job switching is handled without overlapping time.
- [ ] Corrections preserve audit/review history.
- [ ] QuickBooks/provider outage does not destroy local time truth.

## Required: 350+ workbook job-cost ingestion
- [ ] Corpus ingestion is designed for 350+ workbooks, not a hand-built one-file flow.
- [ ] Original file identity/hash is preserved outside this public repo.
- [ ] Workbook structure/version detection exists.
- [ ] Versioned adapters exist for materially different workbook shapes.
- [ ] Raw source values and relevant formulas remain attributable.
- [ ] Labor is independently recomputed.
- [ ] Materials are independently recomputed.
- [ ] Revenue/payments are independently recomputed where evidence supports it.
- [ ] Gross profit and margin are independently recomputed.
- [ ] Workbook-vs-recomputed disagreement is surfaced, not overwritten.
- [ ] Import replay is idempotent.
- [ ] Bad/incomplete workbook does not terminate unrelated batch ingestion.
- [ ] Batch progress/errors are observable.
- [ ] A representative validation sample passes manual reconciliation.

## Required: Gmail / material evidence
- [ ] Authorized source retrieval is read-only.
- [ ] PDF/document extraction preserves source locator/provenance.
- [ ] Vendor and invoice fields are extracted when supported.
- [ ] Line-item facts retain confidence/source context.
- [ ] Extraction failures are visible and retry-bounded.
- [ ] No Gmail write occurs.

## Required: job economics
- [ ] Estimate, time, labor, materials, invoices, QuickBooks facts, and historical job-cost facts remain source-separated.
- [ ] Derived totals identify their inputs.
- [ ] Conflicts remain visible.
- [ ] Stale/missing sources are visible.
- [ ] Recomputed economics do not silently overwrite source records.
- [ ] Owner can understand why a job appears profitable/unprofitable.

## Required: estimator foundation
- [ ] Estimator architecture is documented.
- [ ] Scope taxonomy supports painting-relevant surfaces/components.
- [ ] Deterministic rules are separable from AI interpretation.
- [ ] Evidence/provenance is retained for extracted scope.
- [ ] Conflicting/uncertain plan interpretation becomes NEEDS REVIEW.
- [ ] One completed-job backtest protocol exists.
- [ ] A real backtest is not claimed until matching plan set and completed actuals are available.

## Required: UI / UX
- [ ] Every user-facing implementation is reviewed against `UI_STANDARD.md` / UI-STD-1.0.
- [ ] UI briefs declare Product, Surface, dominant archetype, secondary influence, palette, density, motion intensity, primary users, and critical information.
- [ ] Jespersen surfaces preserve the Industrial Operations + Digital Blueprint profile unless an explicit project guide narrows it.
- [ ] Financial/time values use appropriate aligned/tabular presentation and exception states outrank decorative metrics.
- [ ] Mobile interaction is explicitly designed rather than treated as compressed desktop.
- [ ] Accessibility, visible focus, touch targets, semantic structure, status-without-color-only, and reduced-motion behavior are verified.
- [ ] Anti-generic review passes: the surface is recognizably Jespersen/construction operations without relying on the logo.
- [ ] Generic AI SaaS output is release-blocking until redesigned.

## Required: QA / release
- [ ] Unit checks pass where applicable.
- [ ] Integration tests pass.
- [ ] Staging end-to-end tests pass.
- [ ] Tenant/client isolation is verified.
- [ ] Single-writer / revision guards are verified for Hedy deploys.
- [ ] Production is verified unchanged during autonomous staging work.
- [ ] Rollback path is tested.
- [ ] No Critical security/privacy finding remains open.
- [ ] No High security/privacy finding remains open.
- [ ] Independent QA signs off.
- [ ] Independent release/audit review signs off.
- [ ] Autonomous agents do not promote to production.

## Founder review package
At the founder-review gate provide:
- staging URL;
- acceptance matrix;
- test summary;
- current integration status;
- historical-data ingestion status;
- security/privacy findings;
- known limitations;
- founder-only actions;
- rollback state;
- factual release readiness evidence.
