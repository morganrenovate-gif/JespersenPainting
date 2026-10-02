"""DATA-004: synthetic-only, in-memory adapter dispatch; no workbook I/O.

These layouts are invented exemplars. The registry must not be interpreted as
coverage of any real workbook. Failure reasons deliberately omit source values.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from job_cost.schema import (
    CellProvenance, FIELDS, JobCostDocument, SourceFact, SourceRecord, SourceWorkbook,
)
from job_cost.shape_classifier import ShapeClassification, WorkbookStructure, classify_shape

PARSER_VERSION = "synthetic-cell-input/v1"


@dataclass(frozen=True)
class SyntheticCell:
    """Invented extracted cell; raw_text is evidence, not a computed formula result."""

    sheet: str
    address: str
    raw_text: str
    formula_text: str | None = None


@dataclass(frozen=True)
class SyntheticItem:
    source_id: str
    sha256: str  # caller-supplied original-byte digest; not calculated here
    structure: WorkbookStructure
    cells: tuple[SyntheticCell, ...]


class WorkbookAdapter(Protocol):
    shape_version: str
    version: str

    def adapt(self, item: SyntheticItem, workbook: SourceWorkbook) -> JobCostDocument:
        """Produce source-only facts with provenance; do not alter workbook evidence."""


@dataclass(frozen=True)
class _SingleLaborAdapter:
    shape_version: str
    version: str
    hours_address: str

    def adapt(self, item: SyntheticItem, workbook: SourceWorkbook) -> JobCostDocument:
        if type(item.cells) is not tuple or any(type(c) is not SyntheticCell for c in item.cells):
            raise ValueError("invalid cells")
        cells = {}
        for cell in item.cells:
            key = (cell.sheet, cell.address)
            if key in cells:
                raise ValueError("duplicate cell")
            cells[key] = cell
        # These two invented layouts specify exactly one labor hours cell and
        # one source-reported total. No unrecognized cells are silently ignored.
        if set(cells) != {("Invented Ledger", self.hours_address), ("Invented Summary", "B2")}:
            raise ValueError("missing or unexpected cell")

        def number(cell: SyntheticCell, fact_id: str, field: str) -> SourceFact:
            if type(cell.raw_text) is not str or not cell.raw_text.strip():
                raise ValueError("empty numeric cell")
            try:
                value = Decimal(cell.raw_text)
            except InvalidOperation as exc:
                raise ValueError("invalid numeric cell") from exc
            return SourceFact(fact_id, field, "decimal", "present",
                              CellProvenance(workbook.source_id, cell.sheet, cell.address),
                              cell.raw_text, value, cell.formula_text)

        def record(category: str, record_id: str, values: dict[str, SourceFact]) -> SourceRecord:
            return SourceRecord(record_id, category, tuple(
                values.get(field, SourceFact(f"{record_id}:{field}", field, kind,
                                             "missing", None, None, None))
                for field, kind in FIELDS[category].items()
            ))

        job = record("job", "job", {
            "source_labor_total": number(cells[("Invented Summary", "B2")],
                                         "job:source_labor_total", "source_labor_total"),
        })
        labor = record("labor", "labor:1", {
            "hours": number(cells[("Invented Ledger", self.hours_address)],
                            "labor:1:hours", "hours"),
        })
        return JobCostDocument(workbook, job, (labor,), (), ())


# Exact classifier shape versions, with separate, explicit adapter versions.
_ADAPTERS: dict[str, WorkbookAdapter] = {
    "synthetic-ledger/v1": _SingleLaborAdapter("synthetic-ledger/v1", "synthetic-ledger-adapter/v1", "B2"),
    "synthetic-ledger/v2": _SingleLaborAdapter("synthetic-ledger/v2", "synthetic-ledger-adapter/v2", "C3"),
}


def select_adapter(classification: ShapeClassification) -> WorkbookAdapter | None:
    """Only an exact known classification can select a registered adapter."""
    if (type(classification) is not ShapeClassification or classification.state != "known"
            or classification.signature is None or classification.review_reason is not None):
        return None
    adapter = _ADAPTERS.get(classification.shape_version)
    return adapter if adapter is not None and adapter.shape_version == classification.shape_version else None


@dataclass(frozen=True)
class ItemResult:
    state: str  # handled, needs_review, failed
    workbook: SourceWorkbook | None
    classification: ShapeClassification | None
    document: JobCostDocument | None
    reason: str | None  # stable code; no raw content or exception message


def process_item(item: SyntheticItem) -> ItemResult:
    """Classify, dispatch and validate one item; never guess an unknown layout."""
    classification = None
    workbook = None
    try:
        if type(item) is not SyntheticItem:
            raise ValueError("invalid item")
        classification = classify_shape(item.structure)
        adapter = select_adapter(classification)
        # A recognized shape with no registered adapter is still review work,
        # not permission to record a known shape with a guessed adapter.
        selected = adapter is not None
        workbook = SourceWorkbook(item.source_id, item.sha256, PARSER_VERSION,
                                  "known" if selected else "unknown",
                                  classification.shape_version if selected else None,
                                  adapter.version if selected else None)
        if not selected:
            return ItemResult("needs_review", workbook, classification, None,
                              classification.review_reason or "no_registered_adapter")
        document = adapter.adapt(item, workbook)
        if type(document) is not JobCostDocument or document.workbook != workbook:
            raise ValueError("adapter contract violation")
        return ItemResult("handled", workbook, classification, document, None)
    except Exception:
        # Per-item boundary: a malformed input or adapter error cannot terminate
        # another item. No source text or exception details escape into results.
        return ItemResult("failed", workbook, classification, None, "item_error")


def process_items(items: tuple[SyntheticItem, ...]) -> tuple[ItemResult, ...]:
    """Repository-only item isolation, not a resumable/persisted batch importer."""
    return tuple(process_item(item) for item in items)
