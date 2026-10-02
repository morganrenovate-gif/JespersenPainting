"""Synthetic-only DATA-004 adapter tests; invented layouts and values only."""

import unittest

from job_cost.adapters import (
    SyntheticCell, SyntheticItem, process_item, process_items, select_adapter,
)
from job_cost.shape_classifier import SheetStructure, WorkbookStructure, classify_shape


# Invented examples, not based on real client workbook structures or rows.
V1 = WorkbookStructure((
    SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Hours"))),
    SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
), True)
V2 = WorkbookStructure((
    SheetStructure("Invented Ledger", (("A2", "Task"), ("C2", "Hours"))),
    SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
), True)


def synthetic_item(layout=V1, hours="2.50", total="72.00", ident="synthetic-1"):
    address = "B2" if layout is V1 else "C3"
    return SyntheticItem(ident, "a" * 64, layout, (
        SyntheticCell("Invented Ledger", address, hours),
        SyntheticCell("Invented Summary", "B2", total, "=SUM(B3:B5)"),
    ))


class AdapterTests(unittest.TestCase):
    def test_registered_shapes_use_distinct_versioned_adapters_and_preserve_evidence(self):
        for layout, shape, adapter_version, address in (
            (V1, "synthetic-ledger/v1", "synthetic-ledger-adapter/v1", "B2"),
            (V2, "synthetic-ledger/v2", "synthetic-ledger-adapter/v2", "C3"),
        ):
            with self.subTest(shape=shape):
                item = synthetic_item(layout=layout)
                selected = select_adapter(classify_shape(layout))
                self.assertEqual(selected.version, adapter_version)
                result = process_item(item)
                self.assertEqual(result.state, "handled")
                self.assertEqual((result.workbook.shape_version, result.workbook.adapter_version),
                                 (shape, adapter_version))
                self.assertEqual(result.document.workbook, result.workbook)
                self.assertEqual(result.document.job.facts[2].raw_text, "72.00")
                self.assertEqual(result.document.job.facts[2].formula_text, "=SUM(B3:B5)")
                self.assertEqual(result.document.job.facts[2].provenance.cell, "B2")
                self.assertEqual(result.document.rows[0].facts[1].provenance.cell, address)
                self.assertEqual(result.document.rows[0].facts[1].raw_text, "2.50")
                self.assertEqual(result.document.metrics, ())
                self.assertEqual(result.document.discrepancies, ())
                self.assertEqual(item.cells[1].raw_text, "72.00")

    def test_malformed_item_does_not_abort_independent_valid_item(self):
        bad = synthetic_item(hours="not-a-number", ident="synthetic-bad")
        good = synthetic_item(layout=V2, ident="synthetic-good")
        results = process_items((bad, good))
        self.assertEqual(tuple(r.state for r in results), ("failed", "handled"))
        self.assertEqual(results[0].reason, "item_error")
        self.assertIsNone(results[0].document)
        self.assertEqual(results[0].workbook.adapter_version, "synthetic-ledger-adapter/v1")
        self.assertEqual(results[1].document.workbook.source_id, "synthetic-good")
        self.assertEqual(results[1].document.workbook.adapter_version, "synthetic-ledger-adapter/v2")
        # Other malformed inputs must also remain item-level failures.
        for malformed in (
            SyntheticItem("synthetic-dup", "b" * 64, V1, bad.cells + (bad.cells[0],)),
            SyntheticItem("synthetic-hash", "invalid", V1, bad.cells),
            synthetic_item(total="NaN"),
        ):
            with self.subTest(malformed=malformed.source_id):
                self.assertEqual(process_items((malformed, good))[1].state, "handled")
                self.assertEqual(process_item(malformed).state, "failed")

    def test_unknown_and_incomplete_require_review_without_selection(self):
        changed = WorkbookStructure((
            SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Minutes"))),
            V1.sheets[1],
        ), True)
        for layout, reason in ((changed, "unrecognized_shape"),
                               (WorkbookStructure(V1.sheets, False), "insufficient_metadata")):
            with self.subTest(reason=reason):
                self.assertIsNone(select_adapter(classify_shape(layout)))
                result = process_item(synthetic_item(layout=layout))
                self.assertEqual((result.state, result.reason), ("needs_review", reason))
                self.assertIsNone(result.document)
                self.assertIsNone(result.workbook.adapter_version)
                self.assertEqual(result.workbook.shape_state, "unknown")
                self.assertIsNone(result.workbook.shape_version)
                self.assertEqual(result.classification.signature is None, reason == "insufficient_metadata")


if __name__ == "__main__":
    unittest.main()
