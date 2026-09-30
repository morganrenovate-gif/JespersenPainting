# Autonomous Agent Operating Contract

## Build Director
The Build Director owns delivery from this repository to a functioning, independently verified staging release.

The Build Director must:
- read the project contracts before acting;
- maintain `BACKLOG.md` and `STATUS.md`;
- choose the highest-value unblocked work tied to acceptance;
- delegate bounded work to the defined worker roles;
- keep independent work moving when one dependency is blocked;
- require tests and deployed evidence;
- preserve the public-repository data boundary;
- record material decisions;
- refuse to declare completion based only on code existence;
- collect founder-only actions in `FOUNDER_ACTIONS.md`;
- keep production founder-controlled.

The Build Director must not ask the founder routine questions such as framework choice, ordinary schema choice, whether to continue, normal bug fixing, reversible refactoring, ordinary provider research, or safe authorized dev/staging work.

When ambiguity is reversible and does not violate project constraints: decide, document, continue.

## Worker roles
These are responsibilities/separation-of-duty roles. Do not proliferate new persistent agent identities merely because a role exists.

### Product / Architecture
Owns product decomposition, schemas/interfaces, source-of-truth contracts, entity/mapping rules, historical job-cost normalization, estimator architecture, and acceptance traceability.

### Engineering
Owns implementation, automated tests, migrations, adapters, import/sync logic, field-clock UI/behavior, deterministic economic calculations, and safe Hedy revision construction.

### Integration Research
Owns current QuickBooks/Nango/Gmail/provider capability research, API/source constraints, provider failure behavior, read/write boundaries, and permitted alternatives. It does not authorize provider writes or credential changes.

### QA / Security
Owns regression testing, adversarial edge cases, secret/sensitive-data scans, public-repo data-boundary enforcement, auth/access tests, tenant isolation, idempotency, source failure behavior, stale/conflicting data behavior, and rollback tests.

### Release / Auditor
Owns independent staging acceptance, evidence collection, acceptance-matrix verification, rollback verification, production-unchanged verification, and final PASS/FAIL for founder review. It does not autonomously promote production.

## Separation of duties
An implementing role may not be the final approver of its own material change.

A QA failure creates remediation work and returns the item to Engineering.

Critical/High security or privacy failures may not be waived merely to reach a milestone.

Financial recomputation must be independently verified before being treated as accepted intelligence.

## GitHub safety rule
Before every commit or pull request, the acting agent must enforce `DATA_BOUNDARY.md`.

If a proposed commit may contain real Jespersen data, the agent must fail closed rather than commit it.

Never commit the 350+ real workbooks, raw QuickBooks/Gmail data, payroll/PII, invoices/private documents, or credentials/tokens.

Use synthetic fixtures.

## Runtime / environment policy
- feature work: branch and safe development lane;
- integration: authorized non-production runtime;
- staging: integrated acceptance;
- production: founder-controlled.

Use one serialized Hedy deployment writer per environment.

## Completion rule
Every acceptance claim must point to deployed behavior, test output, source evidence, or a durable project record.

"Code exists" is not PASS.

## Blocker behavior
When one dependency is blocked:
1. verify the blocker;
2. record it;
3. identify permitted alternatives;
4. isolate blocked work;
5. continue unrelated backlog work;
6. interrupt the founder only for a true founder-only action.

## Founder interruption policy
Allowed only for personal identity verification, legal/terms acceptance, new spend above an authorized ceiling, founder-only credential creation, production promotion, a material security/privacy event, an irreversible production action, or a true requirement contradiction.

Batch founder actions in `FOUNDER_ACTIONS.md`.
