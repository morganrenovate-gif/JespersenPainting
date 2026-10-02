"""CONTROL-003 v1: private-lane workbook intake; no provider transport or runtime I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from job_cost.adapters import PARSER_VERSION, ItemResult, SyntheticItem
from job_cost.batch import PIPELINE_VERSION, CheckpointKey, MemoryCheckpoint, run_batch
from job_cost.calculation import CALCULATION_VERSION, recompute
from job_cost.inventory import InventoryRecord
from job_cost.schema import JobCostDocument

WORKER_VERSION = "private-intake/v1"
CLIENT = "jespersen-painting"
ENVIRONMENT = "staging"


def _opaque(value: object) -> bool:
    return type(value) is str and value.isascii() and 1 <= len(value) <= 128 and all(
        c.isalnum() or c in "_-" for c in value)


@dataclass(frozen=True)
class RuntimeScope:
    client: str
    environment: str
    root_id: str  # injected opaque provider ID, never a path

    def __post_init__(self) -> None:
        if self.client != CLIENT or self.environment != ENVIRONMENT or not _opaque(self.root_id):
            raise ValueError("invalid staging scope")


@dataclass(frozen=True)
class FileRef:
    file_id: str
    parent_id: str
    inventory: InventoryRecord


@dataclass(frozen=True)
class ReadResult:
    file_id: str
    parent_id: str
    content: bytes  # transient, never included in public progress


class ReadProvider(Protocol):
    def list_children(self, root_id: str) -> tuple[FileRef, ...]: ...
    def read_file(self, file_id: str) -> ReadResult: ...


class ReadOnlyBoundary:
    """Exactly two allowlisted operations, no generic provider method forwarding."""

    def __init__(self, provider: ReadProvider, root_id: str):
        if not _opaque(root_id):
            raise ValueError("invalid root")
        self._provider, self._root = provider, root_id

    def execute(self, operation: str, *, ref: FileRef | None = None):
        if operation == "list" and ref is None:
            entries = self._provider.list_children(self._root)
            if type(entries) is not tuple:
                raise ValueError("invalid listing")
            return entries
        if operation == "read" and type(ref) is FileRef:
            self.check_ref(ref)
            result = self._provider.read_file(ref.file_id)
            if (type(result) is not ReadResult or result.file_id != ref.file_id
                    or result.parent_id != self._root or type(result.content) is not bytes):
                raise ValueError("read outside root or invalid response")
            return result.content
        raise ValueError("operation not permitted")

    def check_ref(self, ref: FileRef) -> None:
        if (type(ref) is not FileRef or not _opaque(ref.file_id)
                or ref.parent_id != self._root or type(ref.inventory) is not InventoryRecord
                or ref.inventory.file_status != "available"
                or ref.inventory.ingest_status != "pending"):
            raise ValueError("reference outside root or invalid inventory")


class CellParser(Protocol):
    """Injected decoder returning the existing synthetic adapter input contract.

    Built-in adapters cover invented layouts only; no real-client coverage implied.
    """
    version: str

    def parse(self, content: bytes, source_id: str, digest: str) -> SyntheticItem: ...


@dataclass(frozen=True)
class PrivateRecord:
    scope: RuntimeScope
    version: str
    key: CheckpointKey
    file_id: str
    state: str
    reason: str | None  # stable code, no exception text
    result: ItemResult | None  # private source evidence; never publish
    recomputed: JobCostDocument | None  # private derived evidence
    fingerprint: str | None
    calculation_version: str | None
    steps: tuple[str, ...]


class PrivateCheckpoint(Protocol):
    """Governed implementation must atomically enforce unique immutable source IDs."""
    def get(self, source_id: str) -> PrivateRecord | None: ...
    def put_if_absent(self, record: PrivateRecord) -> PrivateRecord: ...


@dataclass
class MemoryPrivateCheckpoint:
    """Synthetic single-writer example only; not durable or concurrent-safe."""
    records: dict[str, PrivateRecord] = field(default_factory=dict)

    def get(self, source_id: str) -> PrivateRecord | None:
        return self.records.get(source_id)

    def put_if_absent(self, record: PrivateRecord) -> PrivateRecord:
        previous = self.get(record.key.source_id)
        if previous is not None:
            if previous.key != record.key or previous.scope != record.scope or previous.file_id != record.file_id:
                raise ValueError("immutable checkpoint identity changed")
            return previous
        self.records[record.key.source_id] = record
        return record


@dataclass(frozen=True)
class PublicProgress:
    """Counts only; no ID, hash, fingerprint, formula, payload or locator."""
    total: int
    completed: int
    handled: int
    needs_review: int
    failed: int
    pending: int


def _validate_record(record: PrivateRecord, scope: RuntimeScope, ref: FileRef, key: CheckpointKey) -> None:
    if (type(record) is not PrivateRecord or record.scope != scope or record.version != WORKER_VERSION
            or record.key != key or record.file_id != ref.file_id
            or record.state not in ("handled", "needs_review", "failed")
            or record.steps[-1:] != ("committed",)):
        raise ValueError("invalid private checkpoint")
    if record.result is not None:
        result = record.result
        if (type(result) is not ItemResult or result.state != record.state
                or result.reason != record.reason or result.workbook is None
                or result.workbook.source_id != key.source_id or result.workbook.sha256 != key.sha256
                or result.workbook.parser_version != PARSER_VERSION
                or record.fingerprint != (result.classification.signature if result.classification else None)):
            raise ValueError("invalid private result")
        if record.state == "handled":
            if (type(record.recomputed) is not JobCostDocument or result.document is None
                    or record.recomputed.workbook != result.document.workbook
                    or record.calculation_version != CALCULATION_VERSION):
                raise ValueError("invalid recomputation checkpoint")
        elif record.recomputed is not None or record.calculation_version is not None:
            raise ValueError("review/failure cannot claim recomputation")
    elif (record.state != "failed" or record.reason not in
          ("boundary_rejected", "read_error", "digest_mismatch", "parser_error")
          or record.recomputed is not None or record.fingerprint is not None):
        raise ValueError("invalid failed checkpoint")


def intake(scope: RuntimeScope, provider: ReadProvider, parser: CellParser,
           checkpoint: PrivateCheckpoint, *, limit: int | None = None) -> PublicProgress:
    """Bounded new attempts in manifest order; terminal checkpoints replay.

    A changed original requires a new governed source ID/revision. No retry
    of terminal failures or review states within this pipeline revision.
    """
    if (type(scope) is not RuntimeScope or (limit is not None and (type(limit) is not int or limit < 0))
            or parser.version != PARSER_VERSION):
        raise ValueError("invalid worker configuration")
    boundary = ReadOnlyBoundary(provider, scope.root_id)
    refs = boundary.execute("list")
    seen: set[str] = set()
    file_ids: set[str] = set()
    existing = []
    # Validate the entire manifest/checkpoint before beginning any read or write.
    for ref in refs:
        if type(ref) is not FileRef or type(ref.inventory) is not InventoryRecord:
            raise ValueError("invalid manifest")
        inv = ref.inventory
        if inv.source_id in seen or ref.file_id in file_ids:
            raise ValueError("duplicate manifest identity")
        seen.add(inv.source_id)
        file_ids.add(ref.file_id)
        key = CheckpointKey(inv.source_id, inv.sha256, PIPELINE_VERSION)
        previous = checkpoint.get(inv.source_id)
        if previous is not None:
            if type(previous) is not PrivateRecord or previous.key != key:
                raise ValueError("immutable source changed")
            _validate_record(previous, scope, ref, key)
            if previous.reason != "boundary_rejected":
                boundary.check_ref(ref)
        existing.append((ref, key, previous))
    counts = dict(handled=0, needs_review=0, failed=0, pending=0)
    attempted = 0
    for ref, key, previous in existing:
        inv = ref.inventory
        if previous is not None:
            state = previous.state
        elif limit is not None and attempted >= limit:
            state = "pending"
        else:
            attempted += 1
            steps = ["listed"]
            result = computed = fingerprint = calculation_version = None
            try:
                boundary.check_ref(ref)
                steps.append("boundary_checked")
            except ValueError:
                state, reason = "failed", "boundary_rejected"
            else:
                try:
                    content = boundary.execute("read", ref=ref)
                    if sha256(content).hexdigest() != inv.sha256:
                        state, reason = "failed", "digest_mismatch"
                    else:
                        steps.append("read_verified")
                        item = parser.parse(content, inv.source_id, inv.sha256)
                        if (type(item) is not SyntheticItem or item.source_id != inv.source_id
                                or item.sha256 != inv.sha256):
                            raise ValueError("invalid parser output")
                        # Reuse existing batch classifier, adapter and checkpoint checks.
                        store = MemoryCheckpoint()
                        run_batch((item,), store)
                        result = store.get(key)
                        state, reason = result.state, result.reason
                        fingerprint = result.classification.signature if result.classification else None
                        steps.append("classified_adapted")
                        if state == "handled":
                            # No category coverage assertion from synthetic adapters.
                            computed = recompute(result.document, ())
                            calculation_version = CALCULATION_VERSION
                            steps.append("recomputed")
                except Exception:
                    state, reason = "failed", "parser_error" if "read_verified" in steps else "read_error"
                    result = computed = fingerprint = calculation_version = None
            steps.append("committed")
            record = PrivateRecord(scope, WORKER_VERSION, key, ref.file_id, state, reason,
                                   result, computed, fingerprint, calculation_version, tuple(steps))
            _validate_record(record, scope, ref, key)
            saved = checkpoint.put_if_absent(record)
            _validate_record(saved, scope, ref, key)
            state = saved.state
        counts[state] += 1
    total = len(refs)
    return PublicProgress(total, total - counts["pending"], counts["handled"],
                          counts["needs_review"], counts["failed"], counts["pending"])
