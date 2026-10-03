"""Synthetic-only Node financial runner checks through trusted pytest workflow."""
import shutil
import subprocess
import unittest
from pathlib import Path


class FinancialRunnerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; JS tests require Node')
    def test_synthetic_financial_runner(self):
        subprocess.run(['node', '--test', str(Path(__file__).with_name('financial_runner.cjs'))],
                       check=True, timeout=30)
