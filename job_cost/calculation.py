"""DATA-006: source-separated, in-memory job-cost recomputation (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from job_cost.schema import COMPARABLE_JOB_TOTALS, DerivedMetric, Discrepancy, JobCostDocument

CALCULATION_VERSION = "job-cost-calculation/1"
CATEGORIES = ("labor", "material", "revenue", "payments")


@dataclass(frozen=True)
class CategoryEvidence:
    """Adapter coverage assertion, including when a category has no rows.

    complete asserts all rows were enumerated, not that component facts are
    usable. Incomplete means coverage is uncertain; unsupported means the shape
    cannot supply that category. No state is inferred from workbook subtotals.
    """

    category: str
    state: str

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES or self.state not in ("complete", "incomplete", "unsupported"):
            raise ValueError("invalid category evidence")


def recompute(document: JobCostDocument, evidence: tuple[CategoryEvidence, ...]) -> JobCostDocument:
    """Return new schema-valid results without modifying workbook or source facts.

    No rounding, quantization or coercion. Input IDs include examined component
    and entry-type facts, including non-present facts for unresolved results.
    """
    if type(document) is not JobCostDocument or type(evidence) is not tuple or any(type(e) is not CategoryEvidence for e in evidence):
        raise ValueError("expected document and tuple of category evidence")
    coverage = {e.category: e.state for e in evidence}
    if len(coverage) != len(evidence):
        raise ValueError("duplicate category evidence")

    def metric(name: str, state: str, value: Decimal | None, ids: tuple[str, ...], reason: str | None = None) -> DerivedMetric:
        return DerivedMetric(f"calc:{name}", document.job.id, name, state, value,
                             tuple(dict.fromkeys(ids)), CALCULATION_VERSION, reason)

    def category_metric(category: str, name: str, rows, fields, product=False, extra_ids=()):
        ids = list(extra_ids)
        values = []
        blockers = []
        for row in rows:
            facts = {f.field: f for f in row.facts}
            selected = [facts[f] for f in fields]
            ids.extend(f.id for f in selected)
            if any(f.state != "present" for f in selected):
                blockers.extend(f.state for f in selected if f.state != "present")
            else:
                values.append(selected[0].value * selected[1].value if product else selected[0].value)
        state = coverage.get(category, "incomplete")
        if state == "unsupported" or "unsupported" in blockers:
            return metric(name, "unsupported", None, tuple(ids), "category or component unsupported")
        if state != "complete" or blockers or not rows:
            return metric(name, "unknown", None, tuple(ids),
                          "coverage incomplete, component not present, or no supporting rows")
        return metric(name, "computed", sum(values, Decimal(0)), tuple(ids))

    labor = category_metric("labor", "labor_cost", [r for r in document.rows if r.category == "labor"],
                            ("hours", "hourly_cost"), True)
    materials = category_metric("material", "material_cost", [r for r in document.rows if r.category == "material"],
                                ("quantity", "unit_cost"), True)

    # Unknown/unsupported entry types could be either revenue or payment: block
    # both totals rather than silently omitting a row from either partition.
    revenue_rows = []
    payment_rows = []
    ambiguous = []
    entry_ids = {}
    for row in document.rows:
        if row.category != "revenue":
            continue
        entry = next(f for f in row.facts if f.field == "entry_type")
        if entry.state != "present" or entry.value not in ("invoice", "revenue", "payment"):
            ambiguous.append(entry)
        else:
            entry_ids[row.id] = entry.id
            (payment_rows if entry.value == "payment" else revenue_rows).append(row)

    def entries(category, rows):
        base = category_metric(category, category, rows, ("amount",),
                               extra_ids=tuple(entry_ids[r.id] for r in rows))
        if not ambiguous:
            return base
        ids = base.input_fact_ids + tuple(f.id for f in ambiguous)
        state = "unsupported" if base.state == "unsupported" or any(f.state == "unsupported" for f in ambiguous) else "unknown"
        return metric(category, state, None, ids, "unclassified revenue/payment entry")

    revenue = entries("revenue", revenue_rows)
    payments = entries("payments", payment_rows)

    def combine(name, inputs, operation):
        ids = tuple(fid for m in inputs for fid in m.input_fact_ids)
        if any(m.state != "computed" for m in inputs):
            state = "unsupported" if any(m.state == "unsupported" for m in inputs) else "unknown"
            return metric(name, state, None, ids, "prerequisite not computed")
        return metric(name, "computed", operation(*(m.value for m in inputs)), ids)

    cost = combine("total_cost", (labor, materials), lambda a, b: a + b)
    profit = combine("gross_profit", (revenue, cost), lambda a, b: a - b)
    if revenue.state == "computed" and revenue.value == 0 and profit.state == "computed":
        margin = metric("gross_margin", "unknown", None, profit.input_fact_ids, "zero revenue: margin undefined")
    else:
        margin = combine("gross_margin", (profit, revenue), lambda a, b: a / b)
    metrics = (labor, materials, revenue, payments, cost, profit, margin)
    by_name = {m.name: m for m in metrics}
    comparisons = []
    for fact in document.job.facts:
        if fact.field not in COMPARABLE_JOB_TOTALS:
            continue
        derived = by_name[COMPARABLE_JOB_TOTALS[fact.field]]
        if fact.state == "present" and derived.state == "computed":
            delta = derived.value - fact.value
            if delta == 0:
                continue  # agreement: schema has no agreement record
            comparisons.append(Discrepancy(f"compare:{fact.field}", fact.id, derived.id,
                                           "differing", delta, "computed minus source total"))
        else:
            comparisons.append(Discrepancy(f"compare:{fact.field}", fact.id, derived.id,
                                           "unresolved", None, "source or recomputed total unavailable"))
    return replace(document, metrics=metrics, discrepancies=tuple(comparisons))
