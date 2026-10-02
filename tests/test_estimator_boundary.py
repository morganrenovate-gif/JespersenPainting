"""Synthetic-only EST-002 tests: invented ceiling and source locator, no real plans."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
import unittest

from estimator.boundary import (
    RULE_VERSION, AreaResult, InterpretationProposal, MeasurementReview,
    ReviewedMeasurement, approve_measurement, calculate_ceiling_area,
)
from estimator.taxonomy import FinishRequirement, PaintingScope


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scope = PaintingScope("ceilings", FinishRequirement("paint"))
        self.proposal = InterpretationProposal(
            "synthetic-proposal-A", "synthetic-sheet-A/room-X", self.scope,
            Decimal("99"), Decimal("88"))
        self.review = MeasurementReview(
            "synthetic-proposal-A", "synthetic-reviewer", "synthetic-sheet-A/room-X",
            Decimal("12.5"), Decimal("8"), "approved")

    def test_proposals_cannot_be_measured_or_financial_facts(self):
        self.assertEqual(self.proposal.state, "needs_review")
        for item in (self.proposal, self.review, None):
            with self.subTest(item=item), self.assertRaises(ValueError):
                calculate_ceiling_area(item)
        with self.assertRaises(ValueError):
            approve_measurement(self.proposal, None)
        with self.assertRaises(ValueError):
            ReviewedMeasurement(self.proposal.proposal_id, self.proposal.source_locator,
                                "synthetic-reviewer", self.scope, Decimal(12), Decimal(8))
        with self.assertRaises(FrozenInstanceError):
            self.proposal.state = "measured"

    def test_explicit_review_and_separate_deterministic_rule(self):
        measured = approve_measurement(self.proposal, self.review)
        self.assertIs(type(measured), ReviewedMeasurement)
        self.assertEqual((measured.length_ft, measured.width_ft),
                         (Decimal("12.5"), Decimal("8")))  # not suggested 99 x 88
        result = calculate_ceiling_area(measured)
        self.assertEqual(result, AreaResult(self.proposal.proposal_id,
                         self.proposal.source_locator, "synthetic-reviewer",
                         RULE_VERSION, Decimal("100.0")))
        self.assertNotIn("cost", AreaResult.__dataclass_fields__)
        self.assertNotIn("price", AreaResult.__dataclass_fields__)
        with self.assertRaises(FrozenInstanceError):
            measured.length_ft = Decimal("999")

    def test_mismatched_or_rejected_review_fails_closed(self):
        for change in ({"proposal_id": "other"}, {"evidence_locator": "other"},
                       {"decision": "rejected"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                approve_measurement(self.proposal, replace(self.review, **change))

    def test_incomplete_unsupported_and_malformed_inputs_fail_closed(self):
        for scope in (PaintingScope("walls", FinishRequirement("paint")),
                      PaintingScope("ceilings")):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                approve_measurement(InterpretationProposal("p", "synthetic-loc", scope),
                                    MeasurementReview("p", "reviewer", "synthetic-loc",
                                                      Decimal(4), Decimal(5), "approved"))
        for bad in (None, 5, Decimal(0), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                MeasurementReview("p", "reviewer", "synthetic-loc", bad,
                                  Decimal(5), "approved")
        for bad in (5, Decimal(0), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(suggestion=bad), self.assertRaises(ValueError):
                InterpretationProposal("p", "synthetic-loc", self.scope, bad)
        # Missing suggestions are permitted; missing checked measurements are not.
        proposal = InterpretationProposal("p", "synthetic-loc", self.scope)
        measured = approve_measurement(proposal, MeasurementReview(
            "p", "reviewer", "synthetic-loc", Decimal(4), Decimal(5), "approved"))
        self.assertEqual(calculate_ceiling_area(measured).area_sq_ft, Decimal(20))
        for name in ("proposal_id", "reviewer_ref", "evidence_locator"):
            values = {"proposal_id": "p", "reviewer_ref": "reviewer",
                      "evidence_locator": "synthetic-loc", "checked_length_ft": Decimal(4),
                      "checked_width_ft": Decimal(5), "decision": "approved"}
            values[name] = " "
            with self.subTest(name=name), self.assertRaises(ValueError):
                MeasurementReview(**values)
        with self.assertRaises(ValueError):
            InterpretationProposal("p", "synthetic-loc", self.scope, state="verified")
        with self.assertRaises(ValueError):
            MeasurementReview("p", "reviewer", "synthetic-loc",
                              Decimal(4), Decimal(5), "auto")


if __name__ == "__main__":
    unittest.main()
