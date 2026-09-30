# Public GitHub Data Boundary

## Purpose
This file is a hard safety contract for every human and autonomous agent touching `morganrenovate-gif/JespersenPainting`.

The repository is public. Real Jespersen operational data must remain in governed runtime/storage, not GitHub.

## Allowed in GitHub
- application/source code that contains no secret or private client data;
- schemas and interfaces;
- migration definitions that contain no live data;
- agent contracts and project documentation;
- test code;
- synthetic fixtures;
- irreversibly sanitized examples;
- fake names, fake addresses, fake invoice numbers, fake job numbers;
- aggregate/non-identifying examples that cannot reconstruct a person, customer, or real transaction.

## Prohibited in GitHub
Never commit:
- credentials or secrets of any kind;
- OAuth/access/refresh tokens;
- QuickBooks company exports or row-level real accounting data;
- Gmail message bodies, headers containing private identities, or attachments;
- payroll data or compensation details tied to real employees;
- SSNs, bank/routing/account numbers, or tax records;
- employee personal information;
- customer personal information;
- private job/customer addresses;
- private invoices/receipts;
- the 350+ real Excel job-cost workbooks;
- raw exports from Hedy/client collections;
- production logs containing private payloads;
- screenshots containing private operational data;
- copied source documents used to train/test extraction;
- reversible pseudonyms that can be joined back to a real person without a separately governed mapping.

## Synthetic fixture standard
Synthetic data must:
1. use invented people/companies/jobs;
2. use fake contact details;
3. avoid copying real monetary combinations when they could identify a real job;
4. avoid real addresses;
5. avoid real document IDs;
6. be clearly labeled synthetic;
7. preserve only the structural edge case needed for testing.

## Sanitization standard
If an example is derived from a real structure, strip or replace names, email addresses, phone numbers, street addresses, job/customer identifiers, invoice/account numbers, free-text notes, exact identifying dates when not needed, file metadata that can reveal identity, and any credential/session/token material.

When in doubt, create a fresh synthetic fixture instead.

## Autonomous-agent pre-commit rule
Before every autonomous GitHub write:
1. inspect the proposed diff;
2. run secret-pattern checks;
3. run sensitive-data checks;
4. reject binary/private source files;
5. verify every test fixture is synthetic/sanitized;
6. fail closed on uncertainty.

A blocked sensitive-data check is not a reason to weaken the scanner.

## Release rule
Any discovered sensitive material in Git history is a release-blocking security/privacy incident.

Required response:
1. stop autonomous GitHub writes;
2. notify Adam;
3. remove/rewrite the exposed material using an approved remediation path;
4. rotate/revoke any exposed credential;
5. verify Git history and external caches as appropriate;
6. document the incident.

## Storage rule
Real business evidence belongs in governed Hedy/runtime storage or another explicitly approved private data store.

GitHub references may use safe internal IDs or schema names, but must not embed the underlying private payload.
