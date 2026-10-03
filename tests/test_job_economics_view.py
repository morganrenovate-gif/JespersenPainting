"""Invented synthetic-only ECON-003 owner-view examples; no operational records."""

import unittest
from dataclasses import replace
from decimal import Decimal
from html.parser import HTMLParser

from job_cost.schema import CellProvenance, SourceFact
from job_economics.model import ComparisonLink, FactRef, SourceEvidence
from job_economics.view import render_job_economics, stylesheet
from test_job_economics_model import invented_job


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.hrefs = []
        self.headers = []
        self.states = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if "href" in attributes:
            self.hrefs.append(attributes["href"])
        if tag in ("main", "section", "table", "th"):
            self.headers.append((tag, attributes))
        if "data-state" in attributes:
            self.states.append(attributes["data-state"])


class SyntheticOwnerViewTests(unittest.TestCase):
    def setUp(self):
        self.job = invented_job()
        self.invoice = FactRef("invoices", "synthetic-invoices-source", "synthetic-row-1", "synthetic-fact-1")
        self.accounting = FactRef("quickbooks", "synthetic-quickbooks-source", "synthetic-row-1", "synthetic-fact-1")
        self.link = ComparisonLink(self.invoice, self.accounting, "invented_amount")

    def test_all_sources_are_distinct_and_values_have_locators(self):
        html = render_job_economics(self.job)
        tree = Structure()
        tree.feed(html)
        self.assertEqual(len([entry for entry in tree.headers if entry[0] == "section" and
                              entry[1].get("class") == "source"]), 8)
        for label in ("Estimate", "Change orders", "Time", "Labor cost", "Materials",
                      "Vendor invoices", "QuickBooks", "Historical workbooks"):
            self.assertIn(label, html)
        self.assertIn("synthetic-field-1", html)
        self.assertIn("synthetic-invoices-source", html)
        self.assertIn("synthetic-quickbooks-source", html)
        self.assertIn("source_labor_total", html)
        self.assertIn("Not reported", html)
        self.assertIn("19.25", html)
        self.assertNotIn("$19.25", html)  # no assumed currency
        self.assertIn("No explicit comparisons supplied", html)
        self.assertIn("cannot be concluded", html)

    def test_workbook_source_fact_shows_cell_and_value_without_promoting_metrics(self):
        record = self.job.historical_workbooks.records[0]
        book = record.workbook
        original = book.job.facts[2]  # source_labor_total in synthetic workbook
        updated = replace(original, state="present", value=Decimal("44.20"),
                          raw_text="44.20", provenance=CellProvenance("synthetic-book-01", "Synthetic Sheet", "B2"))
        updated_job = replace(book.job, facts=book.job.facts[:2] + (updated,) + book.job.facts[3:])
        updated_book = replace(book, job=updated_job)
        job = replace(self.job, historical_workbooks=replace(self.job.historical_workbooks,
            records=(replace(record, workbook=updated_book),)))
        html = render_job_economics(job)
        self.assertIn("Synthetic Sheet!B2", html)
        self.assertIn("44.20", html)
        self.assertIn("Workbook source-reported", html)
        self.assertIn("recomputed metrics and discrepancies require separate source review", html)

    def test_linked_conflict_has_two_navigable_full_references_and_no_unlinked_join(self):
        record = self.job.quickbooks.records[0]
        altered = replace(record, facts=(replace(record.facts[0], value=Decimal("31.00")), record.facts[1]))
        job = replace(self.job, quickbooks=replace(self.job.quickbooks, records=(altered,)))
        html = render_job_economics(job, (self.link,))
        tree = Structure()
        tree.feed(html)
        self.assertIn("Conflict — source values differ", html)
        self.assertIn("In conflict — job result unresolved", html)
        self.assertIn("31.00", html)
        self.assertIn("invoices / synthetic-invoices-source", html.lower())
        self.assertIn("quickbooks / synthetic-quickbooks-source", html.lower())
        fragments = [href for href in tree.hrefs if href.startswith("#")]
        self.assertTrue(fragments)
        for href in fragments:
            self.assertIn(href[1:], tree.ids)
        self.assertEqual(html.count("Compared field:"), 1)
        self.assertNotIn("Conflict — source values differ", render_job_economics(job))
        self.assertEqual(job.invoices.records[0].facts[0].value, Decimal("19.25"))
        self.assertEqual(render_job_economics(self.job, (self.link,)).count("Agree — linked source values match"), 1)

    def test_missing_stale_review_error_and_retained_values_are_not_fresh_or_zero(self):
        job = replace(self.job, invoices=SourceEvidence("invoices", "missing", ()),
                      quickbooks=replace(self.job.quickbooks, state="stale"),
                      time=SourceEvidence("time", "error", ()),
                      labor=replace(self.job.labor, state="needs_review"))
        html = render_job_economics(job)
        tree = Structure()
        tree.feed(html)
        for state in ("missing", "stale", "error", "needs_review"):
            self.assertIn(state, tree.states)
        self.assertIn("4 source coverage exception(s)", html)
        self.assertIn("Retained · stale", html)
        self.assertIn("No source records supplied. Not zero.", html)
        self.assertIn("Not current evidence", html)
        self.assertNotIn("0.00", html)
        stale_record = self.job.quickbooks.records[0]
        changed = replace(stale_record, facts=(replace(stale_record.facts[0], value=Decimal("31.00")),
                                               stale_record.facts[1]))
        retained = replace(self.job, quickbooks=SourceEvidence("quickbooks", "stale", (changed,)))
        linked = render_job_economics(retained, (self.link,))
        self.assertIn("Conflict — source values differ · retained source; freshness unresolved", linked)
        self.assertIn("Retained · stale", linked)

    def test_uncomparable_link_and_unsafe_text_do_not_invent_agreement_or_inject_markup(self):
        record = self.job.quickbooks.records[0]
        changed = replace(record, facts=(replace(record.facts[0], value="19.25"), record.facts[1]))
        job = replace(self.job, job_id='<script>alert(1)</script>',
                      quickbooks=replace(self.job.quickbooks, records=(changed,)))
        html = render_job_economics(job, (self.link,))
        self.assertIn("Not comparable — value types differ", html)
        self.assertNotIn("Agree —", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        with self.assertRaises(ValueError):
            render_job_economics(job, (ComparisonLink(self.invoice,
                FactRef("quickbooks", "synthetic-quickbooks-source", "absent", "synthetic-fact-1"),
                "invented_amount"),))

    def test_semantic_mobile_focus_and_motion_contract(self):
        html = render_job_economics(self.job)
        css = stylesheet()
        tree = Structure()
        tree.feed(html)
        self.assertIn('name="viewport"', html)
        self.assertIn('href="view.css"', html)
        self.assertIn('href="#main"', html)
        self.assertIn(("main", {"id": "main"}), tree.headers)
        self.assertTrue(any(tag == "th" and attrs.get("scope") == "col" for tag, attrs in tree.headers))
        self.assertTrue(any(tag == "th" and attrs.get("scope") == "row" for tag, attrs in tree.headers))
        self.assertIn("@media (max-width: 700px)", css)
        self.assertIn("grid-template-columns: 1fr", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn("env(safe-area-inset-left)", css)


if __name__ == "__main__":
    unittest.main()

