"""Synthetic-only DATA-005 batch tests; all identities and values invented."""

import unittest
from unittest.mock import patch

from job_cost.adapters import SyntheticCell, SyntheticItem, process_item
from job_cost.batch import MemoryCheckpoint, CheckpointKey, run_batch
from job_cost.shape_classifier import SheetStructure, WorkbookStructure

# Invented layout; not based on a real workbook.
LAYOUT = WorkbookStructure((
    SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Hours"))),
    SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
), True)
UNKNOWN = WorkbookStructure((SheetStructure("Invented Other", (("A1", "Odd"),)),), True)


def item(name, *, hours="2.5", layout=LAYOUT, digest="a" * 64):
    return SyntheticItem(name, digest, layout, (
        SyntheticCell("Invented Ledger", "B2", hours),
        SyntheticCell("Invented Summary", "B2", "72", "=SUM(B3:B5)"),
    ))


class BatchTests(unittest.TestCase):
    def test_resume_and_replay_do_not_duplicate_results(self):
        items = tuple(item(f"synthetic-{i}") for i in range(375))
        store = MemoryCheckpoint()
        first = run_batch(items, store, limit=120)
        self.assertEqual((first.total, first.completed, first.handled, first.pending),
                         (375, 120, 120, 255))
        self.assertEqual(first.items[120].state, "pending")
        # Restart with the same checkpoint. Previously completed results must
        # be read, not re-adapted; limit only counts new attempts.
        with patch("job_cost.batch.process_item", wraps=process_item) as adapt:
            second = run_batch(items, store, limit=10)
            self.assertEqual(adapt.call_count, 10)
        self.assertEqual((second.completed, second.pending), (130, 245))
        done = run_batch(items, store)
        self.assertEqual((done.completed, done.handled, done.pending, len(store.records)),
                         (375, 375, 0, 375))
        original = store.get(CheckpointKey("synthetic-0", "a" * 64))
        self.assertEqual(original.workbook, original.document.workbook)
        self.assertEqual(original.workbook.source_id, "synthetic-0")
        self.assertEqual(original.workbook.sha256, "a" * 64)
        self.assertEqual(original.document.job.facts[2].formula_text, "=SUM(B3:B5)")
        with patch("job_cost.batch.process_item", side_effect=AssertionError("reprocessed")):
            self.assertEqual(run_batch(items, store), done)
        self.assertIs(store.get(CheckpointKey("synthetic-0", "a" * 64)), original)

    def test_failure_review_progress_and_safe_status(self):
        secret = "synthetic-sensitive-cell-marker"
        items = (item("synthetic-bad", hours=secret),
                 item("synthetic-unknown", layout=UNKNOWN), item("synthetic-good"))
        store = MemoryCheckpoint()
        progress = run_batch(items, store)
        self.assertEqual((progress.total, progress.completed, progress.handled,
                          progress.failed, progress.needs_review, progress.pending),
                         (3, 3, 1, 1, 1, 0))
        self.assertEqual(tuple(s.state for s in progress.items),
                         ("failed", "needs_review", "handled"))
        self.assertEqual(progress.items[0].reason, "item_error")
        self.assertEqual(progress.items[1].reason, "unrecognized_shape")
        self.assertNotIn(secret, repr(progress))
        failure = store.get(CheckpointKey("synthetic-bad", "a" * 64))
        self.assertIsNone(failure.document)
        self.assertEqual(failure.workbook.source_id, "synthetic-bad")
        self.assertNotIn(secret, repr(failure))
        self.assertIsNone(store.get(CheckpointKey("synthetic-unknown", "a" * 64)).document)
        self.assertEqual(run_batch(items, store), progress)

    def test_invalid_identity_is_isolated_and_not_persisted(self):
        store = MemoryCheckpoint()
        progress = run_batch((item("synthetic-invalid", digest="bad"), item("synthetic-ok")), store)
        self.assertEqual((progress.failed, progress.handled, len(store.records)), (1, 1, 1))
        self.assertEqual(progress.items[0].state, "failed")
        self.assertEqual(progress.items[0].reason, "invalid_identity")
        self.assertIsNone(progress.items[0].source_id)

    def test_manifest_duplicates_and_corrupt_checkpoint_fail_closed(self):
        store = MemoryCheckpoint()
        with self.assertRaises(ValueError):
            run_batch((item("synthetic-same"), item("synthetic-same", digest="b" * 64)), store)
        self.assertFalse(store.records)
        store.records[CheckpointKey("synthetic-a", "a" * 64)] = process_item(item("synthetic-b"))
        with self.assertRaisesRegex(ValueError, "invalid checkpoint record"):
            run_batch((item("synthetic-a"),), store)


if __name__ == "__main__":
    unittest.main()
