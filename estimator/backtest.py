"""EST-003 synthetic-only backtest protocol. No plan reading or financial truth.

Caller-supplied provenance references are locators, not verified source evidence.
The comparator fails closed on incomplete or nonmatching records.
"""

from dataclasses import dataclass
from decimal import Decimal

from estimator.taxonomy import PaintingScope

PROTOCOL_VERSION = "synthetic-estimator-backtest/v1"
SCOPE_UNITS = {"sq_ft", "linear_ft", "count"}
MATERIAL_UNITS = {"gallon", "each", "linear_ft"}


def _ref(value, name):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} requires a nonempty reference")


def _quantity(value, name):
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise ValueError(f"{name} requires a nonnegative finite Decimal")


def _unit(value, allowed, name):
    if type(value) is not str or value not in allowed:
        raise ValueError(f"unsupported {name}")


def _rows(rows, kind):
    if type(rows) is not tuple or not rows:
        raise ValueError(f"{kind} requires nonempty tuple of rows")


@dataclass(frozen=True)
class PlanScope:
    scope_id: str
    scope: PaintingScope
    unit: str
    evidence_ref: str

    def __post_init__(self):
        _ref(self.scope_id, "scope_id")
        if type(self.scope) is not PaintingScope:
            raise ValueError("scope requires painting taxonomy")
        _unit(self.unit, SCOPE_UNITS, "scope unit")
        _ref(self.evidence_ref, "plan scope evidence_ref")


@dataclass(frozen=True)
class PlanSet:
    job_ref: str
    plan_ref: str
    scopes: tuple[PlanScope, ...]

    def __post_init__(self):
        _ref(self.job_ref, "job_ref")
        _ref(self.plan_ref, "plan_ref")
        _index(self.scopes, lambda r: r.scope_id, PlanScope, "plan scopes")


@dataclass(frozen=True)
class ScopeQuantity:
    scope_id: str
    scope: PaintingScope
    quantity: Decimal
    unit: str
    evidence_ref: str

    def __post_init__(self):
        _ref(self.scope_id, "scope_id")
        if type(self.scope) is not PaintingScope:
            raise ValueError("scope requires painting taxonomy")
        _quantity(self.quantity, "scope quantity")
        _unit(self.unit, SCOPE_UNITS, "scope unit")
        _ref(self.evidence_ref, "scope evidence_ref")


@dataclass(frozen=True)
class LaborHours:
    scope_id: str
    hours: Decimal
    evidence_ref: str

    def __post_init__(self):
        _ref(self.scope_id, "scope_id")
        _quantity(self.hours, "labor hours")
        _ref(self.evidence_ref, "labor evidence_ref")


@dataclass(frozen=True)
class MaterialQuantity:
    scope_id: str
    material_id: str
    quantity: Decimal
    unit: str
    evidence_ref: str

    def __post_init__(self):
        _ref(self.scope_id, "scope_id")
        _ref(self.material_id, "material_id")
        _quantity(self.quantity, "material quantity")
        _unit(self.unit, MATERIAL_UNITS, "material unit")
        _ref(self.evidence_ref, "material evidence_ref")


@dataclass(frozen=True)
class PredictedTakeoff:
    job_ref: str
    plan_ref: str
    evidence_ref: str
    scopes: tuple[ScopeQuantity, ...]
    labor: tuple[LaborHours, ...]
    materials: tuple[MaterialQuantity, ...]

    def __post_init__(self):
        _validate_record(self)


@dataclass(frozen=True)
class CompletedActuals:
    job_ref: str
    plan_ref: str
    evidence_ref: str
    scopes: tuple[ScopeQuantity, ...]
    labor: tuple[LaborHours, ...]
    materials: tuple[MaterialQuantity, ...]
    status: str = "completed"

    def __post_init__(self):
        if self.status != "completed":
            raise ValueError("actuals must be completed")
        _validate_record(self)


def _index(rows, key, expected_type, kind):
    _rows(rows, kind)
    result = {}
    for row in rows:
        if type(row) is not expected_type:
            raise ValueError(f"invalid {kind} row")
        identity = key(row)
        if identity in result:
            raise ValueError(f"duplicate {kind} key")
        result[identity] = row
    return result


def _validate_record(record):
    _ref(record.job_ref, "job_ref")
    _ref(record.plan_ref, "plan_ref")
    _ref(record.evidence_ref, "record evidence_ref")
    scopes = _index(record.scopes, lambda r: r.scope_id, ScopeQuantity, "scopes")
    labor = _index(record.labor, lambda r: r.scope_id, LaborHours, "labor")
    materials = _index(record.materials, lambda r: (r.scope_id, r.material_id),
                       MaterialQuantity, "materials")
    if scopes.keys() != labor.keys() or {key[0] for key in materials} != scopes.keys():
        raise ValueError("each scope requires labor and at least one material row")


@dataclass(frozen=True)
class Variance:
    key: tuple[str, ...]
    unit: str
    predicted: Decimal
    actual: Decimal
    actual_minus_predicted: Decimal
    plan_evidence_ref: str
    predicted_evidence_ref: str
    actual_evidence_ref: str


@dataclass(frozen=True)
class BacktestReport:
    protocol_version: str
    job_ref: str
    plan_ref: str
    predicted_evidence_ref: str
    actual_evidence_ref: str
    scope: tuple[Variance, ...]
    labor: tuple[Variance, ...]
    materials: tuple[Variance, ...]


def _variance(key, unit, predicted, actual, plan_ref):
    return Variance(key, unit, predicted.quantity if hasattr(predicted, "quantity") else predicted.hours,
                    actual.quantity if hasattr(actual, "quantity") else actual.hours,
                    (actual.quantity if hasattr(actual, "quantity") else actual.hours)
                    - (predicted.quantity if hasattr(predicted, "quantity") else predicted.hours),
                    plan_ref, predicted.evidence_ref, actual.evidence_ref)


def compare(plan: PlanSet, predicted: PredictedTakeoff,
            actual: CompletedActuals) -> BacktestReport:
    """Compare exactly matched synthetic records; never infer missing rows or units."""
    if type(plan) is not PlanSet or type(predicted) is not PredictedTakeoff or type(actual) is not CompletedActuals:
        raise ValueError("plan, prediction and completed actuals are required")
    # Revalidate so even caller-mutated/forged records cannot silently omit rows.
    plan.__post_init__()
    predicted.__post_init__()
    actual.__post_init__()
    if ((predicted.job_ref, predicted.plan_ref) != (plan.job_ref, plan.plan_ref)
            or (actual.job_ref, actual.plan_ref) != (plan.job_ref, plan.plan_ref)):
        raise ValueError("job or plan reference mismatch")
    plan_scopes = _index(plan.scopes, lambda r: r.scope_id, PlanScope, "plan scopes")
    p_scopes = _index(predicted.scopes, lambda r: r.scope_id, ScopeQuantity, "scopes")
    a_scopes = _index(actual.scopes, lambda r: r.scope_id, ScopeQuantity, "scopes")
    if plan_scopes.keys() != p_scopes.keys() or plan_scopes.keys() != a_scopes.keys():
        raise ValueError("scope evidence incomplete or unmatched")
    for key, item in plan_scopes.items():
        if any((row.scope, row.unit) != (item.scope, item.unit)
               for row in (p_scopes[key], a_scopes[key])):
            raise ValueError("scope taxonomy or unit mismatch")
    p_labor = _index(predicted.labor, lambda r: r.scope_id, LaborHours, "labor")
    a_labor = _index(actual.labor, lambda r: r.scope_id, LaborHours, "labor")
    if p_labor.keys() != a_labor.keys() or p_labor.keys() != plan_scopes.keys():
        raise ValueError("labor evidence incomplete or unmatched")
    p_materials = _index(predicted.materials, lambda r: (r.scope_id, r.material_id),
                         MaterialQuantity, "materials")
    a_materials = _index(actual.materials, lambda r: (r.scope_id, r.material_id),
                         MaterialQuantity, "materials")
    if p_materials.keys() != a_materials.keys():
        raise ValueError("material evidence incomplete or unmatched")
    if any(p_materials[key].unit != a_materials[key].unit for key in p_materials):
        raise ValueError("material unit mismatch")
    return BacktestReport(
        PROTOCOL_VERSION, plan.job_ref, plan.plan_ref,
        predicted.evidence_ref, actual.evidence_ref,
        tuple(_variance((key,), plan_scopes[key].unit, p_scopes[key], a_scopes[key],
                        plan_scopes[key].evidence_ref) for key in sorted(plan_scopes)),
        tuple(_variance((key,), "hours", p_labor[key], a_labor[key],
                        plan_scopes[key].evidence_ref) for key in sorted(plan_scopes)),
        tuple(_variance(key, p_materials[key].unit, p_materials[key], a_materials[key],
                        plan_scopes[key[0]].evidence_ref) for key in sorted(p_materials)),
    )
