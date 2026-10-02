"""Synthetic-only QA-001 regression tests for the existing public-repository gate."""

import pathlib
import subprocess
import sys
import tempfile
import unittest


GATE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "agent_precommit_gate.py"


class PublicRepositoryGateTests(unittest.TestCase):
    def check_gate(self, filename, content):
        # Each case has its own disposable Git repository; no commits or external writes.
        with tempfile.TemporaryDirectory() as directory:
            repo = pathlib.Path(directory)
            subprocess.run(
                ["git", "-c", "init.templateDir=", "init", "-q"],
                cwd=repo, check=True, capture_output=True, text=True,
            )
            (repo / filename).write_text(content, encoding="utf-8")
            # Force-add so even globally ignored document suffixes reach the gate.
            subprocess.run(
                ["git", "add", "-f", "--", filename],
                cwd=repo, check=True, capture_output=True, text=True,
            )
            return subprocess.run(
                [sys.executable, str(GATE), "--cached"],
                cwd=repo, capture_output=True, text=True, check=False,
            )

    def test_safe_synthetic_content_passes(self):
        result = self.check_gate(
            "sample.txt", "Synthetic job: Amber Hangar; contact: team@example.test\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PUBLIC REPOSITORY GATE: PASS (1 changed paths checked)", result.stdout)

    def test_secret_like_and_pii_markers_are_blocked(self):
        # Assemble invented markers at runtime so scanner-triggering values are not in source.
        cases = (
            ("OpenAI/API-style secret", "sk" + "-" + "A" * 24),
            ("GitHub PAT", "github" + "_pat_" + "B" * 24),
            ("SSN-like value", "000" + "-00-" + "0000"),
        )
        for label, marker in cases:
            with self.subTest(label=label):
                result = self.check_gate("sample.txt", "Synthetic test marker: " + marker + "\n")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("PUBLIC REPOSITORY GATE: FAIL", result.stderr)
                self.assertIn(label + " detected in sample.txt", result.stderr)

    def test_non_synthetic_email_domain_is_blocked(self):
        address = "invented" + "@" + "not-example.invalid"
        result = self.check_gate("sample.txt", "Synthetic test contact: " + address + "\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("non-synthetic email address detected in sample.txt", result.stderr)
        self.assertIn("domain=not-example.invalid", result.stderr)

    def test_labeled_high_confidence_pii_is_blocked_without_echoing_value(self):
        cases = (
            ("labeled date of birth", "DOB" + ": " + "01/02/" + "1990"),
            ("labeled bank routing number", "routing number" + ": " + "123456789"),
            ("labeled bank account number", "account number" + ": " + "123456789012"),
        )
        for label, marker in cases:
            with self.subTest(label=label):
                result = self.check_gate("sample.txt", "Synthetic test field: " + marker + "\n")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(label + " detected in sample.txt", result.stderr)
                self.assertNotIn(marker, result.stderr)

    def test_private_data_prone_file_types_are_blocked(self):
        for suffix in (".xlsx", ".eml", ".csv", ".pdf"):
            with self.subTest(suffix=suffix):
                name = "sample" + suffix
                result = self.check_gate(name, "Synthetic placeholder only.\n")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("PUBLIC REPOSITORY GATE: FAIL", result.stderr)
                self.assertIn("binary/private-data-prone file type blocked: " + name, result.stderr)


if __name__ == "__main__":
    unittest.main()
