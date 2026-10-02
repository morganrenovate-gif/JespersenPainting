"""Invented synthetic-only ECON-001 fixtures; no operational records."""

import unittest
from dataclasses import replace
from decimal import Decimal

from job_cost.schema import JobCostDocument, SourceRecord, SourceWorkbook, FIELDS, SourceFact
from job_economics.model import (
    CATEGORIES, SCHEMA_VERSION, EvidenceFact, EvidenceRecord, JobEconomics, SourceEvidence,
)


def synthetic_workbook():
    # Invented, empty job-cost source document; no real workbook or provider row.
    workbook = SourceWorkbook("synthetic-book-01", "a" * 64, "synthetic-parser/1",
                              "known", "synthetic-shape/1", "synthetic-adapter/1")
    job = SourceRecord("synthetic-book-job", "job", tuple(
        SourceFact(f"synthetic-{field}", field, kind, "missing", None, None, None)
        for field, kind in FIELDS["job"].items()
    ))
    return JobCostDocument(workbook, job, (), (), ())


def invented_record(category, source_id=None, value=Decimal("19.25")):
    source_id = source_id or f"synthetic-{category}-source"
    return EvidenceRecord(category, source_id, "synthetic-row-1", (
        EvidenceFact("synthetic-fact-1", "invented_amount", "present", "synthetic-field-1", value),
        EvidenceFact("synthetic-fact-2", "uncertain_amount", "unknown", "synthetic-field-2", None),
    ))


def invented_job():
    slots = {category: SourceEvidence(category, "available", (invented_record(category),))
             for category in CATEGORIES}
    slots["historical_workbooks"] = SourceEvidence("historical_workbooks", "available", (
        EvidenceRecord("historical_workbooks", "synthetic-book-01", "synthetic-row-1", (), synthetic_workbook()),
    ))
    return JobEconomics("synthetic-job-01", **slots)


class SyntheticEconomicsTests(unittest.TestCase):
    def test_all_seven_backlog_groups_remain_distinct_with_identity_and_state(self):
        job = invented_job()
        self.assertEqual(job.schema_version, SCHEMA_VERSION)
        self.assertEqual(len(CATEGORIES), 8)  # time/labor are deliberately separate
        for category in CATEGORIES:
            source = getattr(job, category)
            self.assertEqual(source.category, category)
            self.assertEqual(source.state, "available")
            self.assertEqual(source.records[0].category, category)
            self.assertTrue(source.records[0].source_id.startswith("synthetic-"))
        self.assertIsInstance(job.historical_workbooks.records[0].workbook, JobCostDocument)
        self.assertEqual(job.historical_workbooks.records[0].workbook.workbook.sha256, "a" * 64)
        self.assertEqual(job.estimate.records[0].facts[1].state, "unknown")
        self.assertNotEqual(job.time.records[0].source_id, job.labor.records[0].source_id)

    def test_identical_values_and_fact_ids_from_different_sources_do_not_merge(self):
        job = invented_job()
        for category in ("estimate", "change_orders", "time", "labor", "materials", "invoices", "quickbooks"):
            fact = getattr(job, category).records[0].facts[0]
            self.assertEqual((fact.id, fact.value), ("synthetic-fact-1", Decimal("19.25")))
        changed_qb = replace(job.quickbooks.records[0], facts=(
            EvidenceFact("synthetic-fact-1", "invented_amount", "present", "synthetic-field-1", Decimal("31.00")),
            job.quickbooks.records[0].facts[1],
        ))
        updated = replace(job, quickbooks=replace(job.quickbooks, records=(changed_qb,)))
        self.assertEqual(updated.quickbooks.records[0].facts[0].value, Decimal("31.00"))
        self.assertEqual(updated.invoices.records[0].facts[0].value, Decimal("19.25"))
        self.assertEqual(job.quickbooks.records[0].facts[0].value, Decimal("19.25"))
        self.assertNotIn("metrics", JobEconomics.__dataclass_fields__)

    def test_absence_stale_and_error_are_explicit_not_zero_or_fresh(self):
        job = invented_job()
        missing = SourceEvidence("invoices", "missing", ())
        stale = replace(job.quickbooks, state="stale")
        errored = SourceEvidence("time", "error", ())
        changed = replace(job, invoices=missing, quickbooks=stale, time=errored)
        self.assertEqual(changed.invoices.records, ())
        self.assertEqual(changed.quickbooks.records[0].facts[0].value, Decimal("19.25"))
        self.assertEqual(changed.quickbooks.state, "stale")
        self.assertEqual(changed.time.state, "error")

    def test_invalid_cross_source_or_dangling_evidence_fails_closed(self):
        job = invented_job()
        with self.assertRaises(ValueError):
            replace(job, schema_version="job-economics/v2")
        with self.assertRaises(ValueError):
            replace(job, invoices=job.materials)
        with self.assertRaises(ValueError):
            SourceEvidence("invoices", "missing", job.invoices.records)
        with self.assertRaises(ValueError):
            SourceEvidence("invoices", "available", job.invoices.records * 2)
        with self.assertRaises(ValueError):
            EvidenceRecord("quickbooks", "synthetic-source", "synthetic-row", (), synthetic_workbook())
        with self.assertRaises(ValueError):
            replace(job.historical_workbooks.records[0], source_id="synthetic-other-book")
        with self.assertRaises(ValueError):
            EvidenceFact("synthetic-x", "amount", "present", None, Decimal("1"))
        with self.assertRaises(ValueError):
            EvidenceFact("synthetic-y", "amount", "missing", None, Decimal("0"))
        with self.assertRaises(ValueError):
            EvidenceFact("synthetic-z", "amount", "present", "synthetic-cell", 2.5)


if __name__ == "__main__":
    unittest.main()
