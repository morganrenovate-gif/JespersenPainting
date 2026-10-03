#!/usr/bin/env python3
"""Build the Mission Controller runtime task ledger from durable project evidence."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import defaultdict

TASK_HEADING_RE = re.compile(r"^###\s+([A-Z]+(?:-[A-Z]+)*-\d{3})\b", re.M)
STATUS_RE = re.compile(r"^Status:\s*([A-Z_]+)\s*$", re.M)
ISSUE_TITLE_RE = re.compile(r"^\[AGENT\]\s+([A-Z]+(?:-[A-Z]+)*-\d{3})(?:\s+—[^\n]+)?\s*$")
PR_TITLE_RE = re.compile(r"^Agent:\s+issue\s+#(\d+)\s*$", re.I)

READY_STATES_DEFAULT = {"PASS", "QA"}


def fail(message: str) -> None:
    raise SystemExit(message)


def backlog_statuses(text: str) -> dict[str, str]:
    matches = list(TASK_HEADING_RE.finditer(text))
    out: dict[str, str] = {}
    for index, match in enumerate(matches):
        task_id = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end():end]
        status_match = STATUS_RE.search(section)
        out[task_id] = status_match.group(1) if status_match else "TODO"
    return out


def main() -> int:
    if len(sys.argv) != 5:
        fail("usage: build_task_ledger.py <backlog.md> <task_graph.json> <issues.json> <prs.json>")

    backlog_path, graph_path, issues_path, prs_path = map(pathlib.Path, sys.argv[1:])
    statuses = backlog_statuses(backlog_path.read_text(encoding="utf-8"))
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    issues = json.loads(issues_path.read_text(encoding="utf-8"))
    prs = json.loads(prs_path.read_text(encoding="utf-8"))

    graph_tasks = graph.get("tasks") or {}
    missing = sorted(set(statuses) - set(graph_tasks))
    extra = sorted(set(graph_tasks) - set(statuses))
    if missing or extra:
        fail(f"TASK_GRAPH mismatch: missing={missing} extra={extra}")

    merged_issue_numbers: set[int] = set()
    pr_evidence: dict[int, list[dict[str, object]]] = defaultdict(list)
    for pr in prs:
        match = PR_TITLE_RE.match(str(pr.get("title") or "").strip())
        if not match:
            continue
        issue_number = int(match.group(1))
        if str(pr.get("state") or "").upper() == "MERGED" or pr.get("mergedAt"):
            merged_issue_numbers.add(issue_number)
            pr_evidence[issue_number].append({
                "pr": pr.get("number"),
                "url": pr.get("url"),
                "mergedAt": pr.get("mergedAt"),
            })

    attempts: dict[str, list[dict[str, object]]] = defaultdict(list)
    for issue in issues:
        match = ISSUE_TITLE_RE.match(str(issue.get("title") or "").strip())
        if not match:
            continue
        task_id = match.group(1)
        if task_id not in statuses:
            continue
        issue_number = int(issue["number"])
        state = str(issue.get("state") or "").upper()
        reason = str(issue.get("stateReason") or "").upper() or None
        merged = issue_number in merged_issue_numbers
        attempts[task_id].append({
            "issue": issue_number,
            "url": issue.get("url"),
            "state": state,
            "stateReason": reason,
            "createdAt": issue.get("createdAt"),
            "closedAt": issue.get("closedAt"),
            "mergedPullRequest": merged,
            "pullRequests": pr_evidence.get(issue_number, []),
        })

    ledger: dict[str, dict[str, object]] = {}
    for task_id, backlog_state in statuses.items():
        task_attempts = sorted(
            attempts.get(task_id, []),
            key=lambda item: str(item.get("createdAt") or ""),
        )
        completed = [
            item for item in task_attempts
            if item["state"] == "CLOSED"
            and item["stateReason"] == "COMPLETED"
            and item["mergedPullRequest"] is True
        ]
        open_attempts = [item for item in task_attempts if item["state"] == "OPEN"]
        failed = [
            item for item in task_attempts
            if item["state"] == "CLOSED"
            and item["stateReason"] != "COMPLETED"
        ]

        if backlog_state in {"PASS", "QA", "BLOCKED_EXTERNAL"}:
            state = backlog_state
            state_source = "BACKLOG.md"
        elif completed:
            state = "QA"
            state_source = "merged_agent_pr"
        elif open_attempts:
            state = "IN_PROGRESS"
            state_source = "open_agent_issue"
        elif failed:
            state = "BLOCKED"
            state_source = "terminal_failed_attempt"
        else:
            state = backlog_state
            state_source = "BACKLOG.md"

        ledger[task_id] = {
            "taskId": task_id,
            "state": state,
            "stateSource": state_source,
            "repositoryEligibleConfigured": bool(graph_tasks[task_id].get("repositoryEligible")),
            "dependencies": list(graph_tasks[task_id].get("dependencies") or []),
            "userFacing": bool(graph_tasks[task_id].get("userFacing")),
            "protectedControlPlane": bool(graph_tasks[task_id].get("protectedControlPlane")),
            "routingReason": graph_tasks[task_id].get("reason"),
            "attemptCount": len(task_attempts),
            "attempts": task_attempts,
        }

    ready_states = set(graph.get("repositoryReadyStates") or READY_STATES_DEFAULT)
    for task_id, entry in ledger.items():
        dependencies = entry["dependencies"]
        unsatisfied = [
            dep for dep in dependencies
            if dep not in ledger or ledger[dep]["state"] not in ready_states
        ]
        entry["dependenciesSatisfied"] = not unsatisfied
        entry["unsatisfiedDependencies"] = unsatisfied
        entry["eligible"] = bool(
            entry["state"] == "TODO"
            and entry["repositoryEligibleConfigured"]
            and not entry["protectedControlPlane"]
            and not unsatisfied
        )

    output = {
        "schemaVersion": 1,
        "stateAuthority": {
            "routing": "Derived from BACKLOG.md plus durable GitHub [AGENT] issues and merged Agent PRs.",
            "completionRule": "A completed [AGENT] issue only counts as repository QA evidence when a merged Agent PR references that issue.",
            "failureRule": "A terminal non-completed [AGENT] attempt blocks automatic reselection of the same task ID.",
            "dependencyReadyStates": sorted(ready_states),
        },
        "tasks": ledger,
        "eligibleTaskIds": sorted(task_id for task_id, entry in ledger.items() if entry["eligible"]),
    }
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

