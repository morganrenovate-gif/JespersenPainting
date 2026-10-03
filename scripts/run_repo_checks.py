#!/usr/bin/env python3
"""Trusted post-agent repository checks.

Runs only after the Perplexity-backed agent step has exited, so provider credentials are
not present in this process. This script is protected from autonomous edits.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path.cwd()


def run(cmd: list[str], *, optional: bool = False) -> bool:
    print("+", " ".join(cmd), flush=True)
    try:
        cp = subprocess.run(cmd, cwd=ROOT, text=True, timeout=300)
    except FileNotFoundError:
        if optional:
            print(f"SKIP: executable not available: {cmd[0]}")
            return True
        raise
    if cp.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ok = run(["git", "diff", "--check"])

    package = ROOT / "package.json"
    if package.exists() and shutil.which("npm"):
        data = json.loads(package.read_text(encoding="utf-8"))
        scripts = data.get("scripts") or {}
        for name in ("verify", "test", "lint", "typecheck", "build"):
            if name in scripts:
                ok = run(["npm", "run", name]) and ok

    if (ROOT / "tests").exists():
        if importlib.util.find_spec("pytest") is None:
            print("FAIL: required pytest is not installed", file=sys.stderr)
            ok = False
        elif shutil.which("node") is None:
            print("FAIL: required Node runtime is not installed", file=sys.stderr)
            ok = False
        else:
            ok = run([sys.executable, "-m", "pytest", "-q"]) and ok

    print("TRUSTED REPOSITORY CHECKS:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

