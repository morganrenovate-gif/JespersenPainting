"""Synthetic-only tests for the versioned job-cost contract."""

import unittest
from dataclasses import replace
from decimal import Decimal

from job_cost.schema import (
    CellProvenance, DerivedMetric, Discrepancy, FIELDS, JobCostDocument,
    SourceFact, SourceRecord, SourceWorkbook,
)


# Every identifier/value here is invented; no client workbook or row was used.
BOOK = SourceWorkbook("synthetic-book-001", "a" * 64, "parser/1", "known", "synthetic-shape/1", "adapter/1")


def row(category, record_id, overrides=None):
    overrides = overrides or {}
    facts = []
    for index, (field, kind) in enumerate(FIELDS[category].items(), 1):
        state, value, raw, formula = overrides.get(field, ("missing", None, None, None))
        provenance = CellProvenance(BOOK.source_id, "Invented Sheet", f"B{index}") if raw is not None else None
        facts.append(SourceFact(f"{record_id}:{field}", field, kind, state, provenance, raw, value, formula))
    return SourceRecord(record_id, category, tuple(facts))


def present(value, formula=None):
    return ("present", value, str(value), formula)


def document():
    job = row("job", "synthetic-job", {
        "job_reference": present("Invented Job"),
        "source_labor_total": present(Decimal("40.00"), "=SUM(B2:B3)"),
    })
    labor = row("labor", "synthetic-labor-1", {
        "employee_label": ("unknown", None, "unreadable", None),
        "hours": present(Decimal("2")),
        "hourly_cost": present(Decimal("25.00")),
        "source_labor_cost": ("malformed", None, "not a number", None),
    })
    metric = DerivedMetric("synthetic-computed-labor", job.id, "labor_cost", "computed",
                           Decimal("50.00"), ("synthetic-labor-1:hours", "synthetic-labor-1:hourly_cost"), "economics/1")
    discrepancy = Discrepancy("synthetic-difference", "synthetic-job:source_labor_total",
                              metric.id, "differing", Decimal("10.00"), "workbook total differs")
    return JobCostDocument(BOOK, job, (labor,), (metric,), (discrepancy,))


class SchemaTests(unittest.TestCase):
    def test_valid_source_and_derived_are_distinct(self):
        doc = document()
        self.assertEqual(doc.job.facts[2].formula_text, "=SUM(B2:B3)")
        self.assertEqual(doc.metrics[0].value, Decimal("50.00"))
        self.assertEqual(doc.discrepancies[0].delta, Decimal("10.00"))
        self.assertEqual(doc.rows[0].facts[0].state, "unknown")
        self.assertEqual(doc.rows[0].facts[3].raw_text, "not a number")
        self.assertIsNone(doc.rows[0].facts[3].value)
        self.assertEqual(doc.job.facts[2].provenance.sheet_name, "Invented Sheet")
        self.assertEqual(doc.workbook.sha256, "a" * 64)
        self.assertEqual(doc.workbook.adapter_version, "adapter/1")

    def test_missing_unknown_unsupported_and_unresolved(self):
        doc = document()
        self.assertEqual(doc.job.facts[1].state, "missing")
        self.assertIsNone(doc.job.facts[1].value)
        unknown = replace(doc.metrics[0], state="unknown", value=None, reason="missing source", input_fact_ids=())
        unresolved = replace(doc.discrepancies[0], state="unresolved", delta=None, reason="cannot compare")
        changed = replace(doc, metrics=(unknown,), discrepancies=(unresolved,))
        self.assertEqual(changed.metrics[0].state, "unknown")
        unknown_book = SourceWorkbook("synthetic-unknown-book", "b" * 64, "parser/1", "unknown", None, None)
        self.assertIsNone(unknown_book.adapter_version)
        unsupported = row("revenue", "synthetic-payment", {"entry_type": present("payment"),
                                                              "amount": ("unsupported", None, "format not supported", None)})
        self.assertEqual(unsupported.facts[2].state, "unsupported")

    def test_all_row_categories_and_source_link(self):
        doc = document()
        material = row("material", "synthetic-material", {"vendor_label": present("Invented Vendor"),
                                                            "quantity": present(Decimal("3"))})
        revenue = row("revenue", "synthetic-invoice", {"entry_type": present("invoice"),
                                                        "amount": present(Decimal("91"))})
        extended = replace(doc, rows=doc.rows + (material, revenue))
        self.assertEqual(tuple(r.category for r in extended.rows), ("labor", "material", "revenue"))
        self.assertEqual(extended.rows[2].facts[2].provenance.workbook_id, BOOK.source_id)

    def test_no_implicit_coercion_or_unattributed_facts(self):
        with self.assertRaises(ValueError):
            SourceFact("synthetic-float", "hours", "decimal", "present", CellProvenance(BOOK.source_id, "Sheet", "A1"), "2.5", 2.5)
        with self.assertRaises(ValueError):
            SourceFact("synthetic-bad", "hours", "decimal", "malformed", CellProvenance(BOOK.source_id, "Sheet", "A1"), "bad", Decimal(0))
        with self.assertRaises(ValueError):
            SourceFact("synthetic-unattributed", "amount", "decimal", "present", None, "10", Decimal(10))
        with self.assertRaises(ValueError):
            SourceRecord("synthetic-incomplete", "material", ())
        with self.assertRaises(ValueError):
            SourceWorkbook("synthetic-bad-book", "c" * 64, "parser/1", "unknown", "guessed", "adapter/1")

    def test_provenance_and_discrepancy_references_are_checked(self):
        doc = document()
        with self.assertRaises(ValueError):
            replace(doc, workbook=replace(doc.workbook, source_id="different-book"))
        with self.assertRaises(ValueError):
            replace(doc, discrepancies=(replace(doc.discrepancies[0], delta=Decimal("11")),))
        with self.assertRaises(ValueError):
            replace(doc, metrics=(replace(doc.metrics[0], input_fact_ids=("absent",)),))
        with self.assertRaises(ValueError):
            replace(doc, metrics=(replace(doc.metrics[0], input_fact_ids=("synthetic-labor-1:employee_label",)),))
        with self.assertRaises(ValueError):
            replace(doc, discrepancies=(replace(doc.discrepancies[0], source_fact_id="absent"),))
        with self.assertRaises(ValueError):
            replace(doc, discrepancies=(replace(doc.discrepancies[0], source_fact_id="synthetic-job:source_material_total"),))


if __name__ == "__main__":
    unittest.main()
