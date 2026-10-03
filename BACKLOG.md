# Jespersen Painting Intelligence Backlog

Status values: TODO, IN_PROGRESS, BLOCKED_EXTERNAL, QA, PASS.

`QA` means the bounded repository implementation has merged and is no longer eligible for another autonomous task with the same ID; integrated/live acceptance may still be outstanding.

Priority:
- P0 = blocks operating foundation
- P1 = required for Mission 01 acceptance
- P2 = follow-on / estimator foundation

## CONTROL

### CONTROL-001 — Bootstrap autonomous project contracts
Priority: P0
Status: PASS

Acceptance:
- approved project-control files committed;
- public-repo data boundary encoded;
- backlog and status become durable.

### CONTROL-002 — Persistent autonomous coding runtime
Priority: P0
Status: IN_PROGRESS

Goal:
Connect a persistent coding/build runtime to GitHub and an authorized Hedy non-production lane so the Build Director can continue without an active chat session.

Current:
- bounded GitHub Actions Perplexity Agent API executor implemented on setup branch;
- event-driven Mission Controller implemented to select the next eligible public-safe T0/T1 backlog task after each accepted agent PR;
- user reports the repository Actions secret `PERPLEXITY_API_KEY` is stored; activation smoke test remains;
- Hedy staging deployment remains a separate controlled lane and is not falsely represented as wired yet.

Acceptance:
- can read repo/contracts;
- can create bounded branches/commits/PRs;
- can run tests;
- can inspect Hedy non-production state;
- can build/test/promote only within authorized non-production scope;
- can continue backlog work after one dependency blocks;
- cannot autonomously promote production;
- sensitive-data pre-commit checks enforced.

### CONTROL-003 — Hedy private runtime bridge package
Priority: P0
Status: TODO

Goal:
Build the public-safe, synthetic-only source package for Jespersen's bounded Hedy staging private-runtime worker so the existing autonomous Mission Controller can hand private DATA work to a separately authorized Hedy lane without exposing client data or credentials to GitHub.

Acceptance:
- defines a versioned private-runtime worker contract and deterministic state machine for bounded, resumable workbook intake;
- enforces fixed client context and staging-only execution through runtime-provided configuration, never repository secrets;
- defines a read-only provider adapter boundary that permits list/read operations only and rejects write-like operations;
- enforces a configured root-folder boundary and rejects out-of-bound synthetic file references;
- preserves opaque source identity, immutable hash/fingerprint fields, parser/adapter/recompute evidence, and item-level failure isolation;
- produces no accounting/provider writes and no production behavior;
- includes deterministic synthetic tests for resume/idempotency, folder-boundary rejection, unknown-shape fail-closed behavior, and private/public data separation;
- does not claim live Hedy, Google Drive, Nango, or real-workbook acceptance.

Constraints:
- T1 repository-only implementation using synthetic fixtures and public contracts only;
- do not access or include real Jespersen workbooks, employee/customer/job identities, QuickBooks/Gmail rows, Hedy private payloads, credentials, tokens, OAuth material, or the real Drive folder identifier;
- do not modify .github workflows, TASK_GRAPH.json, BACKLOG.md, STATUS.md, DATA_BOUNDARY.md, AGENTS.md, safety gates, validators, agent contracts, auth/permissions, provider configuration, Hedy runtime state, or production;
- keep provider transport behind an injected interface so credentials and OAuth remain entirely outside the public repository executor;
- rollback is removal/revert of this isolated repository package and tests only.


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
Status: QA

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
Status: QA

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
Status: QA

Acceptance:
- identifies materially different workbook structures;
- unknown shape fails to review instead of guessing;
- classification is reproducible.

### DATA-003 — Normalized job-cost schema
Priority: P0
Status: QA

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
Status: QA

Acceptance:
- adapter version stored;
- one malformed workbook does not break batch;
- unknown layout remains reviewable.

### DATA-005 — Batch importer
Priority: P0
Status: QA

Acceptance:
- designed for 350+ files;
- resumable/idempotent;
- progress observable;
- item-level error isolation;
- immutable source link retained.

### DATA-006 — Independent recomputation
Priority: P0
Status: QA

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
Status: QA

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
Status: QA

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
Status: QA

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


## PRIVATE RUNTIME SOURCE

### PRIVATE-DATA-006 — Financial extraction runner source
Priority: P0
Status: TODO

Goal: Existing Job Cost Intelligence source runner with a three-file pilot, independent financial reconciliation QA, and bounded resumable corpus continuation. Original attempt #44 stopped before acceptance; bounded remediation is owned by the trusted executor. Public synthetic source only. Real corpus execution and private runtime installation require separate evidence.

Acceptance: executable synthetic tests, decimal calculations, provenance, source immutability, idempotency, tenant/staging isolation, unknown-data review states, pilot gate, cancellation and bounded failure recovery. Production and provider writes remain excluded.

### PRIVATE-DATA-007 — Read-only XLSX financial JSON transport source
Priority: P0
Status: TODO

Goal: Build a bounded Node-compatible XLSX-to-JSON decoder and a dependency-injected provider action adapter using only synthetic workbooks. Hedy cannot buffer binary HTTP responses, so the private runtime needs source-bound JSON cell evidence from a separately installed read-only decoder.

Requested work: Preserve original-byte SHA-256 and MD5, worksheet names/locators, literal values, original formulas and separately read cached results, and complete nonempty-cell inventory. Verify provider metadata before and after reads through injected read-only transport, enforce parent/root and expected hash/version boundaries, and bound ZIP expansion, CRC, XML parsing, response size and retries. Decode shared/inline strings without evaluating formulas; reject unsupported shapes/entities/external relationships instead of guessing. Produce raw cell evidence for independently approved private profiles; never invent actual Jespersen layouts. Include executable synthetic XLSX fixtures and failure tests. A source adapter must not contain actual tenant configuration, source IDs, real workbook data or credentials.

Acceptance: Executable synthetic tests prove immutable originals, deterministic hashes/provenance, cached formula separation, complete cell coverage, safe ZIP/XML limits, changed metadata rejection, read-only provider interface, and unsupported format review dispositions. Public source only: do not install/deploy a provider action, modify credentials/auth/permissions, use real client data, call Hedy/Nango/Drive, or claim any live financial analysis. Exact private runtime installation, source-profile validation and independent three-file QA remain separate tasks. Backend source only; UI_STANDARD.md remains inherited.

Rollback: Revert decoder source and synthetic tests; no external/provider/source state is changed.
