"""Synthetic-only CONTROL-003 contract tests. All IDs, bytes and values invented."""

import unittest
from unittest.mock import patch

from job_cost.adapters import PARSER_VERSION, SyntheticCell, SyntheticItem
from job_cost.inventory import InventoryRecord
from job_cost.shape_classifier import SheetStructure, WorkbookStructure
from private_runtime.worker import (
    FileRef, ReadResult, RuntimeScope, ReadOnlyBoundary, MemoryPrivateCheckpoint,
    WORKER_VERSION, intake,
)
from hashlib import sha256

ROOT = "synthetic_root"
SCOPE = RuntimeScope("jespersen-painting", "staging", ROOT)
LAYOUT = WorkbookStructure((
    SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Hours"))),
    SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
), True)
UNKNOWN = WorkbookStructure((SheetStructure("Invented Other", (("A1", "Odd"),)),), True)


def ref(index, *, parent=ROOT, content=None):
    content = content if content is not None else f"synthetic-bytes-{index}".encode()
    digest = sha256(content).hexdigest()
    inv = InventoryRecord(f"src_{index:016d}", digest, "available", None, None, "pending", "pending")
    return FileRef(f"synthetic_file_{index}", parent, inv)


class Provider:
    def __init__(self, refs):
        self.refs = refs
        self.reads = []
        self.writes = []

    def list_children(self, root_id):
        assert root_id == ROOT
        return self.refs

    def read_file(self, file_id):
        self.reads.append(file_id)
        index = int(file_id.split("_")[-1])
        return ReadResult(file_id, ROOT, f"synthetic-bytes-{index}".encode())

    def delete_file(self, *args):
        self.writes.append(args)


class Parser:
    version = PARSER_VERSION

    def __init__(self, layout=LAYOUT):
        self.calls = 0
        self.layout = layout

    def parse(self, content, source_id, digest):
        self.calls += 1
        return SyntheticItem(source_id, digest, self.layout, (
            SyntheticCell("Invented Ledger", "B2", "2"),
            SyntheticCell("Invented Summary", "B2", "123", "=SUM(B3:B5)"),
        ))


class WorkerTests(unittest.TestCase):
    def test_scope_and_operation_allowlist(self):
        for client, env in (("other", "staging"), ("jespersen-painting", "production")):
            with self.assertRaises(ValueError):
                RuntimeScope(client, env, ROOT)
        provider = Provider((ref(0),))
        boundary = ReadOnlyBoundary(provider, ROOT)
        for operation in ("delete", "write", "move", "update", "create", "list_and_write"):
            with self.assertRaisesRegex(ValueError, "not permitted"):
                boundary.execute(operation, ref=ref(0))
        self.assertEqual(provider.writes, [])

    def test_resume_idempotency_and_private_public_split(self):
        provider = Provider(tuple(ref(i) for i in range(5)))
        parser = Parser()
        store = MemoryPrivateCheckpoint()
        first = intake(SCOPE, provider, parser, store, limit=2)
        self.assertEqual((first.total, first.handled, first.pending, parser.calls), (5, 2, 3, 2))
        second = intake(SCOPE, provider, parser, store, limit=1)
        self.assertEqual((second.handled, second.pending, parser.calls), (3, 2, 3))
        final = intake(SCOPE, provider, parser, store)
        with patch.object(parser, "parse", side_effect=AssertionError("reparsed")):
            self.assertEqual(intake(SCOPE, provider, parser, store), final)
        self.assertEqual((final.completed, final.handled, len(provider.reads)), (5, 5, 5))
        record = store.get(ref(0).inventory.source_id)
        self.assertEqual(record.version, WORKER_VERSION)
        self.assertEqual(record.steps, ("listed", "boundary_checked", "read_verified",
                                        "classified_adapted", "recomputed", "committed"))
        self.assertEqual(record.key.sha256, ref(0).inventory.sha256)
        self.assertIsNotNone(record.fingerprint)
        self.assertEqual(record.result.document.job.facts[2].formula_text, "=SUM(B3:B5)")
        self.assertTrue(record.recomputed.metrics)
        self.assertTrue(all(m.state != "computed" for m in record.recomputed.metrics))
        for private in (record.file_id, record.key.source_id, record.key.sha256, "SUM", "123"):
            self.assertNotIn(private, repr(final))
        self.assertEqual(provider.writes, [])

    def test_out_of_root_and_changed_read_response_rejected(self):
        bad = ref(0, parent="synthetic_other_root")
        good = ref(1)
        provider = Provider((bad, good))
        store = MemoryPrivateCheckpoint()
        progress = intake(SCOPE, provider, Parser(), store)
        self.assertEqual((progress.failed, progress.handled, provider.reads),
                         (1, 1, [good.file_id]))
        self.assertEqual(store.get(bad.inventory.source_id).reason, "boundary_rejected")
        # A read that reports an outside parent, even after an in-root listing,
        # cannot be passed to a parser.
        provider = Provider((good,))
        provider.read_file = lambda file_id: ReadResult(file_id, "synthetic_other_root", b"private")
        parser = Parser()
        progress = intake(SCOPE, provider, parser, MemoryPrivateCheckpoint())
        self.assertEqual((progress.failed, parser.calls), (1, 0))

    def test_digest_and_immutable_source_guard(self):
        provider = Provider((ref(0), ref(1)))
        provider.read_file = lambda file_id: ReadResult(file_id, ROOT, b"different")
        store = MemoryPrivateCheckpoint()
        self.assertEqual(intake(SCOPE, provider, Parser(), store).failed, 2)
        self.assertEqual(store.get(ref(0).inventory.source_id).reason, "digest_mismatch")
        provider.refs = (ref(0, content=b"changed original"),)
        with self.assertRaisesRegex(ValueError, "immutable source changed"):
            intake(SCOPE, provider, Parser(), store)

    def test_unknown_shape_and_item_failure_isolation(self):
        provider = Provider((ref(0), ref(1), ref(2)))
        class Mixed(Parser):
            def parse(self, content, source_id, digest):
                if source_id == ref(0).inventory.source_id:
                    return SyntheticItem(source_id, digest, UNKNOWN, ())
                if source_id == ref(1).inventory.source_id:
                    raise ValueError("synthetic-private-source-marker")
                return super().parse(content, source_id, digest)
        store = MemoryPrivateCheckpoint()
        progress = intake(SCOPE, provider, Mixed(), store)
        self.assertEqual((progress.needs_review, progress.failed, progress.handled), (1, 1, 1))
        unknown = store.get(ref(0).inventory.source_id)
        self.assertIsNone(unknown.recomputed)
        self.assertEqual(unknown.result.workbook.shape_state, "unknown")
        self.assertIsNone(unknown.result.workbook.adapter_version)
        self.assertEqual(store.get(ref(1).inventory.source_id).reason, "parser_error")
        self.assertNotIn("synthetic-private-source-marker", repr(progress) + repr(store))
        self.assertEqual(intake(SCOPE, provider, Mixed(), store), progress)

    def test_manifest_conflict_fails_before_read(self):
        provider = Provider((ref(0), ref(0)))
        store = MemoryPrivateCheckpoint()
        with self.assertRaises(ValueError):
            intake(SCOPE, provider, Parser(), store)
        self.assertFalse(store.records)
        self.assertEqual(provider.reads, [])


if __name__ == "__main__":
    unittest.main()
