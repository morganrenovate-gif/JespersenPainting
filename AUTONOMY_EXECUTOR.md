# Autonomous Codex Executor

## Purpose

This repository uses a bounded GitHub Actions + Codex lane as the hands of Product Engineering.

The Jespersen Mission Controller owns the outcome and backlog. Codex is an implementation executor, not an independent authority and not a new product/governance agent.

## Flow

1. Mission Controller selects an acceptance-linked T0/T1 coding task.
2. It produces a public-safe issue beginning with `[CODEX]`.
3. The executor validates the task envelope and trigger actor.
4. Codex works only in an isolated Git branch using the public repository.
5. The public-repository data gate runs before any commit.
6. A pull request is opened.
7. A fresh read-only Codex run acts as independent QA/Security reviewer.
8. PASS automatically squash-merges the PR and closes the task.
9. FAIL leaves the PR open for remediation.
10. Hedy staging deployment/acceptance remains a separate controlled lane. The public GitHub executor receives no Hedy token and no real Jespersen data.

## Required issue envelope

Use this exact shape:

```text
Task ID: DATA-003
Client context: jespersen-painting
Permission tier: T1
Environment: staging
Public-safe task package: yes

Objective:
<bounded outcome>

Requested work:
<implementation request>

Acceptance:
<replayable acceptance criteria>

Constraints:
<paths, boundaries, source-of-truth rules>

Rollback:
<how to reverse this repository change>
```

The task package must contain only public-safe implementation context. Never paste real workbook rows, customer/job identities, employee/payroll data, Gmail content, QuickBooks row data, private invoices, credentials, tokens, or private Hedy payloads.

## Credential boundary

The executor requires one GitHub Actions secret:

- `OPENAI_API_KEY` — used only by the pinned official `openai/codex-action`.

The workflow deliberately does **not** receive `HEDY_CONNECTOR_TOKEN`. The repository is public and Actions logs/artifacts must never become a path for private Jespersen runtime data.

A later Mission Controller -> GitHub dispatch binding will require a narrowly scoped GitHub credential stored in governed Hedy secret storage. That credential is a T3 setup action and is not part of routine T1 execution.

## Security controls

- only users with repository write permission may trigger Codex;
- the official Codex action is pinned to an exact reviewed commit;
- Codex runs with the built-in `:workspace` permission profile;
- independent review runs in `:read-only`;
- critical safety files cannot be modified by the autonomous lane;
- private-data-prone/binary file types are blocked;
- secret, private-key, bearer-token, SSN-like, and non-synthetic email patterns are blocked;
- synthetic/test fixtures must be explicitly labeled synthetic;
- production promotion is outside this workflow;
- no Hedy credential or client payload is available to Codex.

## Current activation status

The repository-side executor is ready once `OPENAI_API_KEY` is stored as a GitHub Actions repository secret.

Until that secret exists, CONTROL-002 remains IN_PROGRESS rather than PASS.
