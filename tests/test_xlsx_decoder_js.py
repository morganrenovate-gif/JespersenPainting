"""Synthetic-only XLSX decoder executable test bridge for trusted pytest checks."""
import pathlib
import subprocess


def test_xlsx_decoder_node():
    root = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run(["node", "--test", "tests/xlsx_decoder.cjs"], cwd=root, check=True, timeout=120)
