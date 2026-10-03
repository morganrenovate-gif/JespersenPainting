"""Synthetic-only JS runner regression hook for trusted pytest repository checks."""
import shutil
import subprocess
from pathlib import Path


def test_financial_runner_node():
    node = shutil.which("node")
    assert node, "Node required for financial runner checks"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, "--test", "tests/financial_runner.cjs"],
                            cwd=root, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
