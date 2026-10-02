"""Synthetic control-plane tests for the Mission Controller runtime task ledger."""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "scripts" / "build_task_ledger.py"
VALIDATOR = ROOT / "scripts" / "validate_controller_plan.py"


class TaskLedgerTests(unittest.TestCase):
    def run_ledger(self, backlog, graph, issues, prs):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "BACKLOG.md").write_text(backlog, encoding="utf-8")
            (root / "TASK_GRAPH.json").write_text(json.dumps(graph), encoding="utf-8")
            (root / "issues.json").write_text(json.dumps(issues), encoding="utf-8")
            (root / "prs.json").write_text(json.dumps(prs), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(LEDGER),
                    str(root / "BACKLOG.md"),
                    str(root / "TASK_GRAPH.json"),
                    str(root / "issues.json"),
                    str(root / "prs.json"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_completed_task_is_not_reselected_and_unlocks_dependency(self):
        backlog = """# Backlog

### DATA-001 — First
Priority: P0
Status: TODO

### DATA-002 — Second
Priority: P0
Status: TODO
"""
        graph = {
            "schemaVersion": 1,
            "repositoryReadyStates": ["PASS", "QA"],
            "tasks": {
                "DATA-001": {"repositoryEligible": True, "dependencies": []},
                "DATA-002": {"repositoryEligible": True, "dependencies": ["DATA-001"]},
            },
        }
        issues = [
            {
                "number": 7,
                "title": "[AGENT] DATA-001",
                "state": "CLOSED",
                "stateReason": "COMPLETED",
                "createdAt": "2026-01-01T00:00:00Z",
                "closedAt": "2026-01-01T00:02:00Z",
                "url": "https://example.test/issues/7",
            }
        ]
        prs = [
            {
                "number": 8,
                "title": "Agent: issue #7",
                "state": "MERGED",
                "mergedAt": "2026-01-01T00:01:00Z",
                "url": "https://example.test/pulls/8",
            }
        ]
        ledger = self.run_ledger(backlog, graph, issues, prs)
        self.assertEqual(ledger["tasks"]["DATA-001"]["state"], "QA")
        self.assertFalse(ledger["tasks"]["DATA-001"]["eligible"])
        self.assertTrue(ledger["tasks"]["DATA-002"]["eligible"])
        self.assertEqual(ledger["eligibleTaskIds"], ["DATA-002"])

    def test_terminal_failed_attempt_blocks_same_task_id(self):
        backlog = """# Backlog

### QA-001 — Gate
Priority: P0
Status: TODO
"""
        graph = {
            "schemaVersion": 1,
            "repositoryReadyStates": ["PASS", "QA"],
            "tasks": {
                "QA-001": {"repositoryEligible": True, "dependencies": []},
            },
        }
        issues = [
            {
                "number": 23,
                "title": "[AGENT] QA-001",
                "state": "CLOSED",
                "stateReason": "NOT_PLANNED",
                "createdAt": "2026-01-01T00:00:00Z",
                "closedAt": "2026-01-01T00:01:00Z",
                "url": "https://example.test/issues/23",
            }
        ]
        ledger = self.run_ledger(backlog, graph, issues, [])
        self.assertEqual(ledger["tasks"]["QA-001"]["state"], "BLOCKED")
        self.assertFalse(ledger["tasks"]["QA-001"]["eligible"])

    def test_validator_rejects_noneligible_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            backlog = """# Backlog

### DATA-001 — First
Priority: P0
Status: QA
"""
            ledger = {
                "tasks": {
                    "DATA-001": {
                        "state": "QA",
                        "eligible": False,
                        "protectedControlPlane": False,
                        "unsatisfiedDependencies": [],
                    }
                },
                "eligibleTaskIds": [],
            }
            plan = {
                "action": "dispatch",
                "task_id": "DATA-001",
                "permission_tier": "T1",
                "environment": "dev",
                "objective": "Synthetic objective",
                "requested_work": "Synthetic work",
                "acceptance": "Synthetic acceptance",
                "constraints": "Synthetic constraints",
                "rollback": "Revert the synthetic change.",
            }
            (root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (root / "BACKLOG.md").write_text(backlog, encoding="utf-8")
            (root / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    str(root / "plan.json"),
                    str(root / "BACKLOG.md"),
                    str(root / "ledger.json"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("task is not TODO", result.stderr)


if __name__ == "__main__":
    unittest.main()
