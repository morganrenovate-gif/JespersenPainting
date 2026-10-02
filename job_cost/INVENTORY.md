# DATA-001 — historical workbook inventory metadata contract

`job_cost.inventory.InventoryRecord` is a frozen, slots-based **in-memory snapshot** of one original file's inventory state. It is not a workbook, a path/locator, an extracted `JobCostDocument`, or a job-cost fact. `source_id` is an opaque `src_` identifier (16–64 lowercase ASCII letters/digits after the prefix) assigned to the original file by a future governed inventory; it is not derived from a filename, job number or customer. `sha256` is a lowercase 64-character digest supplied by that inventory for **original file bytes**, not for normalized contents or formulas. This module does not open files, calculate hashes, identify duplicates, allocate IDs, or validate that a claimed digest matches bytes. A changed original is a different inventory source, not a silent mutation of the old digest.

Fields and valid states:

| Field | Meaning |
| --- | --- |
| `file_status` | `available`, `missing`, `quarantined` (inventory availability; not ingestion success) |
| `parser_version`, `adapter_version` | Optional versioned identifiers such as `cell-parser/1`, `ledger-adapter/2`; distinguish source parsing and selected shape adapter |
| `ingest_status` | `pending`, `failed`, `ingested` |
| `review_status` | `pending`, `needs_review`, `approved` |

`pending` ingestion has neither parser nor adapter selection. Attempted ingestion (`failed` or `ingested`) requires a parser version; failure may have no adapter if shape selection failed. `ingested` requires an available file and selected adapter. Missing/quarantined files or failed ingests require `needs_review`. `approved` requires ingestion success. Ingested records may still need review; a successful parser does not imply reviewed economics. These are snapshot consistency rules, **not** a workflow or transition engine: an authorized future workflow must retain audit history and define any stricter transitions.

`validate_inventory_update(previous, current)` rejects reassignment of a source ID or original-byte digest between snapshots. Frozen instances protect in-process mutation only; a future governed store must enforce stable ID/hash uniqueness and compare updates atomically, including concurrent writes, and maintain review history. No persistence, storage integration, filesystem traversal, provider connection, runtime integration, or user-facing surface is supplied here. No file path, workbook bytes, source cell/formula, customer label or job-cost amount belongs in this model. The separate `job_cost.schema.SourceWorkbook` belongs to an extracted document and identifies its shape/parser/adapter context; `JobCostDocument` holds source facts and separate derived metrics. A later integration must reconcile IDs/hashes and versions explicitly rather than treating an inventory snapshot as evidence of extracted or recomputed financial truth.

The tests use invented synthetic IDs and hashes only. This repository contract does **not** establish real 350+ workbook corpus coverage, original-byte hashing in governed storage, deployed ingestion, review approval, staging acceptance or production capability. Those require separately authorized private storage/runtime evidence and independent QA. Rollback is deletion of `job_cost/inventory.py`, `tests/test_job_cost_inventory.py`, and this document; there is no external state to revert.
