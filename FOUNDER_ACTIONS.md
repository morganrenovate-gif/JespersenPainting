# Founder Actions

This file batches actions that truly require Adam.

## Open

None for the repository executor credential setup.



Do not add routine architecture, schema, debugging, staging, testing, backlog, or reversible implementation decisions here.

## Allowed future founder actions
Only add items that require:
- personal identity verification;
- legal/provider terms acceptance;
- spend above an authorized ceiling;
- a credential that only Adam can create;
- production promotion;
- a material security/privacy decision;
- an irreversible production action;
- resolution of a true requirement contradiction.

## Closed

### CONTROL-BOOTSTRAP-001
Decision: Replace the hourly Jespersen worker pattern with the DropRadar-style autonomous Build Director model.

Result:
- old hourly worker disabled;
- public GitHub repository selected as project/source-control plane;
- exact bootstrap approval granted;
- project contracts authorized for creation.


### CONTROL-EXECUTOR-CREDENTIAL-001
Decision: Use existing Perplexity API credits instead of requiring new OpenAI API billing.

Result:
- user reports `PERPLEXITY_API_KEY` is stored as a GitHub Actions repository secret;
- the key is never committed or pasted into project records;
- runtime smoke verification is still required after merge.
