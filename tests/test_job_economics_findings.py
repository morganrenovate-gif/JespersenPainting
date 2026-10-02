"""Clearly invented synthetic ECON-002 evidence; no provider or operational data."""

import unittest
from dataclasses import replace
from decimal import Decimal

from job_economics.model import (
    CATEGORIES, ComparisonLink, FactRef, SourceEvidence, find_evidence,
)
from test_job_economics_model import invented_job


class SyntheticFindingsTests(unittest.TestCase):
    def setUp(self):
        self.job = invented_job()
        self.invoice = FactRef("invoices", "synthetic-invoices-source", "synthetic-row-1", "synthetic-fact-1")
        self.accounting = FactRef("quickbooks", "synthetic-quickbooks-source", "synthetic-row-1", "synthetic-fact-1")
        self.link = ComparisonLink(self.invoice, self.accounting, "invented_amount")

    def test_explicit_link_produces_traceable_conflict_without_mutation(self):
        changed = replace(self.job.quickbooks.records[0], facts=(
            replace(self.job.quickbooks.records[0].facts[0], value=Decimal("31.00")),
            self.job.quickbooks.records[0].facts[1],
        ))
        job = replace(self.job, quickbooks=replace(self.job.quickbooks, records=(changed,)))
        before = repr(job)
        findings = find_evidence(job, (self.link,))
        self.assertEqual(findings.conflicts[0].link, self.link)
        self.assertEqual(len(findings.conflicts), 1)
        self.assertEqual(repr(job), before)
        self.assertEqual(job.invoices.records[0].facts[0].value, Decimal("19.25"))
        self.assertEqual(job.quickbooks.records[0].facts[0].value, Decimal("31.00"))
        self.assertEqual(self.job.quickbooks.records[0].facts[0].value, Decimal("19.25"))
        self.assertEqual(find_evidence(job, (self.link, ComparisonLink(self.accounting, self.invoice,
                                                                      "invented_amount"))).conflicts,
                         findings.conflicts)
        self.assertEqual(find_evidence(job).conflicts, ())  # no inferred join
        self.assertEqual(findings.coverage, ())
        for category in CATEGORIES:
            if category != "quickbooks":
                self.assertIs(getattr(job, category), getattr(self.job, category))

    def test_equal_unlinked_and_non_comparable_facts_do_not_conflict(self):
        self.assertEqual(find_evidence(self.job, (self.link,)).conflicts, ())
        changed = replace(self.job.quickbooks.records[0], facts=(
            replace(self.job.quickbooks.records[0].facts[0], value=Decimal("31.00")),
            self.job.quickbooks.records[0].facts[1],
        ))
        job = replace(self.job, quickbooks=replace(self.job.quickbooks, records=(changed,)))
        self.assertEqual(find_evidence(job).conflicts, ())
        self.assertEqual(find_evidence(job, (ComparisonLink(self.invoice, self.accounting,
                                                            "different_field"),)).conflicts, ())
        unknown = FactRef("quickbooks", "synthetic-quickbooks-source", "synthetic-row-1", "synthetic-fact-2")
        self.assertEqual(find_evidence(job, (ComparisonLink(self.invoice, unknown,
                                                            "invented_amount"),)).conflicts, ())
        text_record = replace(changed, facts=(replace(changed.facts[0], value="31.00"), changed.facts[1]))
        text_job = replace(job, quickbooks=replace(job.quickbooks, records=(text_record,)))
        self.assertEqual(find_evidence(text_job, (self.link,)).conflicts, ())  # no coercion

    def test_coverage_preserves_missing_stale_and_retained_fact_references(self):
        job = replace(self.job, invoices=SourceEvidence("invoices", "missing", ()),
                      quickbooks=replace(self.job.quickbooks, state="stale"),
                      time=SourceEvidence("time", "error", ()))
        findings = find_evidence(job)
        self.assertEqual([(f.category, f.state) for f in findings.coverage],
                         [("time", "error"), ("invoices", "missing"), ("quickbooks", "stale")])
        self.assertEqual(findings.coverage[0].retained_facts, ())
        self.assertEqual(findings.coverage[1].retained_facts, ())
        self.assertEqual(set(findings.coverage[2].retained_facts), {
            self.accounting,
            FactRef("quickbooks", "synthetic-quickbooks-source", "synthetic-row-1", "synthetic-fact-2"),
        })
        self.assertEqual(job.quickbooks.records[0].facts[0].value, Decimal("19.25"))
        self.assertEqual(findings.conflicts, ())

    def test_stale_coverage_is_not_erased_by_a_linked_disagreement(self):
        changed = replace(self.job.quickbooks.records[0], facts=(
            replace(self.job.quickbooks.records[0].facts[0], value=Decimal("31.00")),
            self.job.quickbooks.records[0].facts[1],
        ))
        job = replace(self.job, quickbooks=SourceEvidence("quickbooks", "stale", (changed,)))
        findings = find_evidence(job, (self.link,))
        self.assertEqual(findings.conflicts[0].link.right, self.accounting)
        self.assertEqual(findings.coverage[0].state, "stale")
        self.assertIn(self.accounting, findings.coverage[0].retained_facts)
        self.assertEqual(job.quickbooks.state, "stale")

    def test_invalid_links_fail_closed_without_guessing(self):
        with self.assertRaises(ValueError):
            find_evidence(self.job, (ComparisonLink(self.invoice,
                FactRef("quickbooks", "synthetic-quickbooks-source", "unknown-row", "synthetic-fact-1"),
                "invented_amount"),))
        with self.assertRaises(ValueError):
            ComparisonLink(self.invoice, self.invoice, "invented_amount")
        with self.assertRaises(ValueError):
            ComparisonLink(self.invoice, self.accounting, "")
        with self.assertRaises(ValueError):
            find_evidence(self.job, [self.link])


if __name__ == "__main__":
    unittest.main()
