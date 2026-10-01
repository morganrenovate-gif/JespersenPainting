#!/usr/bin/env python3
"""Validate a public-safe Jespersen autonomous coding task envelope."""

from __future__ import annotations

import json
import pathlib
import re
import sys

MAX_BODY = 12_000
REQUIRED_LABELS = [
    "Task ID:",
    "Client context:",
    "Permission tier:",
    "Environment:",
    "Public-safe task package:",
    "Objective:",
    "Requested work:",
    "Acceptance:",
    "Constraints:",
    "Rollback:",
]

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bpplx-[A-Za-z0-9_-]{20,}\b", re.I),
    re.compile(r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
]


def value_for(body: str, label: str) -> str:
    lines = body.splitlines()
    target = label.lower()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.lower().startswith(target):
            continue
        same_line = stripped.split(":", 1)[1].strip()
        if same_line:
            return same_line

        block = []
        for later in lines[idx + 1 :]:
            candidate = later.strip()
            if any(candidate.lower().startswith(required.lower()) for required in REQUIRED_LABELS):
                break
            if candidate:
                block.append(candidate)
        return "\n".join(block).strip()
    return ""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_agent_task.py <task.json>", file=sys.stderr)
        return 2

    task = json.loads(pathlib.Path(sys.argv[1]).read_text())
    title = str(task.get("title") or "")
    body = str(task.get("body") or "")

    failures: list[str] = []
    if not title.startswith("[AGENT]"):
        failures.append("title must start with [AGENT]")
    if not body or len(body) > MAX_BODY:
        failures.append(f"task body must be 1..{MAX_BODY} characters")

    for label in REQUIRED_LABELS:
        if not value_for(body, label):
            failures.append(f"missing required field: {label}")

    if value_for(body, "Client context:") != "jespersen-painting":
        failures.append("Client context must equal jespersen-painting")

    if value_for(body, "Permission tier:") not in {"T0", "T1"}:
        failures.append("repository executor lane accepts only T0 or T1")

    if value_for(body, "Environment:") not in {"dev", "staging"}:
        failures.append("Environment must be dev or staging")

    if value_for(body, "Public-safe task package:").lower() != "yes":
        failures.append("Public-safe task package must be yes")

    for pattern in SECRET_PATTERNS:
        if pattern.search(body):
            failures.append("task body contains secret/private-data-like material")
            break

    if failures:
        print("AGENT TASK ENVELOPE: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("AGENT TASK ENVELOPE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
