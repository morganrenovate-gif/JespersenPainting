"""DATA-005: in-memory, single-writer coordination of synthetic item adapters.

The checkpoint protocol is a boundary for a future governed store, not persistence.
Progress contains only states and opaque source identity references, never evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from job_cost.adapters import ItemResult, PARSER_VERSION, SyntheticItem, process_item
from job_cost.schema import JobCostDocument, SourceWorkbook

# Bump when classifier, adapter registry, parser, schema or coordination semantics change.
# Old checkpoints must not be reused under a changed interpretation of source bytes.
PIPELINE_VERSION = "synthetic-batch/v1"
_REASONS = {
    "handled": frozenset({None}),
    "needs_review": frozenset({"unrecognized_shape", "insufficient_metadata", "no_registered_adapter"}),
    "failed": frozenset({"item_error"}),
}


@dataclass(frozen=True)
class CheckpointKey:
    source_id: str
    sha256: str
    pipeline_version: str = PIPELINE_VERSION


class BatchCheckpoint(Protocol):
    """One atomic insert per key; reads must return the entire recorded ItemResult."""

    def get(self, key: CheckpointKey) -> ItemResult | None: ...

    def put_if_absent(self, key: CheckpointKey, result: ItemResult) -> ItemResult: ...


@dataclass
class MemoryCheckpoint:
    """Example checkpoint; lost on process exit. Not safe for parallel writers."""

    records: dict[CheckpointKey, ItemResult] = field(default_factory=dict)

    def get(self, key: CheckpointKey) -> ItemResult | None:
        return self.records.get(key)

    def put_if_absent(self, key: CheckpointKey, result: ItemResult) -> ItemResult:
        return self.records.setdefault(key, result)


@dataclass(frozen=True)
class ItemStatus:
    source_id: str | None  # None if identity is invalid; never echo invalid input
    sha256: str | None
    state: str  # pending, handled, needs_review, failed
    reason: str | None  # stable code only; no exception text or source evidence


@dataclass(frozen=True)
class BatchProgress:
    total: int
    completed: int
    handled: int
    needs_review: int
    failed: int
    pending: int
    items: tuple[ItemStatus, ...]


def _key(item: object) -> CheckpointKey | None:
    try:
        if type(item) is not SyntheticItem:
            return None
        # Reuse the existing immutable identity contract; do not hash extracted
        # values, trust a file path, or silently coerce an invalid digest.
        SourceWorkbook(item.source_id, item.sha256, PARSER_VERSION, "unknown", None, None)
        return CheckpointKey(item.source_id, item.sha256)
    except (ValueError, TypeError):
        return None


def _checked_result(key: CheckpointKey, result: ItemResult) -> ItemResult:
    # A corrupted/mismatched store is a batch-level safety failure, not a reason
    # to reuse a document belonging to another original source or revision.
    if (type(result) is not ItemResult or result.state not in _REASONS
            or result.reason not in _REASONS[result.state]
            or type(result.workbook) is not SourceWorkbook
            or (result.workbook.source_id, result.workbook.sha256) != (key.source_id, key.sha256)
            or result.workbook.parser_version != PARSER_VERSION
            or (result.state == "handled") != (result.document is not None)
            or (result.document is not None and (
                type(result.document) is not JobCostDocument
                or result.document.workbook != result.workbook))):
        raise ValueError("invalid checkpoint record")
    return result


def run_batch(items: tuple[SyntheticItem, ...], checkpoint: BatchCheckpoint,
              *, limit: int | None = None) -> BatchProgress:
    """Process at most `limit` new items; replay terminal records without re-adapting.

    The caller supplies a stable manifest for each resume. A failure or review
    is terminal for this pipeline revision; explicit reprocessing needs a new
    revision or a governed checkpoint reset. No exceptions/source text are logged.
    """
    if type(items) is not tuple or limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("invalid batch arguments")
    keys = tuple(_key(item) for item in items)
    seen: set[str] = set()
    for key in keys:
        if key is not None:
            if key.source_id in seen:
                raise ValueError("duplicate source identity in manifest")
            seen.add(key.source_id)

    statuses = []
    attempted = 0
    for item, key in zip(items, keys):
        if key is None:
            # Unkeyable items cannot be safely checkpointed, but do not block
            # unrelated items. Never expose an unvalidated identifier.
            statuses.append(ItemStatus(None, None, "failed", "invalid_identity"))
            continue
        result = checkpoint.get(key)
        if result is not None:
            result = _checked_result(key, result)
        elif limit is None or attempted < limit:
            result = _checked_result(key, process_item(item))
            attempted += 1
            result = _checked_result(key, checkpoint.put_if_absent(key, result))
        if result is None:
            statuses.append(ItemStatus(key.source_id, key.sha256, "pending", None))
        else:
            statuses.append(ItemStatus(key.source_id, key.sha256, result.state, result.reason))
    counts = {state: sum(s.state == state for s in statuses)
              for state in ("handled", "needs_review", "failed", "pending")}
    return BatchProgress(len(statuses), len(statuses) - counts["pending"],
                         counts["handled"], counts["needs_review"],
                         counts["failed"], counts["pending"], tuple(statuses))
