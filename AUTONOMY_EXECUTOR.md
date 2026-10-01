# Autonomous Repository Executor

## Purpose

This repository uses a bounded Perplexity Agent API lane as the hands of Product Engineering.

The Jespersen Mission Controller owns the outcome and backlog. The Perplexity-backed executor is an implementation runtime, not a new governance agent.

## Flow

1. Mission Controller reads the durable project contracts and backlog.
2. It selects one highest-value eligible public-safe T0/T1 repository task.
3. It creates an issue beginning with `[AGENT]`.
4. The executor validates the task envelope and trigger actor before the provider secret is exposed to the agent step.
5. The implementation model works only through bounded repository read/write tools on an isolated Git branch.
6. The model has no shell, GitHub, Hedy, QuickBooks, Gmail, or arbitrary network tool.
7. A trusted post-agent step runs repository checks with no provider credential present.
8. The public-repository data gate runs before any commit.
9. A pull request is opened.
10. A separate model/provider performs read-only independent QA.
11. PASS automatically squash-merges the PR and closes the task.
12. That merge immediately triggers Mission Controller to select the next eligible task.

The loop is event-driven, not hourly.

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

## Perplexity configuration

The executor uses the GitHub Actions repository secret:

- `PERPLEXITY_API_KEY`

Default models:

- implementation: `openai/gpt-6-sol` through Perplexity Agent API, using the `flex` service tier;
- Mission Controller: `openai/gpt-6-luna` through Perplexity Agent API, using `flex`;
- independent QA: `google/gemini-3.7-flash`.

Optional GitHub repository variables may override them:

- `PERPLEXITY_CODER_MODEL`
- `PERPLEXITY_CONTROLLER_MODEL`
- `PERPLEXITY_REVIEW_MODEL`

The workflow records Perplexity-reported API cost in the Actions log without exposing the API key.

## Credential boundary

The Perplexity API key is injected only into the provider-call step.

The implementation model does **not** receive:

- a GitHub token;
- Hedy credentials;
- QuickBooks/Gmail credentials;
- private Jespersen data;
- arbitrary shell access.

The checkout also uses `persist-credentials: false` during model execution. Trusted GitHub credentials are introduced only later, after the model process exits and deterministic safety checks pass.

## Repository tools

Implementation receives only bounded tools for:

- listing files;
- reading UTF-8 text files;
- literal repository search;
- reading git status/diff;
- writing non-protected UTF-8 files;
- deleting non-protected files.

Control-plane paths under `.github/`, the autonomous executor itself, data-boundary rules, agent contract, validators, and safety gates are protected.

Executable tests are run by a trusted workflow step **after** the provider-key process exits.

## Safety controls

- only repository writers or the trusted GitHub Actions bot may trigger execution;
- issue envelopes are validated before model execution;
- public-repo data and secret scanners fail closed;
- private-data-prone/binary file types are blocked from autonomous commits;
- synthetic/test fixtures must be explicitly labeled synthetic;
- the implementation model cannot modify workflow/control-plane files;
- the implementation model cannot push, merge, call Hedy, send email, or mutate providers;
- independent QA uses a separate model/provider;
- production promotion remains outside this workflow.

## Hedy boundary

Hedy staging deployment and runtime acceptance are a separate execution lane.

This repository executor may build source that is later deployed to authorized Hedy staging, but it does not receive a Hedy connector token and cannot directly deploy.

That separation prevents a public-repository coding model from becoming a bridge to private Jespersen runtime data.

## Activation

The repository-side loop becomes active when:

1. this control-plane PR is merged to `main`;
2. `PERPLEXITY_API_KEY` exists as a GitHub Actions repository secret;
3. Mission Controller is manually dispatched once for the smoke test.

CONTROL-002 remains IN_PROGRESS until the first complete Mission Controller -> task -> implementation -> safety -> independent QA -> merge -> next-controller cycle is observed.
