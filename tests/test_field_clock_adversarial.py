"""Synthetic-only TIME-005 adversarial field-clock register checks; no provider or real workers."""
import shutil
import subprocess
import unittest
from pathlib import Path


class FieldClockAdversarialTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; JS interaction checks require Node')
    def test_synthetic_time_adversaries(self):
        subprocess.run(['node', str(Path(__file__).with_name('field_clock_adversarial.cjs'))],
                       check=True, timeout=15)
