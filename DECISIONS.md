# Jespersen Painting Intelligence Decisions

## D-001 — GitHub is the durable project/source-control plane
Status: Accepted

GitHub stores project contracts, backlog, decisions, agent operating rules, tests, and versioned implementation source where practical. Real Jespersen business data is not GitHub source code.

## D-002 — Hedy is the initial runtime/control plane
Status: Accepted

Use the existing Hedy Jespersen Intelligence project for hosted runtime, app data, logs, non-production testing/deployments, and rollback. Production remains founder-controlled.

## D-003 — Public repository means synthetic/sanitized data only
Status: Accepted

The repository is public. No real Jespersen workbook, QuickBooks export, Gmail content, payroll/PII, private invoice, credential, or token may be committed.

## D-004 — QuickBooks remains accounting source of truth
Status: Accepted

Jespersen Intelligence may read, normalize, reconcile, and derive intelligence from authorized accounting data but may not silently redefine accounting truth.

## D-005 — Historical workbook totals are evidence, not canonical truth
Status: Accepted

Preserve workbook evidence and independently recompute supported job economics. Disagreement must remain visible.

## D-006 — Field clock uses an HoursTracker-familiar mental model
Status: Accepted

The worker experience should minimize steps and hide accounting/integration internals while preserving reviewable time truth.

## D-007 — Backlog-driven autonomous build, not hourly one-task execution
Status: Accepted

The Build Director owns the whole accepted mission and keeps independent work moving until the staging/founder-review gate.

## D-008 — Separation of duties
Status: Accepted

Implementation may not be the sole final verifier of its own material change. Independent QA/Security and Release/Auditor review are required.

## D-009 — One serialized Hedy deployment writer
Status: Accepted

Avoid parallel/stale-revision deploys. Capture pre-change state, use concurrency guards, verify result, and retain rollback.

## D-010 — Evidence before claims
Status: Accepted

Do not call a capability complete merely because code exists. Require deployed/tested evidence or a durable runtime record.


## D-011 — Perplexity Agent API is the bounded Product Engineering executor
Status: Accepted

Use Perplexity Agent API credits as the repository coding runtime. Mission Controller owns task selection and bounded dispatch; the implementation model edits only through restricted repository tools on an isolated branch; trusted checks run after the provider-key process exits; a different model/provider performs independent QA before automated merge. The executor is an execution lane, not a new governance agent.

## D-012 — Mission Controller is event-driven, not hourly
Status: Accepted

After an accepted autonomous PR merges, the Mission Controller immediately re-reads the durable project contracts/backlog and dispatches the next eligible public-safe T0/T1 repository task. It stops when no eligible task exists or when work requires private runtime evidence/T3 authority. This avoids arbitrary hourly one-task polling.
