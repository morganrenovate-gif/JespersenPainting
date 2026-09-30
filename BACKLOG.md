# Jespersen Painting Intelligence Backlog

Status values: TODO, IN_PROGRESS, BLOCKED_EXTERNAL, QA, PASS.

Priority:
- P0 = blocks operating foundation
- P1 = required for Mission 01 acceptance
- P2 = follow-on / estimator foundation

## CONTROL

### CONTROL-001 — Bootstrap autonomous project contracts
Priority: P0
Status: IN_PROGRESS

Acceptance:
- approved project-control files committed;
- public-repo data boundary encoded;
- backlog and status become durable.

### CONTROL-002 — Persistent autonomous coding runtime
Priority: P0
Status: TODO

Goal:
Connect a persistent coding/build runtime to GitHub and an authorized Hedy non-production lane so the Build Director can continue without an active chat session.

Acceptance:
- can read repo/contracts;
- can create bounded branches/commits/PRs;
- can run tests;
- can inspect Hedy non-production state;
- can build/test/promote only within authorized non-production scope;
- can continue backlog work after one dependency blocks;
- cannot autonomously promote production;
- sensitive-data pre-commit checks enforced.

## TIME / QUICKBOOKS

### TIME-001 — Fresh QuickBooks provider reads
Priority: P0
Status: TODO

Goal:
Repair/verify the provider path so fresh authorized customer/job and employee reads work in the safe non-production lane.

Constraints:
- read-only verification first;
- credential/auth changes require exact authority;
- provider blocker must not stop independent DATA work.

### TIME-002 — Employee/job identity mapping
Priority: P0
Status: TODO

Acceptance:
- suggestions are reviewable;
- uncertain matches fail safely;
- normalization does not silently merge people/jobs.

### TIME-003 — Field clock UX
Priority: P0
Status: TODO

Acceptance:
- one assignment: open -> Clock In;
- multiple assignments: open -> select job -> Clock In;
- obvious running timer and Clock Out;
- accounting/provider internals hidden from field employee.

### TIME-004 — Offline/pending sync
Priority: P1
Status: TODO

Acceptance:
- poor connectivity does not destroy a captured time event;
- pending state visible;
- replay is idempotent.

### TIME-005 — Time adversarial QA
Priority: P1
Status: TODO

Cases:
- duplicate clock-in;
- forgotten clock-out;
- cross-midnight;
- job switch;
- location unavailable/suspicious;
- provider outage;
- correction request;
- replay/duplicate sync.

## DATA — 350+ HISTORICAL WORKBOOKS

### DATA-001 — Corpus inventory contract
Priority: P0
Status: TODO

Goal:
Inventory the 350+ real workbooks in governed storage without putting them in public GitHub.

Acceptance:
- stable source ID;
- immutable file hash;
- file status;
- parser/adapter version;
- ingest/review status.

### DATA-002 — Workbook shape classifier
Priority: P0
Status: TODO

Acceptance:
- identifies materially different workbook structures;
- unknown shape fails to review instead of guessing;
- classification is reproducible.

### DATA-003 — Normalized job-cost schema
Priority: P0
Status: TODO

Model:
- job;
- employee/labor row;
- material/vendor row;
- invoice/payment/revenue row;
- source workbook/sheet/cell provenance;
- formula/source evidence;
- recomputed economics;
- discrepancy.

### DATA-004 — Versioned workbook adapters
Priority: P0
Status: TODO

Acceptance:
- adapter version stored;
- one malformed workbook does not break batch;
- unknown layout remains reviewable.

### DATA-005 — Batch importer
Priority: P0
Status: TODO

Acceptance:
- designed for 350+ files;
- resumable/idempotent;
- progress observable;
- item-level error isolation;
- immutable source link retained.

### DATA-006 — Independent recomputation
Priority: P0
Status: TODO

Acceptance:
- labor recomputed;
- materials recomputed;
- supported revenue/payments recomputed;
- gross profit/margin recomputed;
- source-vs-recomputed difference explicit.

### DATA-007 — Representative reconciliation QA
Priority: P1
Status: TODO

Acceptance:
- manual review across representative workbook variants;
- known formula/reconciliation inconsistencies surfaced;
- no silent overwrites.

## GMAIL / MATERIAL EVIDENCE

### GMAIL-001 — Authorized read-only source path
Priority: P1
Status: TODO

Acceptance:
- exact authorized mailbox/data scope;
- read-only;
- source failures observable;
- no Gmail writes.

### GMAIL-002 — Invoice/document extraction
Priority: P1
Status: TODO

Acceptance:
- vendor/date/invoice/job reference;
- line-item facts when supported;
- source locator;
- confidence/extractor version;
- bounded failure behavior.

## ECON — JOB ECONOMICS

### ECON-001 — Source-separated economics model
Priority: P1
Status: TODO

Inputs remain distinct:
- estimate;
- change orders;
- time/labor;
- materials;
- invoice evidence;
- QuickBooks facts;
- historical workbook facts.

### ECON-002 — Conflict/staleness model
Priority: P1
Status: TODO

Acceptance:
- missing source visible;
- stale source visible;
- conflicting source visible;
- derived value traceable to inputs.

### ECON-003 — Owner job-economics view
Priority: P1
Status: TODO

Acceptance:
Owner can understand what a job made/lost and why without needing API/accounting knowledge.

## EST — ESTIMATOR FOUNDATION

### EST-001 — Painting takeoff taxonomy
Priority: P2
Status: TODO

Scope:
walls, ceilings, doors, trim, cabinets, exterior and finish requirements.

### EST-002 — Deterministic rules + AI interpretation boundary
Priority: P2
Status: TODO

Acceptance:
AI interpretation cannot silently become measured/financial truth.

### EST-003 — Backtest harness
Priority: P2
Status: TODO

Acceptance:
plans -> predicted scope/labor/material -> completed-job actual -> variance.

Real PASS requires a matching completed plan set and actuals.

## QA / RELEASE

### QA-001 — Public-repo sensitive-data gate
Priority: P0
Status: TODO

Acceptance:
secret/PII/private-client-data checks block unsafe commits.

### QA-002 — Tenant/auth/isolation
Priority: P1
Status: TODO

### QA-003 — Hedy revision/rollback safety
Priority: P1
Status: TODO

### QA-004 — Full staging acceptance matrix
Priority: P1
Status: TODO

### RELEASE-001 — Independent founder-review package
Priority: P1
Status: TODO

No autonomous production promotion.
