"""Synthetic-only DATA-006 tests; no real workbook or provider data."""

import unittest
from dataclasses import replace
from decimal import Decimal as D

from job_cost.calculation import CALCULATION_VERSION, CategoryEvidence, recompute
from job_cost.schema import CellProvenance, FIELDS, JobCostDocument, SourceFact, SourceRecord, SourceWorkbook

BOOK = SourceWorkbook("synthetic-book", "a" * 64, "parser/1", "known", "invented-shape/1", "adapter/1")


def row(category, key, **values):
    facts = []
    for index, (field, kind) in enumerate(FIELDS[category].items(), 1):
        value = values.get(field)
        state = "present" if value is not None else "missing"
        facts.append(SourceFact(f"{key}:{field}", field, kind, state,
                                CellProvenance(BOOK.source_id, "Synthetic", f"A{index}") if value is not None else None,
                                str(value) if value is not None else None, value))
    return SourceRecord(key, category, tuple(facts))


def fixture(*, labor=True, material=True, invoice=True, payment=True, job_total=D("9")):
    job = row("job", "synthetic-job", source_labor_total=job_total)
    rows = []
    if labor:
        rows.append(row("labor", "synthetic-labor", hours=D("1.25"), hourly_cost=D("7.20"), source_labor_cost=D("999")))
    if material:
        rows.append(row("material", "synthetic-material", quantity=D("2.5"), unit_cost=D("0.40"), source_material_cost=D("999")))
    if invoice:
        rows.append(row("revenue", "synthetic-invoice", entry_type="invoice", amount=D("20"), source_revenue_total=D("999")))
    if payment:
        rows.append(row("revenue", "synthetic-payment", entry_type="payment", amount=D("100")))
    return JobCostDocument(BOOK, job, tuple(rows), (), ())


def evidence(**states):
    return tuple(CategoryEvidence(category, states.get(category, "complete"))
                 for category in ("labor", "material", "revenue", "payments"))


def metrics(doc):
    return {m.name: m for m in doc.metrics}


class CalculationTests(unittest.TestCase):
    def test_arithmetic_payment_separation_and_discrepancy(self):
        source = fixture()
        result = recompute(source, evidence())
        m = metrics(result)
        self.assertEqual({name: metric.value for name, metric in m.items()}, {
            "labor_cost": D("9.0000"), "material_cost": D("1.000"),
            "revenue": D("20"), "payments": D("100"), "total_cost": D("10.0000"),
            "gross_profit": D("10.0000"), "gross_margin": D("0.5000"),
        })
        self.assertEqual({x.calculation_version for x in m.values()}, {CALCULATION_VERSION})
        self.assertEqual(m["labor_cost"].input_fact_ids, ("synthetic-labor:hours", "synthetic-labor:hourly_cost"))
        self.assertEqual(m["material_cost"].input_fact_ids, ("synthetic-material:quantity", "synthetic-material:unit_cost"))
        self.assertEqual(set(m["revenue"].input_fact_ids), {"synthetic-invoice:entry_type", "synthetic-invoice:amount"})
        self.assertEqual(set(m["payments"].input_fact_ids), {"synthetic-payment:entry_type", "synthetic-payment:amount"})
        self.assertNotIn("synthetic-payment:amount", m["gross_profit"].input_fact_ids)
        # Equal totals have no discrepancy in schema v1; differences are explicit.
        self.assertFalse(any(d.source_fact_id == "synthetic-job:source_labor_total" for d in result.discrepancies))
        changed = recompute(fixture(job_total=D("4")), evidence())
        delta = next(d for d in changed.discrepancies if d.source_fact_id == "synthetic-job:source_labor_total")
        self.assertEqual((delta.state, delta.delta), ("differing", D("5.0000")))
        self.assertEqual(next(f for f in changed.job.facts if f.field == "source_labor_total").value, D("4"))
        self.assertEqual(source.metrics, ())
        self.assertEqual(result, recompute(source, evidence()))
        self.assertEqual(result, recompute(result, evidence()))

    def test_multirow_and_negative_delta(self):
        source = fixture(job_total=D("30"))
        more = (row("labor", "synthetic-labor-2", hours=D("2"), hourly_cost=D("3")),
                row("material", "synthetic-material-2", quantity=D("3"), unit_cost=D("2")),
                row("revenue", "synthetic-revenue-2", entry_type="revenue", amount=D("5")),
                row("revenue", "synthetic-payment-2", entry_type="payment", amount=D("7")))
        result = recompute(replace(source, rows=source.rows + more), evidence())
        m = metrics(result)
        self.assertEqual(m["labor_cost"].value, D("15"))
        self.assertEqual(m["material_cost"].value, D("7"))
        self.assertEqual(m["revenue"].value, D("25"))
        self.assertEqual(m["payments"].value, D("107"))
        self.assertEqual(m["gross_profit"].value, D("3"))
        self.assertEqual(m["gross_margin"].value, D("0.12"))
        difference = next(d for d in result.discrepancies if d.source_fact_id == "synthetic-job:source_labor_total")
        self.assertEqual(difference.delta, D("-15"))

    def test_completeness_is_independent_and_empty_is_not_zero(self):
        result = recompute(fixture(), evidence(material="incomplete"))
        m = metrics(result)
        self.assertEqual(m["labor_cost"].state, "computed")
        self.assertEqual(m["revenue"].state, "computed")
        for name in ("material_cost", "total_cost", "gross_profit", "gross_margin"):
            self.assertEqual((m[name].state, m[name].value), ("unknown", None))
        self.assertIn("synthetic-material:quantity", m["total_cost"].input_fact_ids)
        self.assertEqual(metrics(recompute(fixture(labor=False), evidence()))["labor_cost"].state, "unknown")
        self.assertEqual(metrics(recompute(fixture(), ()))["revenue"].state, "unknown")
        self.assertEqual(metrics(recompute(fixture(invoice=False), evidence()))["revenue"].state, "unknown")
        self.assertEqual(metrics(recompute(fixture(payment=False), evidence()))["payments"].state, "unknown")

    def test_missing_and_unsupported_component(self):
        source = fixture()
        missing = row("labor", "synthetic-labor", hours=D("1.25"), source_labor_cost=D("999"))
        doc = replace(source, rows=(missing,) + source.rows[1:])
        m = metrics(recompute(doc, evidence()))
        self.assertEqual((m["labor_cost"].state, m["labor_cost"].value), ("unknown", None))
        self.assertIn("synthetic-labor:hourly_cost", m["labor_cost"].input_fact_ids)
        unsupported = replace(missing.facts[2], state="unsupported")  # hourly_cost
        doc = replace(doc, rows=(replace(missing, facts=missing.facts[:2] + (unsupported,) + missing.facts[3:]),) + doc.rows[1:])
        m = metrics(recompute(doc, evidence()))
        self.assertEqual(m["labor_cost"].state, "unsupported")
        self.assertEqual(m["total_cost"].state, "unsupported")
        self.assertTrue(all(x.value is None for x in (m["labor_cost"], m["total_cost"], m["gross_profit"])))
        self.assertEqual(metrics(recompute(source, evidence(labor="unsupported")))["labor_cost"].state, "unsupported")
        missing_invoice = row("revenue", "synthetic-invoice", entry_type="invoice", source_revenue_total=D("999"))
        doc = replace(source, rows=source.rows[:2] + (missing_invoice,) + source.rows[3:])
        self.assertEqual(metrics(recompute(doc, evidence()))["revenue"].state, "unknown")

    def test_unknown_entry_type_blocks_both_and_no_payment_as_revenue(self):
        source = fixture()
        unknown = row("revenue", "synthetic-unknown", amount=D("7"))
        doc = replace(source, rows=source.rows + (unknown,))
        m = metrics(recompute(doc, evidence()))
        self.assertEqual((m["revenue"].state, m["payments"].state), ("unknown", "unknown"))
        self.assertIn("synthetic-unknown:entry_type", m["revenue"].input_fact_ids)
        self.assertEqual(m["gross_profit"].state, "unknown")
        m = metrics(recompute(fixture(invoice=False), evidence()))
        self.assertEqual((m["payments"].value, m["revenue"].value), (D("100"), None))

    def test_zero_revenue_and_unresolved_comparison(self):
        source = fixture()
        zero = row("revenue", "synthetic-invoice", entry_type="invoice", amount=D("0"))
        job = row("job", "synthetic-job", source_labor_total=D("9"), source_gross_margin=D("0.4"))
        doc = replace(source, job=job, rows=source.rows[:2] + (zero,) + source.rows[3:])
        result = recompute(doc, evidence())
        m = metrics(result)
        self.assertEqual(m["revenue"].value, D("0"))
        self.assertEqual(m["gross_profit"].value, D("-10.0000"))
        self.assertEqual((m["gross_margin"].state, m["gross_margin"].value), ("unknown", None))
        comparison = next(d for d in result.discrepancies if d.source_fact_id == "synthetic-job:source_gross_margin")
        self.assertEqual((comparison.state, comparison.delta), ("unresolved", None))
        self.assertEqual(job, result.job)

    def test_invalid_evidence(self):
        with self.assertRaises(ValueError):
            recompute(fixture(), (CategoryEvidence("labor", "complete"), CategoryEvidence("labor", "complete")))
        with self.assertRaises(ValueError):
            CategoryEvidence("labor", "guess")


if __name__ == "__main__":
    unittest.main()
