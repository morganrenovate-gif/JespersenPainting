# Jespersen Painting Intelligence Product Specification

## Primary users

### Owner / office
Needs a reliable view of jobs, time, cost, margin, exceptions, evidence, and what requires attention.

### Field employee
Needs a fast clock-in/clock-out experience with almost no technical or accounting concepts exposed.

### Estimating / operations
Needs historical actuals, production patterns, material history, and evidence-backed estimating support.

## Core jobs
1. Clock employees into the correct active job quickly.
2. Preserve a trustworthy time record with clear correction history.
3. Reconcile employee/job identities across operational systems.
4. Read QuickBooks accounting facts without making unauthorized writes.
5. Ingest 350+ historical job-cost workbooks at batch scale.
6. Preserve original workbook evidence and independently recompute economics.
7. Extract structured material/invoice facts from authorized email/document sources.
8. Build source-separated job economics.
9. Turn completed-job history into estimating calibration data.
10. Surface uncertainty, source conflict, stale data, and missing evidence explicitly.

## Field clock experience
The field clock must use a familiar HoursTracker-style mental model without copying branding or protected design assets.

### One active assignment
Open app -> Clock In.

### Multiple active assignments
Open app -> choose job -> Clock In.

### While clocked in
Show:
- obvious running timer;
- current job;
- clock-in time;
- large Clock Out action;
- optional break/switch-job path where supported.

Hide from field employees:
- QuickBooks technical state;
- accounting mappings;
- payroll integration details;
- profitability;
- API/provider errors;
- internal source IDs.

Location capture should happen quietly at required events. A suspicious location should create an owner/admin review signal rather than unnecessary worker friction.

Poor connectivity must not destroy a time event. The product should retain a safe local/pending state and make synchronization status clear.

Corrections should be request/review based when they can affect payroll or accounting.

## Identity and mapping
Employee and job names from different systems are evidence, not automatic identity truth.

Normalization may suggest likely matches such as capitalization or spelling variants, but uncertain matches must remain reviewable. Silent identity merges are prohibited.

## Historical job-cost intelligence
Jespersen has a corpus of 350+ Excel job-cost workbooks.

The ingestion system must:
- support batch processing;
- preserve immutable source identity and file hash;
- identify workbook shape/version;
- use versioned adapters;
- preserve source sheet/cell or equivalent provenance where practical;
- preserve relevant formulas as evidence;
- independently recompute labor, materials, revenue, cost, gross profit, and margin;
- surface workbook-vs-recomputed disagreement;
- never silently replace source values;
- tolerate incomplete and structurally inconsistent historical files;
- make parser/adapter version observable.

The initial retrieved sample is QA/adaptation evidence, not the full corpus and not proof that all workbooks share one structure.

## QuickBooks
QuickBooks remains the accounting source of truth for accounting records.

Initial integration behavior is read/reconcile first.

Writes, including TimeActivity or accounting changes, require their own exact authorization when governance requires it.

The intelligence layer must distinguish:
- provider source data;
- cached data;
- normalized entities;
- inferred mappings;
- user-confirmed mappings;
- sync errors/staleness.

## Gmail / invoice evidence
Authorized Gmail/document ingestion should extract source-attributed facts such as:
- vendor;
- invoice number;
- invoice date;
- job reference;
- line description;
- SKU when available;
- quantity;
- unit price;
- total;
- source message/document locator;
- extraction confidence/version.

No Gmail writes are part of the operating foundation.

## Job economics
A job economics view should reconcile, without collapsing distinctions:
- estimate;
- approved changes;
- time;
- labor cost;
- materials;
- vendor invoices;
- QuickBooks accounting facts;
- historical job-cost records.

Every derived margin or cost should be traceable to its inputs.

Conflict is a first-class state.

## Estimator foundation
The estimator should eventually combine:
- plan/document ingestion;
- scale/geometry where available;
- room/surface classification;
- walls, ceilings, doors, trim, cabinets, exterior scope;
- finish requirements;
- Jespersen-specific production rules;
- historical labor/material calibration;
- provenance by plan/sheet/room/scope.

The first meaningful backtest requires a complete plan set plus matching completed-job actuals.

## Product language
Do not present unsupported certainty.

Use states such as:
- verified;
- source-reported;
- recomputed;
- inferred;
- needs review;
- missing;
- conflicting;
- stale/error.

## Expansion rule
Do not add unrelated business features merely because they are possible. Finish the operating foundation and acceptance contract first.
