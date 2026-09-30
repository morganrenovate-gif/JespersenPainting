# Autonomous Build Runbook

## Startup loop
1. Read `PROJECT.md`, `PRODUCT_SPEC.md`, `ACCEPTANCE.md`, `CONSTRAINTS.md`, `DATA_BOUNDARY.md`, and `AGENTS.md`.
2. Read `STATUS.md`, `BACKLOG.md`, `DECISIONS.md`, and `FOUNDER_ACTIONS.md`.
3. Inspect repository state, open work, current Hedy non-production state, production baseline, and recent failures.
4. Verify no unresolved security/privacy incident is open.
5. Select the highest-value unblocked work tied to an acceptance criterion.
6. Work on a safe development lane.
7. Run automated checks.
8. Test deployed/integrated behavior where authorized.
9. Send material work to independent QA/Security.
10. Repair failures.
11. Promote only passing immutable work into staging when authorized.
12. Run staging acceptance and adversarial QA.
13. Update `STATUS.md`, `BACKLOG.md`, and `DECISIONS.md`.
14. Continue automatically until the founder-review gate or a true founder-only blocker.

The build loop is mission/backlog driven, not an arbitrary hourly one-task worker.

## GitHub write preflight
Before every GitHub write:
1. inspect diff/content;
2. enforce `DATA_BOUNDARY.md`;
3. scan for secret patterns;
4. scan for PII/private client data;
5. reject real spreadsheets/exports/email/invoices;
6. verify fixtures are synthetic or irreversibly sanitized;
7. fail closed if uncertain.

## Hedy write preflight
Before any authorized Hedy non-production mutation:
1. resolve current project/environment;
2. capture current active revision;
3. confirm the exact authority/approval covers the intended write;
4. dry-run where supported;
5. require expected revision/hash guards where supported;
6. keep one deployment writer;
7. record rollback target.

After the write:
1. verify active revision/result;
2. run relevant tests;
3. verify production baseline did not move;
4. record evidence.

## QuickBooks integration protocol
1. Prefer read-only diagnostics first.
2. Separate provider source facts from cached/normalized state.
3. Make stale/error state visible.
4. Do not perform a QuickBooks write without exact authorization.
5. Do not expose credentials in logs or GitHub.
6. If provider credentials/routing are blocked, isolate that blocker and continue unrelated backlog work.

## Historical workbook protocol
For the 350+ workbook corpus:
1. keep real files outside public GitHub;
2. inventory files in governed storage;
3. compute/preserve immutable source identity/hash;
4. detect workbook structure/version;
5. choose a versioned adapter;
6. extract raw source facts with provenance;
7. independently recompute supported economics;
8. record source-vs-recomputed discrepancies;
9. make bad files item-level failures rather than batch failure;
10. preserve adapter/parser version;
11. validate representative samples manually;
12. never silently overwrite source evidence.

## Source failure protocol
A provider timeout, malformed response, auth failure, rate limit, or parser failure must be isolated and logged, must not corrupt unrelated work, must use bounded retry, must expose degraded health, and should preserve the last known trustworthy state where appropriate.

## Blocker protocol
When a dependency is unavailable:
1. verify failure;
2. determine whether a permitted alternative exists;
3. implement the alternative when reasonable;
4. isolate blocked integration/work item;
5. document it in backlog/status;
6. continue independent work;
7. add a founder action only if the founder truly must act.

## Release protocol
Autonomous development may reach verified staging only under active authorization.

Production promotion is prohibited without founder approval.

## Founder review package
At the finish gate provide:
- staging URL;
- acceptance matrix;
- automated/integration/E2E test summary;
- security/privacy findings;
- known limitations;
- QuickBooks/Gmail integration status;
- 350+ workbook ingestion status;
- job-economics status;
- estimator/backtest status;
- `FOUNDER_ACTIONS.md`;
- rollback state;
- production baseline confirmation.
