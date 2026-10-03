"""Trusted recovery of abandoned public-safe executor issues; no private access."""
import json
import os
import re
from datetime import datetime, timezone, timedelta

from recover_agent_task import gh, main as recover

LIVE = {'queued', 'in_progress', 'waiting', 'pending', 'requested'}
MARKER = re.compile(r'^AUTONOMY_DISPATCH attempt=(\d+) at=(\S+)$', re.M)


def dispatch(repo, issue, runs, comments, now=None):
    """Reserve before dispatch; an interrupted reservation can expire and retry."""
    now = now or datetime.now(timezone.utc)
    if issue.get('state', '').upper() != 'OPEN':
        return False
    # Serialization plus this global check prevents watchdog/implementation races.
    if any(r['status'] in LIVE for r in runs):
        return False
    markers = []
    for comment in comments:
        if comment.get('user', {}).get('login') == 'github-actions[bot]':
            markers.extend(MARKER.findall(comment.get('body', '')))
    attempt = max((int(x[0]) for x in markers), default=0)
    latest = max((datetime.fromisoformat(x[1].replace('Z', '+00:00')) for x in markers), default=None)
    if latest and now - latest < timedelta(minutes=15):
        return False
    if attempt >= 3:
        gh('issue', 'close', str(issue['number']), '--repo', repo, '--reason', 'not planned',
           '--comment', 'Autonomous dispatch budget exhausted. This task is blocked; unrelated eligible work continues. No acceptance gate was bypassed.')
        return False
    # Validate through the existing trusted validator before any external mutation.
    import tempfile
    from pathlib import Path
    import subprocess
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'task.json'
        path.write_text(json.dumps(issue))
        subprocess.run(['python', 'scripts/validate_agent_task.py', str(path)], check=True)
    gh('issue', 'comment', str(issue['number']), '--repo', repo, '--body',
       f'AUTONOMY_DISPATCH attempt={attempt + 1} at={now.isoformat()}')
    gh('workflow', 'run', 'jespersen-perplexity-executor.yml', '--repo', repo,
       '--ref', 'main', '-f', f"issue_number={issue['number']}")
    return True


def pages(repo, endpoint):
    result = json.loads(gh('api', '--paginate', '--slurp', f'/repos/{repo}/{endpoint}'))
    return [item for page in result for item in (page.get('workflow_runs', []) if isinstance(page, dict) else page)]


def valid_task(repo, issue):
    """Ignore malformed/untrusted queue entries without widening authority."""
    import tempfile
    import subprocess
    from pathlib import Path
    author = issue.get('user', {}).get('login', '')
    if not author:
        return False
    if author != 'github-actions[bot]':
        permission = json.loads(gh('api', f'/repos/{repo}/collaborators/{author}/permission')).get('permission')
        if permission not in {'write', 'maintain', 'admin'}:
            return False
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'task.json'
        path.write_text(json.dumps(issue))
        return subprocess.run(['python', 'scripts/validate_agent_task.py', str(path)],
                              capture_output=True).returncode == 0


def active_count(repo):
    return sum(1 for issue in pages(repo, 'issues?state=open&per_page=100')
               if 'pull_request' not in issue and issue.get('title', '').startswith('[AGENT]')
               and valid_task(repo, issue))


def ledger_issues(repo):
    return [{'number': i['number'], 'title': i['title'], 'state': i['state'].upper(),
             'stateReason': str(i.get('state_reason') or '').upper(),
             'createdAt': i.get('created_at'), 'closedAt': i.get('closed_at'), 'url': i.get('html_url')}
            for i in pages(repo, 'issues?state=all&per_page=100')
            if 'pull_request' not in i and i.get('title', '').startswith('[AGENT]') and valid_task(repo, i)]


def ledger_prs(repo):
    return [{'number': p['number'], 'title': p['title'], 'state': 'MERGED',
             'mergedAt': p['merged_at'], 'url': p.get('html_url')}
            for p in pages(repo, 'pulls?state=closed&per_page=100') if p.get('merged_at')]


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    runs = pages(repo, 'actions/workflows/jespersen-perplexity-executor.yml/runs?per_page=100')
    active = [r for r in runs if r['status'] in LIVE]
    now = datetime.now(timezone.utc)
    for run in active:
        stamp = run.get('run_started_at') if run['status'] == 'in_progress' else run.get('created_at')
        limit = timedelta(minutes=45 if run['status'] == 'in_progress' else 60)
        if stamp and now - datetime.fromisoformat(stamp.replace('Z', '+00:00')) > limit:
            # Executor's declared hard timeout is 30 minutes. Cancel only after
            # that plus grace; next controller tick recovers the terminal run.
            gh('api', '--method', 'POST', f'/repos/{repo}/actions/runs/{run["id"]}/cancel')
            print(f'Watchdog cancelled overdue executor {run["id"]}; awaiting terminal state.')
            return
    if active:
        print('Healthy executor queued/running; watchdog does not interrupt it.')
        return
    issues = pages(repo, 'issues?state=open&per_page=100')
    for issue in issues:
        if 'pull_request' in issue or not issue.get('title', '').startswith('[AGENT]'):
            continue
        if not valid_task(repo, issue):
            print(f'Skip untrusted or malformed task: issue {issue["number"]}')
            continue
        # New issue/run events may still be propagating.
        if now - datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')) < timedelta(minutes=15):
            continue
        prs = json.loads(gh('pr', 'list', '--repo', repo, '--state', 'merged', '--search',
                            f'"Agent: issue #{issue["number"]}" in:title', '--json', 'number,title'))
        if any(p['title'] == f'Agent: issue #{issue["number"]}' for p in prs):
            gh('issue', 'close', str(issue['number']), '--repo', repo, '--reason', 'completed',
               '--comment', 'Watchdog reconciled existing merged implementation; no duplicate execution.')
            continue
        matching = [r for r in runs if r.get('display_title') == f'Jespersen executor issue #{issue["number"]}']
        if matching:
            gh('issue', 'close', str(issue['number']), '--repo', repo, '--reason', 'not planned',
               '--comment', 'Watchdog recovered a terminal executor attempt without accepted merge. Retained source requires independent QA before acceptance.')
            os.environ['ISSUE_NUMBER'] = str(issue['number'])
            recover()
            return
        comments = pages(repo, f'issues/{issue["number"]}/comments?per_page=100')
        if dispatch(repo, issue, runs, comments, now):
            return


if __name__ == '__main__':
    import sys
    if '--count-active' in sys.argv:
        print(active_count(os.environ['GITHUB_REPOSITORY']))
    elif '--ledger-issues' in sys.argv:
        print(json.dumps(ledger_issues(os.environ['GITHUB_REPOSITORY'])))
    elif '--ledger-prs' in sys.argv:
        print(json.dumps(ledger_prs(os.environ['GITHUB_REPOSITORY'])))
    else:
        main()
