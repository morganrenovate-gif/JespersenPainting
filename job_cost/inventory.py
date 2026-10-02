"""DATA-001: repository-only inventory metadata contract; no workbook I/O.

An InventoryRecord is a snapshot of one original workbook's inventory/review state,
not extracted facts. The caller supplies an original-byte digest from governed storage.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_SOURCE_ID = re.compile(r"src_[a-z0-9]{16,64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"[a-z][a-z0-9_-]*/[1-9][0-9]*\Z")
FILE_STATUSES = frozenset({"available", "missing", "quarantined"})
INGEST_STATUSES = frozenset({"pending", "failed", "ingested"})
REVIEW_STATUSES = frozenset({"pending", "needs_review", "approved"})


@dataclass(frozen=True, slots=True)
class InventoryRecord:
    """One immutable metadata snapshot; never contains a locator, bytes or facts."""

    source_id: str  # opaque identity for an original file, not a job or path
    sha256: str  # caller-supplied SHA-256 of original bytes, not extracted data
    file_status: str
    parser_version: str | None
    adapter_version: str | None
    ingest_status: str
    review_status: str

    def __post_init__(self) -> None:
        if type(self.source_id) is not str or not _SOURCE_ID.fullmatch(self.source_id):
            raise ValueError("source_id must be an opaque src_ identifier")
        if type(self.sha256) is not str or not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must be a lowercase 64-digit hex digest")
        for name, allowed in (("file_status", FILE_STATUSES),
                              ("ingest_status", INGEST_STATUSES),
                              ("review_status", REVIEW_STATUSES)):
            value = getattr(self, name)
            if type(value) is not str or value not in allowed:
                raise ValueError(f"invalid {name}")
        for name in ("parser_version", "adapter_version"):
            version = getattr(self, name)
            if version is not None and (type(version) is not str or not _VERSION.fullmatch(version)):
                raise ValueError(f"{name} must be a versioned identifier or None")
        if self.ingest_status == "pending":
            if self.parser_version is not None or self.adapter_version is not None:
                raise ValueError("pending ingestion cannot claim parser or adapter selection")
        elif self.parser_version is None:
            raise ValueError("attempted ingestion requires a parser version")
        if self.ingest_status == "ingested":
            if self.file_status != "available" or self.adapter_version is None:
                raise ValueError("ingested source must be available with a selected adapter")
        if self.file_status != "available" or self.ingest_status == "failed":
            if self.review_status != "needs_review":
                raise ValueError("unavailable or failed source needs review")
        if self.review_status == "approved" and self.ingest_status != "ingested":
            raise ValueError("only ingested sources may be approved")


def validate_inventory_update(previous: InventoryRecord, current: InventoryRecord) -> None:
    """Reject identity/hash replacement when storing a later status snapshot.

    This does not persist either snapshot or prove original-byte hashing. Storage
    must enforce this check atomically for each source ID, including concurrent writes.
    """
    if type(previous) is not InventoryRecord or type(current) is not InventoryRecord:
        raise ValueError("updates require inventory records")
    if previous.source_id != current.source_id or previous.sha256 != current.sha256:
        raise ValueError("source identity and original-file digest cannot change")
