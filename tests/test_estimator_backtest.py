"""EST-003: invented synthetic-only plan, prediction and completed-job records."""

from dataclasses import replace
from decimal import Decimal as D
import unittest

from estimator.backtest import (
    PROTOCOL_VERSION, PlanScope, PlanSet, ScopeQuantity, LaborHours,
    MaterialQuantity, PredictedTakeoff, CompletedActuals, compare,
)
from estimator.taxonomy import PaintingScope, FinishRequirement

SCOPE = PaintingScope("ceilings", FinishRequirement("paint", "flat"))
SECOND = PaintingScope("doors", FinishRequirement("paint"))
A = "synthetic-room-A/ceiling"
B = "synthetic-room-A/doors"


def fixture():
    """Synthetic records only; no source document or actual business evidence."""
    plan = PlanSet("synthetic-job-A", "synthetic-plan-v1", (
        PlanScope(A, SCOPE, "sq_ft", "synthetic-sheet-1/A"),
        PlanScope(B, SECOND, "count", "synthetic-sheet-1/B"),
    ))
    predicted = PredictedTakeoff(plan.job_ref, plan.plan_ref, "synthetic-takeoff-1", (
        ScopeQuantity(A, SCOPE, D("100"), "sq_ft", "synthetic-p-scope-A"),
        ScopeQuantity(B, SECOND, D("2"), "count", "synthetic-p-scope-B"),
    ), (
        LaborHours(A, D("4"), "synthetic-p-labor-A"),
        LaborHours(B, D("2"), "synthetic-p-labor-B"),
    ), (
        MaterialQuantity(A, "synthetic-paint", D("2"), "gallon", "synthetic-p-material-A"),
        MaterialQuantity(B, "synthetic-paint", D("1"), "gallon", "synthetic-p-material-B"),
    ))
    actual = CompletedActuals(plan.job_ref, plan.plan_ref, "synthetic-completion-1", (
        ScopeQuantity(A, SCOPE, D("90"), "sq_ft", "synthetic-a-scope-A"),
        ScopeQuantity(B, SECOND, D("3"), "count", "synthetic-a-scope-B"),
    ), (
        LaborHours(A, D("5.5"), "synthetic-a-labor-A"),
        LaborHours(B, D("2"), "synthetic-a-labor-B"),
    ), (
        MaterialQuantity(A, "synthetic-paint", D("1.5"), "gallon", "synthetic-a-material-A"),
        MaterialQuantity(B, "synthetic-paint", D("1"), "gallon", "synthetic-a-material-B"),
    ))
    return plan, predicted, actual


class BacktestTests(unittest.TestCase):
    def test_deterministic_variances_and_provenance(self):
        plan, prediction, actual = fixture()
        result = compare(plan, prediction, actual)
        self.assertEqual(result, compare(plan, prediction, actual))
        self.assertEqual((result.protocol_version, result.job_ref, result.plan_ref),
                         (PROTOCOL_VERSION, plan.job_ref, plan.plan_ref))
        self.assertEqual((result.predicted_evidence_ref, result.actual_evidence_ref),
                         (prediction.evidence_ref, actual.evidence_ref))
        self.assertEqual([v.actual_minus_predicted for v in result.scope], [D("-10"), D("1")])
        self.assertEqual([v.actual_minus_predicted for v in result.labor], [D("1.5"), D("0")])
        self.assertEqual([v.actual_minus_predicted for v in result.materials], [D("-0.5"), D("0")])
        self.assertEqual([v.unit for v in result.scope], ["sq_ft", "count"])
        self.assertEqual([v.unit for v in result.labor], ["hours", "hours"])
        self.assertEqual([v.unit for v in result.materials], ["gallon", "gallon"])
        self.assertEqual(result.scope[0].key, (A,))
        self.assertEqual(result.scope[0].predicted, D("100"))
        self.assertEqual(result.scope[0].actual, D("90"))
        self.assertEqual((result.scope[0].plan_evidence_ref, result.scope[0].predicted_evidence_ref,
                          result.scope[0].actual_evidence_ref),
                         ("synthetic-sheet-1/A", "synthetic-p-scope-A", "synthetic-a-scope-A"))
        self.assertEqual(result.labor[0].actual_evidence_ref, "synthetic-a-labor-A")
        self.assertEqual(result.materials[0].predicted_evidence_ref, "synthetic-p-material-A")
        self.assertNotIn("price", result.__dataclass_fields__)

    def test_missing_mismatched_or_extra_evidence_never_compares(self):
        plan, p, a = fixture()
        cases = [
            lambda: compare(replace(plan, plan_ref="synthetic-other-plan"), p, a),
            lambda: compare(plan, replace(p, job_ref="synthetic-other-job"), a),
            lambda: compare(plan, p, replace(a, plan_ref="synthetic-other-plan")),
            lambda: compare(plan, p, replace(a, scopes=a.scopes[:1])),
            lambda: compare(plan, p, replace(a, scopes=a.scopes + (replace(a.scopes[0], scope_id="synthetic-extra"),))),
            lambda: compare(plan, replace(p, scopes=(replace(p.scopes[0], unit="count"), p.scopes[1])), a),
            lambda: compare(plan, p, replace(a, scopes=(replace(a.scopes[0], scope=SECOND), a.scopes[1]))),
            lambda: compare(plan, p, replace(a, materials=(replace(a.materials[0], unit="each"), a.materials[1]))),
            lambda: compare(plan, p, replace(a, materials=(replace(a.materials[0], material_id="synthetic-other"), a.materials[1]))),
            lambda: compare(plan, p, replace(a, labor=(replace(a.labor[0], scope_id="synthetic-other"), a.labor[1]))),
            lambda: compare(plan, p, None),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                case()

    def test_invalid_records_fail_closed(self):
        plan, p, a = fixture()
        for bad in (None, "", "  ", 3):
            with self.subTest(ref=bad), self.assertRaises(ValueError):
                PlanSet(bad, plan.plan_ref, plan.scopes)
            with self.subTest(evidence=bad), self.assertRaises(ValueError):
                replace(p, evidence_ref=bad)
        for bad in (None, 1, 0, D("NaN"), D("Infinity"), D("-1")):
            with self.subTest(quantity=bad), self.assertRaises(ValueError):
                replace(a.scopes[0], quantity=bad)
        for bad in (None, "litre", ""):
            with self.subTest(unit=bad), self.assertRaises(ValueError):
                replace(a.materials[0], unit=bad)
        with self.assertRaises(ValueError):
            replace(a, status="in_progress")
        with self.assertRaises(ValueError):
            replace(plan, scopes=(plan.scopes[0], plan.scopes[0]))
        with self.assertRaises(ValueError):
            replace(p, scopes=(p.scopes[0], p.scopes[0]))
        with self.assertRaises(ValueError):
            replace(a, labor=a.labor[:1])
        with self.assertRaises(ValueError):
            replace(a, materials=a.materials[:1])
        with self.assertRaises(ValueError):
            replace(a, materials=a.materials + (a.materials[0],))
        with self.assertRaises(ValueError):
            replace(a, scopes=())
        with self.assertRaises(ValueError):
            replace(a, scopes=list(a.scopes))
        with self.assertRaises(ValueError):
            replace(a.scopes[0], evidence_ref=" ")
        with self.assertRaises(ValueError):
            replace(plan.scopes[0], scope=3)
        with self.assertRaises(ValueError):
            compare(plan, p, "synthetic-not-actuals")


if __name__ == "__main__":
    unittest.main()
