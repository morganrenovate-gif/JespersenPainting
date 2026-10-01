"""Version 1 normalized historical job-cost contract (source evidence, not accounting truth).

Adapters populate facts; they must not infer an entity match or turn a formula cache
into a recomputed result. No workbook parsing, storage, or batch execution lives here.
All identifiers are scoped to one document/workbook; importers should persist the
workbook's immutable source_id + sha256 and their own batch/checkpoint state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re

SCHEMA_VERSION = "job-cost/v1"
STATES = frozenset({"present", "missing", "unknown", "malformed", "unsupported"})
KINDS = frozenset({"text", "decimal"})
METRICS = frozenset({"labor_cost", "material_cost", "revenue", "payments", "total_cost", "gross_profit", "gross_margin"})
FIELDS = {
    "job": {"job_reference": "text", "customer_label": "text", "source_labor_total": "decimal",
            "source_material_total": "decimal", "source_revenue_total": "decimal",
            "source_cost_total": "decimal", "source_gross_profit": "decimal",
            "source_gross_margin": "decimal"},
    "labor": {"employee_label": "text", "hours": "decimal", "hourly_cost": "decimal",
              "source_labor_cost": "decimal"},
    "material": {"vendor_label": "text", "description": "text", "quantity": "decimal",
                 "unit_cost": "decimal", "source_material_cost": "decimal"},
    "revenue": {"entry_type": "text", "invoice_reference": "text", "amount": "decimal",
                "source_revenue_total": "decimal"},
}
COMPARABLE_JOB_TOTALS = {
    "source_labor_total": "labor_cost", "source_material_total": "material_cost",
    "source_revenue_total": "revenue", "source_cost_total": "total_cost",
    "source_gross_profit": "gross_profit", "source_gross_margin": "gross_margin",
}
_CELL = re.compile(r"\$?[A-Z]+\$?[1-9][0-9]*\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")


def _text(value: str, name: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _decimal(value: Decimal, name: str) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal (no float coercion)")


@dataclass(frozen=True)
class SourceWorkbook:
    source_id: str  # governed-storage identity, never a public file path
    sha256: str  # hash of original bytes, not the extracted values
    parser_version: str
    shape_state: str  # known or unknown; no guessed adapter for unknown shape
    shape_version: str | None
    adapter_version: str | None

    def __post_init__(self) -> None:
        _text(self.source_id, "source_id")
        _text(self.parser_version, "parser_version")
        if type(self.sha256) is not str or not _HASH.fullmatch(self.sha256):
            raise ValueError("sha256 must be a lowercase 64-digit hex digest")
        if self.shape_state not in ("known", "unknown"):
            raise ValueError("shape_state must be known or unknown")
        if self.shape_state == "known":
            _text(self.shape_version, "shape_version")
            _text(self.adapter_version, "adapter_version")
        elif self.shape_version is not None or self.adapter_version is not None:
            raise ValueError("unknown shape cannot have a selected adapter")


@dataclass(frozen=True)
class CellProvenance:
    workbook_id: str
    sheet_name: str
    cell: str  # A1 notation; sheet is separate so names need not be escaped

    def __post_init__(self) -> None:
        _text(self.workbook_id, "workbook_id")
        _text(self.sheet_name, "sheet_name")
        if type(self.cell) is not str or not _CELL.fullmatch(self.cell):
            raise ValueError("cell must use uppercase A1 notation")


@dataclass(frozen=True)
class SourceFact:
    id: str
    field: str
    kind: str
    state: str
    provenance: CellProvenance | None
    raw_text: str | None  # literal extracted display/cache, never normalized in place
    value: str | Decimal | None
    formula_text: str | None = None  # literal source formula; never executed here

    def __post_init__(self) -> None:
        _text(self.id, "fact id")
        _text(self.field, "field")
        if self.kind not in KINDS or self.state not in STATES:
            raise ValueError("invalid fact kind/state")
        if self.provenance is not None and type(self.provenance) is not CellProvenance:
            raise ValueError("invalid provenance")
        if self.raw_text is not None and type(self.raw_text) is not str:
            raise ValueError("raw_text must be a string or None")
        if self.formula_text is not None and (type(self.formula_text) is not str or not self.formula_text.startswith("=")):
            raise ValueError("formula_text must be a literal formula starting with =")
        if self.state == "present":
            if self.provenance is None or self.raw_text is None:
                raise ValueError("present facts require raw source and cell provenance")
            if self.kind == "decimal":
                _decimal(self.value, "fact value")
            else:
                _text(self.value, "fact value")
        elif self.value is not None:
            raise ValueError("non-present facts may not carry a normalized value")
        if self.provenance is None and (self.raw_text is not None or self.formula_text is not None):
            raise ValueError("source evidence requires provenance")


@dataclass(frozen=True)
class SourceRecord:
    id: str
    category: str  # job, labor, material, revenue
    facts: tuple[SourceFact, ...]

    def __post_init__(self) -> None:
        _text(self.id, "record id")
        if self.category not in FIELDS:
            raise ValueError("unknown record category")
        if type(self.facts) is not tuple:
            raise ValueError("facts must be a tuple")
        seen = set()
        for fact in self.facts:
            if type(fact) is not SourceFact:
                raise ValueError("invalid fact")
            if fact.field in seen or FIELDS[self.category].get(fact.field) != fact.kind:
                raise ValueError("duplicate/unsupported field or incorrect kind")
            seen.add(fact.field)
        # Omitted fields are not treated as zero or NULL. Adapters must report
        # each defined field as present, missing, unknown, malformed or unsupported.
        if seen != FIELDS[self.category].keys():
            raise ValueError("all category fields need explicit states")


@dataclass(frozen=True)
class DerivedMetric:
    id: str
    job_id: str
    name: str
    state: str  # computed, unknown or unsupported
    value: Decimal | None
    input_fact_ids: tuple[str, ...]
    calculation_version: str
    reason: str | None = None

    def __post_init__(self) -> None:
        _text(self.id, "metric id")
        _text(self.job_id, "job_id")
        _text(self.calculation_version, "calculation_version")
        if self.name not in METRICS or self.state not in ("computed", "unknown", "unsupported"):
            raise ValueError("invalid metric name/state")
        if type(self.input_fact_ids) is not tuple or any(type(x) is not str or not x.strip() for x in self.input_fact_ids):
            raise ValueError("input_fact_ids must be a tuple of ids")
        if len(self.input_fact_ids) != len(set(self.input_fact_ids)):
            raise ValueError("duplicate metric input")
        if self.state == "computed":
            _decimal(self.value, "metric value")
            if not self.input_fact_ids or self.reason is not None:
                raise ValueError("computed metric needs inputs and no failure reason")
        elif self.value is not None or not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("uncomputed metric needs a reason, not a value")


@dataclass(frozen=True)
class Discrepancy:
    id: str
    source_fact_id: str
    metric_id: str
    state: str  # differing or unresolved; comparisons are never automatic overwrites
    delta: Decimal | None  # computed minus source, only when both are supported
    reason: str

    def __post_init__(self) -> None:
        for name in ("id", "source_fact_id", "metric_id", "reason"):
            _text(getattr(self, name), name)
        if self.state == "differing":
            _decimal(self.delta, "delta")
            if self.delta == 0:
                raise ValueError("differing delta must be nonzero")
        elif self.state != "unresolved" or self.delta is not None:
            raise ValueError("unresolved discrepancy cannot carry a delta")


@dataclass(frozen=True)
class JobCostDocument:
    workbook: SourceWorkbook
    job: SourceRecord
    rows: tuple[SourceRecord, ...]
    metrics: tuple[DerivedMetric, ...]
    discrepancies: tuple[Discrepancy, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or type(self.workbook) is not SourceWorkbook:
            raise ValueError("unsupported schema version or workbook")
        if type(self.job) is not SourceRecord or self.job.category != "job":
            raise ValueError("document needs one job")
        if any(type(x) is not tuple for x in (self.rows, self.metrics, self.discrepancies)):
            raise ValueError("rows, metrics and discrepancies must be tuples")
        if any(type(row) is not SourceRecord or row.category == "job" for row in self.rows):
            raise ValueError("rows must be labor, material or revenue records")
        records = (self.job,) + self.rows
        facts = {fact.id: fact for record in records for fact in record.facts}
        if len({record.id for record in records}) != len(records) or len(facts) != sum(len(r.facts) for r in records):
            raise ValueError("duplicate record or fact id")
        if any(f.provenance is not None and f.provenance.workbook_id != self.workbook.source_id for f in facts.values()):
            raise ValueError("fact provenance belongs to a different workbook")
        metric_ids = {m.id: m for m in self.metrics}
        if len(metric_ids) != len(self.metrics) or len({m.name for m in self.metrics}) != len(self.metrics):
            raise ValueError("duplicate metric id/name")
        for metric in self.metrics:
            if metric.job_id != self.job.id or any(x not in facts for x in metric.input_fact_ids):
                raise ValueError("metric has dangling input or job reference")
            if metric.state == "computed" and any(facts[x].state != "present" for x in metric.input_fact_ids):
                raise ValueError("computed metric cannot use non-present source facts")
        if len({d.id for d in self.discrepancies}) != len(self.discrepancies):
            raise ValueError("duplicate discrepancy id")
        job_facts = {fact.id for fact in self.job.facts}
        for d in self.discrepancies:
            fact, metric = facts.get(d.source_fact_id), metric_ids.get(d.metric_id)
            if fact is None or metric is None or d.source_fact_id not in job_facts or COMPARABLE_JOB_TOTALS.get(fact.field) != metric.name:
                raise ValueError("discrepancy must reference comparable job total and metric")
            if d.state == "differing":
                if fact.state != "present" or metric.state != "computed" or d.delta != metric.value - fact.value:
                    raise ValueError("discrepancy delta must equal computed minus source")
            elif fact.state == "present" and metric.state == "computed":
                raise ValueError("supported values cannot be unresolved")
