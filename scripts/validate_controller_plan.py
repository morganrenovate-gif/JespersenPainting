#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import re
import sys


def fail(msgs):
    print("MISSION CONTROLLER PLAN: FAIL", file=sys.stderr)
    for message in msgs:
        print(f"- {message}", file=sys.stderr)
    raise SystemExit(1)


if len(sys.argv) != 4:
    raise SystemExit(
        "usage: validate_controller_plan.py <plan.json> <backlog.md> <task-ledger.json>"
    )

plan = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
backlog = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
ledger = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))
errs = []

if plan.get("action") not in {"dispatch", "stop"}:
    errs.append("invalid action")

if plan.get("action") == "dispatch":
    task_id = str(plan.get("task_id", "")).strip()
    if not re.fullmatch(r"[A-Z]+-\d{3}", task_id):
        errs.append("invalid task_id")
    if f"### {task_id} " not in backlog:
        errs.append("task_id not present in BACKLOG.md")
    if plan.get("permission_tier") not in {"T0", "T1"}:
        errs.append("executor lane accepts T0/T1 only")
    if plan.get("environment") not in {"dev", "staging"}:
        errs.append("invalid environment")

    for key in ("objective", "requested_work", "acceptance", "constraints", "rollback"):
        value = str(plan.get(key, "")).strip()
        if not value:
            errs.append(f"{key} required")
        if len(value) > 5000:
            errs.append(f"{key} too long")

    task = (ledger.get("tasks") or {}).get(task_id)
    if not task:
        errs.append("task_id missing from runtime task ledger")
    else:
        if task.get("state") != "TODO":
            errs.append(f"task is not TODO in runtime ledger: {task.get('state')}")
        if task.get("eligible") is not True:
            errs.append("task is not eligible in runtime ledger")
        if task.get("protectedControlPlane") is True:
            errs.append("protected control-plane task cannot enter bounded executor lane")
        unsatisfied = task.get("unsatisfiedDependencies") or []
        if unsatisfied:
            errs.append("unsatisfied dependencies: " + ", ".join(map(str, unsatisfied)))

        if task.get("userFacing") is True:
            blob = "\n".join(
                str(plan.get(key, ""))
                for key in ("requested_work", "acceptance", "constraints")
            )
            if "UI_STANDARD.md" not in blob and "UI-STD-1.0" not in blob:
                errs.append("user-facing task must explicitly inherit UI_STANDARD.md / UI-STD-1.0")
            required_design_fields = (
                "Product",
                "Surface",
                "Dominant Visual Archetype",
                "Secondary Influence",
                "Palette",
                "Density",
                "Motion Intensity",
                "Primary Users",
                "Critical Information",
            )
            missing_fields = [field for field in required_design_fields if field not in blob]
            if missing_fields:
                errs.append(
                    "user-facing task missing design assignment fields: "
                    + ", ".join(missing_fields)
                )

    if task_id not in set(ledger.get("eligibleTaskIds") or []):
        errs.append("task_id not present in eligibleTaskIds")

    banned = [
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        r"\bpplx-[A-Za-z0-9_-]{20,}\b",
        r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b",
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    ]
    blob = json.dumps(plan)
    if any(re.search(pattern, blob) for pattern in banned):
        errs.append("secret-like material detected")

if errs:
    fail(errs)

print("MISSION CONTROLLER PLAN: PASS")
