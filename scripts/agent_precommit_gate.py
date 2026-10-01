#!/usr/bin/env python3
"""Fail-closed public-repository gate for autonomous Jespersen commits."""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

PROTECTED = {
    ".github/workflows/jespersen-codex-executor.yml",
    ".github/workflows/jespersen-mission-controller.yml",
    "scripts/agent_precommit_gate.py",
    "scripts/validate_codex_task.py",
    "scripts/validate_controller_plan.py",
    "AGENTS.md",
    "DATA_BOUNDARY.md",
    ".codex/config.toml",
}

DENIED_SUFFIXES = {
    ".xlsx", ".xls", ".xlsm", ".xlsb", ".ods", ".csv", ".tsv",
    ".pdf", ".eml", ".msg", ".mbox", ".zip", ".7z", ".rar",
    ".sqlite", ".sqlite3", ".db", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".heic",
}

MAX_FILE_BYTES = 524_288

SECRET_PATTERNS = [
    ("OpenAI/API-style secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub PAT", re.compile(r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Bearer credential", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}\b", re.I)),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("SSN-like value", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
]

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.I)
ALLOWED_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "example.test",
    "users.noreply.github.com",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def changed_paths(args: argparse.Namespace) -> list[str]:
    if args.cached:
        out = run("git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT")
        return [x for x in out.splitlines() if x]

    if args.base and args.head:
        out = run("git", "diff", "--name-only", "--diff-filter=ACMRT", f"{args.base}...{args.head}")
        return [x for x in out.splitlines() if x]

    tracked = run("git", "diff", "--name-only", "--diff-filter=ACMRT")
    untracked = run("git", "ls-files", "--others", "--exclude-standard")
    return sorted(set([x for x in (tracked + "\n" + untracked).splitlines() if x]))


def read_blob(path: str, args: argparse.Namespace) -> bytes:
    if args.cached:
        try:
            return subprocess.check_output(["git", "show", f":{path}"])
        except subprocess.CalledProcessError:
            return b""
    if args.base and args.head:
        try:
            return subprocess.check_output(["git", "show", f"{args.head}:{path}"])
        except subprocess.CalledProcessError:
            return b""
    p = pathlib.Path(path)
    return p.read_bytes() if p.exists() and p.is_file() else b""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--head")
    args = parser.parse_args()

    if bool(args.base) != bool(args.head):
        parser.error("--base and --head must be supplied together")

    failures: list[str] = []
    paths = changed_paths(args)

    for path in paths:
        if path in PROTECTED:
            failures.append(f"protected control-plane file changed: {path}")
            continue

        suffix = pathlib.Path(path).suffix.lower()
        if suffix in DENIED_SUFFIXES:
            failures.append(f"binary/private-data-prone file type blocked: {path}")
            continue

        data = read_blob(path, args)
        if len(data) > MAX_FILE_BYTES:
            failures.append(f"file exceeds autonomous lane size limit ({MAX_FILE_BYTES} bytes): {path}")
            continue

        if b"\x00" in data:
            failures.append(f"binary content blocked: {path}")
            continue

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(f"non-UTF-8 content blocked: {path}")
            continue

        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"{label} detected in {path}")

        for match in EMAIL_RE.finditer(text):
            domain = match.group(1).lower()
            if domain not in ALLOWED_EMAIL_DOMAINS:
                failures.append(f"non-synthetic email address detected in {path}: domain={domain}")

        lowered = path.lower()
        if ("fixture" in lowered or "testdata" in lowered or "test-data" in lowered) and text.strip():
            if "synthetic" not in text.lower():
                failures.append(f"fixture/test-data file is not explicitly labeled synthetic: {path}")

    if failures:
        print("PUBLIC REPOSITORY GATE: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"PUBLIC REPOSITORY GATE: PASS ({len(paths)} changed paths checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
