"""EST-002: repository-only proposal -> reviewed measurement -> deterministic area.

No document ingestion, verification of review identity, pricing, or accounting authority.
Only rectangular ceiling area is supported; all other rules require a new contract.
"""

from dataclasses import dataclass
from decimal import Decimal

from estimator.taxonomy import PaintingScope

RULE_VERSION = "rectangular-ceiling-area/v1"
_MEASUREMENT_TOKEN = object()


def _text(value: str, field: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be nonempty text")


def _dimension(value: Decimal, field: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise ValueError(f"{field} must be a positive finite Decimal in feet")


@dataclass(frozen=True, slots=True)
class InterpretationProposal:
    """Unverified suggestion, including optional guessed geometry; never a measurement."""

    proposal_id: str
    source_locator: str
    scope: PaintingScope
    suggested_length_ft: Decimal | None = None
    suggested_width_ft: Decimal | None = None
    state: str = "needs_review"

    def __post_init__(self) -> None:
        _text(self.proposal_id, "proposal_id")
        _text(self.source_locator, "source_locator")
        if type(self.scope) is not PaintingScope or self.state != "needs_review":
            raise ValueError("proposal must have a taxonomy scope and needs_review state")
        for name in ("suggested_length_ft", "suggested_width_ft"):
            value = getattr(self, name)
            if value is not None:
                _dimension(value, name)


@dataclass(frozen=True, slots=True)
class MeasurementReview:
    """Explicit reviewer assertion, not proof of plan inspection or authenticated identity.

    Checked dimensions are supplied independently of suggested values; corrections
    are allowed. The evidence locator must match the proposal's source locator.
    """

    proposal_id: str
    reviewer_ref: str
    evidence_locator: str
    checked_length_ft: Decimal
    checked_width_ft: Decimal
    decision: str

    def __post_init__(self) -> None:
        for name in ("proposal_id", "reviewer_ref", "evidence_locator"):
            _text(getattr(self, name), name)
        if self.decision not in ("approved", "rejected"):
            raise ValueError("unsupported review decision")
        _dimension(self.checked_length_ft, "checked_length_ft")
        _dimension(self.checked_width_ft, "checked_width_ft")


@dataclass(frozen=True, slots=True, init=False)
class ReviewedMeasurement:
    """Only issued by approve_measurement in the ordinary API; not financial truth."""

    proposal_id: str
    source_locator: str
    reviewer_ref: str
    scope: PaintingScope
    length_ft: Decimal
    width_ft: Decimal

    def __init__(self, proposal_id, source_locator, reviewer_ref, scope,
                 length_ft, width_ft, *, _token=None):
        if _token is not _MEASUREMENT_TOKEN:
            raise ValueError("measurement requires explicit review")
        object.__setattr__(self, "proposal_id", proposal_id)
        object.__setattr__(self, "source_locator", source_locator)
        object.__setattr__(self, "reviewer_ref", reviewer_ref)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "length_ft", length_ft)
        object.__setattr__(self, "width_ft", width_ft)


def approve_measurement(proposal: InterpretationProposal,
                        review: MeasurementReview) -> ReviewedMeasurement:
    """Validate an explicit review record; never copy suggested dimensions as fact."""
    if type(proposal) is not InterpretationProposal or type(review) is not MeasurementReview:
        raise ValueError("expected proposal and review")
    if (review.decision != "approved" or review.proposal_id != proposal.proposal_id
            or review.evidence_locator != proposal.source_locator):
        raise ValueError("review rejected or does not match proposal evidence")
    if proposal.scope.category != "ceilings" or proposal.scope.finish is None:
        raise ValueError("only ceilings with declared finish are supported for area")
    _dimension(review.checked_length_ft, "checked_length_ft")
    _dimension(review.checked_width_ft, "checked_width_ft")
    return ReviewedMeasurement(proposal.proposal_id, proposal.source_locator,
                               review.reviewer_ref, proposal.scope,
                               review.checked_length_ft, review.checked_width_ft,
                               _token=_MEASUREMENT_TOKEN)


@dataclass(frozen=True, slots=True)
class AreaResult:
    proposal_id: str
    source_locator: str
    reviewer_ref: str
    rule_version: str
    area_sq_ft: Decimal


def calculate_ceiling_area(measurement: ReviewedMeasurement) -> AreaResult:
    """Pure geometric multiplication, never money, labor, or accounting facts."""
    if type(measurement) is not ReviewedMeasurement:
        raise ValueError("only reviewed measurements are accepted")
    if measurement.scope.category != "ceilings" or measurement.scope.finish is None:
        raise ValueError("unsupported scope")
    _dimension(measurement.length_ft, "length_ft")
    _dimension(measurement.width_ft, "width_ft")
    return AreaResult(measurement.proposal_id, measurement.source_locator,
                      measurement.reviewer_ref, RULE_VERSION,
                      measurement.length_ft * measurement.width_ft)
