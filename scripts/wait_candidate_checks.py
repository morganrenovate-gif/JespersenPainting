"""Explicitly dispatch trusted checks and require success for an immutable PR head."""
import json
import os
import time
from datetime import datetime, timezone
from recover_agent_task import gh


def candidate(pr, expected):
    if pr.get('state') != 'open' or pr['head']['sha'] != expected or pr['head']['repo']['full_name'] != os.environ['GITHUB_REPOSITORY']:
        raise ValueError('PR must be open with the expected same-repository immutable head')


def main():
    repo, number, sha = os.environ['GITHUB_REPOSITORY'], os.environ['PR_NUMBER'], os.environ['CANDIDATE_SHA']
    candidate(json.loads(gh('api', f'/repos/{repo}/pulls/{number}')), sha)
    since = datetime.now(timezone.utc)
    title = f'Candidate checks PR #{number} {sha}'
    gh('workflow', 'run', 'autonomy-control-checks.yml', '--repo', repo, '--ref', 'main',
       '-f', f'pr_number={number}', '-f', f'head_sha={sha}')
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        runs = json.loads(gh('api', f'/repos/{repo}/actions/workflows/autonomy-control-checks.yml/runs?event=workflow_dispatch&per_page=100'))['workflow_runs']
        matches = [r for r in runs if r['display_title'] == title and
                   datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')) >= since.replace(microsecond=0)]
        if matches:
            run = max(matches, key=lambda r: r['id'])
            if run['status'] == 'completed':
                if run['conclusion'] != 'success':
                    raise RuntimeError(f'Candidate checks rejected: run {run["id"]} {run["conclusion"]}')
                candidate(json.loads(gh('api', f'/repos/{repo}/pulls/{number}')), sha)
                print(f'Exact candidate checks passed: {run["id"]}')
                return
        time.sleep(10)
    raise RuntimeError('Exact candidate checks did not complete before deadline; merge forbidden')


if __name__ == '__main__':
    main()
