"""Synthetic-only DATA-001 inventory contract tests; no real workbook metadata."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace

from job_cost.inventory import InventoryRecord, validate_inventory_update


# All identifiers and digests below are invented synthetic placeholders.
SOURCE = "src_abcdef0123456789"
DIGEST = "a" * 64


def record(**changes):
    return InventoryRecord(**({
        "source_id": SOURCE, "sha256": DIGEST, "file_status": "available",
        "parser_version": None, "adapter_version": None,
        "ingest_status": "pending", "review_status": "pending",
    } | changes))


class InventoryTests(unittest.TestCase):
    def test_valid_snapshots_and_status_update(self):
        pending = record()
        failed = record(parser_version="cell-parser/1", ingest_status="failed", review_status="needs_review")
        reviewed = record(parser_version="cell-parser/1", adapter_version="ledger-adapter/2",
                          ingest_status="ingested", review_status="approved")
        self.assertEqual(record(file_status="missing", review_status="needs_review").sha256, DIGEST)
        self.assertEqual(record(file_status="quarantined", review_status="needs_review").source_id, SOURCE)
        self.assertEqual(record(parser_version="cell-parser/1", ingest_status="failed",
                                review_status="needs_review").adapter_version, None)
        self.assertEqual(record(parser_version="cell-parser/1", adapter_version="ledger-adapter/2",
                                ingest_status="ingested", review_status="needs_review").review_status, "needs_review")
        validate_inventory_update(pending, failed)
        validate_inventory_update(failed, reviewed)
        self.assertEqual(tuple(f.name for f in fields(InventoryRecord)), (
            "source_id", "sha256", "file_status", "parser_version", "adapter_version",
            "ingest_status", "review_status"))
        with self.assertRaises(FrozenInstanceError):
            reviewed.sha256 = "b" * 64

    def test_identity_digest_and_version_validation(self):
        for changes in (
            {"source_id": "a/path/file.xlsx"}, {"source_id": "src_ABCDEF0123456789"},
            {"source_id": "src_short"}, {"source_id": 10},
            {"sha256": "b" * 63}, {"sha256": "B" * 64}, {"sha256": 0},
            {"parser_version": "not-versioned"}, {"adapter_version": "adapter/0"},
            {"parser_version": 1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                record(**changes)

    def test_contradictory_statuses_fail_closed(self):
        for changes in (
            {"file_status": "other"}, {"ingest_status": "other"}, {"review_status": "other"},
            {"file_status": "missing"}, {"file_status": "quarantined"},
            {"parser_version": "cell-parser/1"}, {"adapter_version": "ledger-adapter/1"},
            {"ingest_status": "failed"}, {"ingest_status": "ingested"},
            {"ingest_status": "failed", "review_status": "needs_review"},
            {"ingest_status": "ingested", "parser_version": "cell-parser/1",
             "review_status": "needs_review"},
            {"review_status": "approved"},
            {"file_status": "missing", "parser_version": "cell-parser/1",
             "adapter_version": "ledger-adapter/1", "ingest_status": "ingested",
             "review_status": "approved"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                record(**changes)
        with self.assertRaises(ValueError):
            record(parser_version="cell-parser/1", ingest_status="failed", review_status="approved")

    def test_source_identity_and_hash_are_stable_across_snapshots(self):
        initial = record()
        updated = record(parser_version="cell-parser/1", adapter_version="ledger-adapter/1",
                         ingest_status="ingested", review_status="approved")
        validate_inventory_update(initial, updated)
        for altered in (replace(updated, source_id="src_0123456789abcdef"),
                        replace(updated, sha256="b" * 64)):
            with self.assertRaises(ValueError):
                validate_inventory_update(initial, altered)
        with self.assertRaises(ValueError):
            validate_inventory_update(initial, object())


if __name__ == "__main__":
    unittest.main()
