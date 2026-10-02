"""ECON-001/002: source-separated job evidence and explicit findings; in-memory only.

No cross-source join, deduplication, aggregation or source-of-truth promotion.
A record's identity is (category, source_id, record_id), never its label/value.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from job_cost.schema import JobCostDocument

SCHEMA_VERSION = "job-economics/v1"
# The backlog's time/labor group is split so time evidence is never labor cost.
CATEGORIES = (
    "estimate", "change_orders", "time", "labor", "materials",
    "invoices", "quickbooks", "historical_workbooks",
)
COVERAGE_STATES = frozenset({"available", "missing", "needs_review", "stale", "error"})
FACT_STATES = frozenset({"present", "missing", "unknown", "malformed", "unsupported"})


def _nonempty(value: str, name: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be nonempty text")


@dataclass(frozen=True, slots=True)
class EvidenceFact:
    """A literal source assertion, not a reconciled/derived accounting fact.

    locator identifies a field/cell/line within its record's source; it is
    opaque to this model. Values are never coerced to numbers or merged.
    """

    id: str
    field: str
    state: str
    locator: str | None
    value: str | Decimal | None

    def __post_init__(self) -> None:
        _nonempty(self.id, "fact id")
        _nonempty(self.field, "field")
        if self.state not in FACT_STATES:
            raise ValueError("invalid fact state")
        if self.locator is not None:
            _nonempty(self.locator, "locator")
        if self.state == "present":
            if self.locator is None:
                raise ValueError("present fact requires a source locator")
            if type(self.value) is Decimal:
                if not self.value.is_finite():
                    raise ValueError("fact value must be finite")
            else:
                _nonempty(self.value, "fact value")
        elif self.value is not None:
            raise ValueError("non-present fact cannot carry a value")


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    category: str
    source_id: str
    record_id: str
    facts: tuple[EvidenceFact, ...]
    workbook: JobCostDocument | None = None

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError("invalid record category")
        _nonempty(self.source_id, "source_id")
        _nonempty(self.record_id, "record_id")
        if type(self.facts) is not tuple or any(type(f) is not EvidenceFact for f in self.facts):
            raise ValueError("facts must be a tuple of EvidenceFact")
        if not self.facts and self.workbook is None:
            raise ValueError("record needs source facts or a historical document")
        if len({f.id for f in self.facts}) != len(self.facts):
            raise ValueError("duplicate fact id within record")
        if self.workbook is not None:
            if (self.category != "historical_workbooks" or type(self.workbook) is not JobCostDocument
                    or self.workbook.workbook.source_id != self.source_id):
                raise ValueError("historical workbook must match its source identity")


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Coverage is explicit, including an unavailable category with no records.

    Stale/error may retain earlier facts; neither implies those facts are fresh.
    """

    category: str
    state: str
    records: tuple[EvidenceRecord, ...]

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES or self.state not in COVERAGE_STATES:
            raise ValueError("invalid source category/coverage state")
        if type(self.records) is not tuple or any(type(r) is not EvidenceRecord or r.category != self.category for r in self.records):
            raise ValueError("records must belong to their source category")
        if self.state == "missing" and self.records:
            raise ValueError("missing category cannot contain records")
        if self.state == "available" and not self.records:
            raise ValueError("available category needs evidence records")
        if len({(r.source_id, r.record_id) for r in self.records}) != len(self.records):
            raise ValueError("duplicate record identity within category")


@dataclass(frozen=True, slots=True)
class JobEconomics:
    """One job's eight independent source slots; not a computed job margin."""

    job_id: str  # opaque caller-supplied reference; no automatic entity mapping
    estimate: SourceEvidence
    change_orders: SourceEvidence
    time: SourceEvidence
    labor: SourceEvidence
    materials: SourceEvidence
    invoices: SourceEvidence
    quickbooks: SourceEvidence
    historical_workbooks: SourceEvidence
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _nonempty(self.job_id, "job_id")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported job economics schema version")
        for category in CATEGORIES:
            source = getattr(self, category)
            if type(source) is not SourceEvidence or source.category != category:
                raise ValueError(f"{category} must have its own source slot")


@dataclass(frozen=True, slots=True, order=True)
class FactRef:
    """Full source identity of a fact; local fact IDs alone are not join keys."""

    category: str
    source_id: str
    record_id: str
    fact_id: str

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError("invalid fact reference category")
        for name in ("source_id", "record_id", "fact_id"):
            _nonempty(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class ComparisonLink:
    """Caller assertion that exactly two source facts share a comparable field."""

    left: FactRef
    right: FactRef
    comparable_field: str

    def __post_init__(self) -> None:
        if type(self.left) is not FactRef or type(self.right) is not FactRef:
            raise ValueError("comparison requires fact references")
        _nonempty(self.comparable_field, "comparable_field")
        if ((self.left.category, self.left.source_id) ==
                (self.right.category, self.right.source_id)):
            raise ValueError("comparison requires distinct sources")


@dataclass(frozen=True, slots=True)
class ConflictFinding:
    """Trace only: values and accounting authority stay with the source facts."""

    link: ComparisonLink


@dataclass(frozen=True, slots=True)
class CoverageFinding:
    """Non-available category; retained facts are referenced, not made fresh."""

    category: str
    state: str
    retained_facts: tuple[FactRef, ...]


@dataclass(frozen=True, slots=True)
class EconomicsFindings:
    conflicts: tuple[ConflictFinding, ...]
    coverage: tuple[CoverageFinding, ...]


def find_evidence(job: JobEconomics, links: tuple[ComparisonLink, ...] = ()) -> EconomicsFindings:
    """Compare only explicitly linked, present facts of the same literal field/type.

    Missing/stale/review/error coverage remains visible even with no comparisons.
    A dangling link is a caller error, not permission to guess a source match.
    """
    if type(job) is not JobEconomics or type(links) is not tuple or any(
            type(link) is not ComparisonLink for link in links):
        raise ValueError("expected a job and a tuple of comparison links")

    facts: dict[FactRef, EvidenceFact] = {}
    coverage = []
    for category in CATEGORIES:
        source = getattr(job, category)
        retained = []
        for record in source.records:
            for fact in record.facts:
                ref = FactRef(category, record.source_id, record.record_id, fact.id)
                facts[ref] = fact
                retained.append(ref)
        if source.state != "available":
            coverage.append(CoverageFinding(category, source.state, tuple(sorted(retained))))

    # Canonicalize link direction and order; repeated/reversed links do not
    # create duplicate conflicts. Nothing is deduplicated in the source slots.
    pairs = {(min(link.left, link.right), max(link.left, link.right), link.comparable_field)
             for link in links}
    conflicts = []
    for left, right, field in sorted(pairs):
        if left not in facts or right not in facts:
            raise ValueError("comparison references a missing source fact")
        a, b = facts[left], facts[right]
        if (a.state == b.state == "present" and a.field == b.field == field
                and type(a.value) is type(b.value) and a.value != b.value):
            conflicts.append(ConflictFinding(ComparisonLink(left, right, field)))
    return EconomicsFindings(tuple(conflicts), tuple(coverage))
