#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, re, sys

def fail(msgs):
    print("MISSION CONTROLLER PLAN: FAIL", file=sys.stderr)
    for m in msgs: print(f"- {m}", file=sys.stderr)
    raise SystemExit(1)

if len(sys.argv)!=3:
    raise SystemExit("usage: validate_controller_plan.py <plan.json> <backlog.md>")
p=json.loads(pathlib.Path(sys.argv[1]).read_text())
backlog=pathlib.Path(sys.argv[2]).read_text()
errs=[]
if p.get("action") not in {"dispatch","stop"}: errs.append("invalid action")
if p.get("action")=="dispatch":
    tid=str(p.get("task_id","")).strip()
    if not re.fullmatch(r"[A-Z]+-\d{3}",tid): errs.append("invalid task_id")
    if f"### {tid} " not in backlog: errs.append("task_id not present in BACKLOG.md")
    if p.get("permission_tier") not in {"T0","T1"}: errs.append("executor lane accepts T0/T1 only")
    if p.get("environment") not in {"dev","staging"}: errs.append("invalid environment")
    for k in ("objective","requested_work","acceptance","constraints","rollback"):
        v=str(p.get(k,"")).strip()
        if not v: errs.append(f"{k} required")
        if len(v)>5000: errs.append(f"{k} too long")
    banned=[
      r"\bsk-[A-Za-z0-9_-]{20,}\b", r"\bpplx-[A-Za-z0-9_-]{20,}\b", r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b",
      r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ]
    blob=json.dumps(p)
    if any(re.search(x,blob) for x in banned): errs.append("secret-like material detected")
if errs: fail(errs)
print("MISSION CONTROLLER PLAN: PASS")
