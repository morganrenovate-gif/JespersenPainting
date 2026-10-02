"""Synthetic-only DATA-002 structural classifier tests; no workbook files or client data."""

import unittest

from job_cost.shape_classifier import (
    SheetStructure, WorkbookStructure, classify_shape, structural_signature,
)


# Entirely invented structures, not derived from actual workbooks.
SYNTHETIC_V1 = WorkbookStructure((
    SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Hours"))),
    SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
), True)
SYNTHETIC_V2 = WorkbookStructure((
    SheetStructure("Invented Ledger", (("A2", "Task"), ("C2", "Hours"))),
    SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
), True)


class ShapeClassifierTests(unittest.TestCase):
    def test_known_synthetic_variants_are_explicit_and_distinct(self):
        first = classify_shape(SYNTHETIC_V1)
        second = classify_shape(SYNTHETIC_V2)
        self.assertEqual((first.state, first.shape_version, first.review_reason),
                         ("known", "synthetic-ledger/v1", None))
        self.assertEqual((second.state, second.shape_version, second.review_reason),
                         ("known", "synthetic-ledger/v2", None))
        self.assertNotEqual(first.signature, second.signature)
        self.assertTrue(first.signature.startswith("workbook-structure/v1:"))
        self.assertFalse(hasattr(first, "adapter_version"))

    def test_repeatability_and_enumeration_order_independence(self):
        reordered = WorkbookStructure((
            SYNTHETIC_V1.sheets[1],
            SheetStructure("Invented Ledger", tuple(reversed(SYNTHETIC_V1.sheets[0].headers))),
        ), True)
        for _ in range(5):
            self.assertEqual(classify_shape(SYNTHETIC_V1), classify_shape(reordered))
            self.assertEqual(structural_signature(reordered), structural_signature(SYNTHETIC_V1))

    def test_unknown_shape_never_selects_adapter(self):
        changed = WorkbookStructure((
            SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Minutes"))),
            SYNTHETIC_V1.sheets[1],
        ), True)
        extra = WorkbookStructure(SYNTHETIC_V1.sheets + (
            SheetStructure("Invented Extra", (("A1", "Other"),)),
        ), True)
        for metadata in (changed, extra):
            with self.subTest(metadata=metadata):
                result = classify_shape(metadata)
                self.assertEqual(result.state, "unknown")
                self.assertIsNone(result.shape_version)
                self.assertEqual(result.review_reason, "unrecognized_shape")
                self.assertIsNotNone(result.signature)
                self.assertFalse(hasattr(result, "adapter_version"))

    def test_insufficient_or_ambiguous_metadata_requires_review(self):
        cases = (
            WorkbookStructure(SYNTHETIC_V1.sheets, False),
            WorkbookStructure((), True),
            WorkbookStructure((SheetStructure("Invented Ledger", ()),), True),
            WorkbookStructure((SYNTHETIC_V1.sheets[0], SYNTHETIC_V1.sheets[0]), True),
            WorkbookStructure((SheetStructure("Invented Ledger", (("A1", "Task"), ("A1", "Hours"))),), True),
            WorkbookStructure((SheetStructure("Invented Ledger", (("a1", "Task"),)),), True),
            WorkbookStructure((SheetStructure(" ", (("A1", "Task"),)),), True),
            WorkbookStructure((SheetStructure("Invented Ledger", (("A1", " "),)),), True),
            WorkbookStructure(SYNTHETIC_V1.sheets, 1),
            None,
        )
        for metadata in cases:
            with self.subTest(metadata=metadata):
                result = classify_shape(metadata)
                self.assertEqual((result.state, result.shape_version, result.signature,
                                  result.review_reason),
                                 ("unknown", None, None, "insufficient_metadata"))


if __name__ == "__main__":
    unittest.main()
