"""Exercise the independent synthetic Hedy persistence protocol tests."""
import pathlib
import shutil
import subprocess


def test_hedy_financial_store_protocol():
    node = shutil.which("node")
    assert node, "Node is required for Hedy financial store protocol verification"
    root = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run([node, "--test", "tests/hedy_financial_store.cjs"], cwd=root, check=True)
