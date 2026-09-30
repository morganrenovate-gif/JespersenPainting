# Jespersen Painting Intelligence Project Contract

## Mission
Build a dependable operating-intelligence system for Jespersen Painting that connects time capture, QuickBooks, historical job costing, material/invoice evidence, job economics, and estimating into one evidence-backed operating system.

The system should reduce manual reconciliation, preserve source truth, surface disagreements instead of hiding them, and turn Jespersen's historical operating history into reusable intelligence.

## Current build objective
Reach a verified staging operating foundation that can demonstrate, end to end:
1. employees can clock time against the right job with minimal friction;
2. QuickBooks data can be read and reconciled without silently changing accounting records;
3. historical job-cost workbooks can be batch-ingested without trusting broken formulas;
4. material and invoice evidence can be normalized with provenance;
5. job economics can separate source facts, computed facts, and unresolved conflicts;
6. the estimator foundation can compare predicted scope/cost against completed-job actuals;
7. independent QA can reconstruct what changed and roll it back.

## Existing runtime
- Hedy project: `proj_793bfb1dcd74481b8c759b9064674aed`
- Application: Jespersen Intelligence
- GitHub repository: `morganrenovate-gif/JespersenPainting`
- GitHub is the durable source of truth for project contracts, backlog, decisions, agent operating rules, and versioned implementation source where practical.
- Hedy is the hosted runtime/control plane.
- Production remains founder-controlled.

## Founder involvement policy
Routine founder involvement is prohibited.

The Build Director should not interrupt Adam for framework choices, ordinary schema choices, routine debugging, reversible refactors, test fixes, prioritization inside the accepted backlog, safe dev/staging iteration, or ordinary integration research.

Founder interruption is allowed only when:
1. personal identity verification is required;
2. provider/legal terms require personal acceptance;
3. new spend exceeds an authorized ceiling;
4. a required credential can only be created personally;
5. production release or another consequential production action requires approval;
6. a material security/privacy event requires judgment;
7. a true requirement contradiction cannot be resolved conservatively.

For all other reversible ambiguity: decide, document, test, continue.

## Decision order
1. `PROJECT.md`
2. `PRODUCT_SPEC.md`
3. `ACCEPTANCE.md`
4. `CONSTRAINTS.md`
5. `DATA_BOUNDARY.md`
6. accepted entries in `DECISIONS.md`
7. safest simple implementation
8. source integrity and observability
9. reversibility
10. lowest reasonable recurring cost

## Definition of real
A capability does not exist because code for it exists.

A capability exists only when its expected behavior is demonstrated in an authorized deployed environment and supported by tests, source evidence, or durable runtime records.

## Data principle
Real Jespersen business data is not source code.

No real client-sensitive workbook, payroll record, QuickBooks export, Gmail content, invoice, customer record, employee record, credential, or token belongs in this public repository. See `DATA_BOUNDARY.md`.
