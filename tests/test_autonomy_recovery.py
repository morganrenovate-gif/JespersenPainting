"""Synthetic regression checks for control-plane failure recovery."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from parse_review_verdict import parse
from recover_agent_task import recovery_body
import pytest


def test_review_prose_and_fail():
    assert parse('Review completed.\nVERDICT: PASS\nEvidence follows.') == 'PASS'
    assert parse('VERDICT: FAIL\nFix rounding.') == 'FAIL'


@pytest.mark.parametrize('text', ['PASS', '', 'VERDICT: PASS\nVERDICT: FAIL',
                                  'Quoted VERDICT: PASS', 'VERDICT: PASS\nVERDICT: PASS'])
def test_ambiguous_or_missing_verdict_fails_closed(text):
    with pytest.raises(ValueError):
        parse(text)


def test_recovery_retains_scope_and_does_not_nest_instruction():
    issue = {'body': 'Task ID: PRIVATE-DATA-006\nClient context: jespersen-painting\nPermission tier: T1\nEnvironment: staging\nPublic-safe task package: yes\nObjective:\nSynthetic extraction\nRequested work:\nKeep source immutable\nAcceptance:\nIndependent QA\nConstraints:\nNo provider writes\nRollback:\nRevert source\n'}
    first = recovery_body(issue, 1, 1)
    second = recovery_body({'body': first}, 1, 2)
    assert second.count('Recovery root issue:') == 1
    assert second.count('Remediation instruction:') == 1
    assert 'No provider writes' in second
    assert 'Recovery attempt: 2' in second
    with pytest.raises(ValueError):
        recovery_body({'body': issue['body'].replace('Permission tier: T1', 'Permission tier: T3')}, 1, 1)


def test_recovery_budget_and_duplicate_child(monkeypatch):
    import json
    import recover_agent_task as module
    import agent_watchdog
    monkeypatch.setattr(agent_watchdog,'valid_task',lambda *args: True)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'synthetic/repository')
    monkeypatch.setenv('ISSUE_NUMBER', '3')
    calls = []
    issue = {'state':'CLOSED', 'stateReason':'NOT_PLANNED', 'body':'Task ID: PRIVATE-DATA-006\nRecovery root issue: 1\nRecovery attempt: 2\n'}
    def gh(*args):
        calls.append(args)
        if args[:2] == ('issue','view'):
            return json.dumps(issue)
        return ''
    monkeypatch.setattr(module,'gh',gh)
    module.main()
    assert any(c[:2] == ('issue','comment') for c in calls)
    assert not any(c[:2] == ('workflow','run') for c in calls)
    calls.clear()
    issue['body'] = 'Task ID: PRIVATE-DATA-006\n'
    def duplicate_gh(*args):
        calls.append(args)
        if args[:2] == ('issue','view'):
            return json.dumps(issue)
        if args[:2] == ('api','--paginate'):
            return json.dumps([[{'title':'[AGENT] PRIVATE-DATA-006 — recovery 3.1','number':4,'state':'closed'}]])
        raise AssertionError(args)
    monkeypatch.setattr(module,'gh',duplicate_gh)
    monkeypatch.setattr(agent_watchdog,'gh',duplicate_gh)
    module.main()
    assert not any(c[:2] == ('issue','create') for c in calls)


def test_dispatch_interruption_retries_after_grace_and_respects_budget(monkeypatch):
    import agent_watchdog as module
    import subprocess
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
    calls = []
    monkeypatch.setattr(module, 'gh', lambda *args: calls.append(args))
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: None)
    issue = {'number': 4, 'state': 'OPEN', 'body': 'synthetic'}
    comments = [{'user': {'login': 'github-actions[bot]'}, 'body':
                 f'AUTONOMY_DISPATCH attempt=1 at={(now-timedelta(minutes=16)).isoformat()}'}]
    assert module.dispatch('synthetic/repository', issue, [], comments, now)
    assert calls[0][:2] == ('issue', 'comment')
    assert 'attempt=2' in calls[0][-1]
    assert calls[1][:2] == ('workflow', 'run')
    calls.clear()
    assert not module.dispatch('synthetic/repository', issue, [{'status':'in_progress'}], [], now)
    assert not calls
    comments[0]['body'] = f'AUTONOMY_DISPATCH attempt=3 at={(now-timedelta(minutes=16)).isoformat()}'
    assert not module.dispatch('synthetic/repository', issue, [], comments, now)
    assert calls[0][:2] == ('issue', 'close')
    assert not any(c[:2] == ('workflow', 'run') for c in calls)


def test_dispatch_ignores_untrusted_markers_and_refuses_completed(monkeypatch):
    import agent_watchdog as module
    import subprocess
    from datetime import datetime, timezone
    now = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
    calls = []
    monkeypatch.setattr(module, 'gh', lambda *args: calls.append(args))
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: None)
    issue = {'number':4, 'state':'CLOSED'}
    assert not module.dispatch('synthetic/repository', issue, [], [], now)
    assert not calls
    issue['state']='OPEN'
    assert module.dispatch('synthetic/repository', issue, [], [{'user':{'login':'attacker'},
        'body':f'AUTONOMY_DISPATCH attempt=3 at={now.isoformat()}'}], now)
    assert 'attempt=1' in calls[0][-1]


def test_candidate_gate_rejects_changed_sha_closed_and_fork(monkeypatch):
    from wait_candidate_checks import candidate
    monkeypatch.setenv('GITHUB_REPOSITORY', 'synthetic/repository')
    pr = {'state':'open', 'head':{'sha':'accepted', 'repo':{'full_name':'synthetic/repository'}}}
    candidate(pr, 'accepted')
    with pytest.raises(ValueError):
        candidate(pr, 'changed')
    pr['state']='closed'
    with pytest.raises(ValueError):
        candidate(pr, 'accepted')
    pr['state']='open'
    pr['head']['repo']['full_name']='attacker/fork'
    with pytest.raises(ValueError):
        candidate(pr, 'accepted')


def test_watchdog_cancels_only_overdue_active_executor(monkeypatch):
    import agent_watchdog as module
    from datetime import datetime, timezone, timedelta
    calls=[]
    monkeypatch.setenv('GITHUB_REPOSITORY', 'synthetic/repository')
    monkeypatch.setattr(module, 'gh', lambda *args: calls.append(args))
    run={'id':99,'status':'in_progress','run_started_at':(datetime.now(timezone.utc)-timedelta(minutes=46)).isoformat()}
    monkeypatch.setattr(module, 'pages', lambda *args: [run])
    module.main()
    assert calls == [('api','--method','POST','/repos/synthetic/repository/actions/runs/99/cancel')]
    calls.clear()
    run['run_started_at']=datetime.now(timezone.utc).isoformat()
    module.main()
    assert not calls


def test_watchdog_recovers_hard_terminal_attempt(monkeypatch):
    import agent_watchdog as module
    from datetime import datetime, timezone, timedelta
    calls=[]
    monkeypatch.setenv('GITHUB_REPOSITORY', 'synthetic/repository')
    issue={'number':4,'title':'[AGENT] PRIVATE-DATA-006','user':{'login':'github-actions[bot]'},
           'created_at':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()}
    run={'id':99,'status':'completed','conclusion':'timed_out','display_title':'Jespersen executor issue #4'}
    monkeypatch.setattr(module, 'pages', lambda repo, endpoint: [run] if endpoint.startswith('actions/') else [issue])
    monkeypatch.setattr(module, 'gh', lambda *args: '[]' if args[:2]==('pr','list') else calls.append(args))
    monkeypatch.setattr(module, 'recover', lambda: calls.append(('recover',)))
    monkeypatch.setattr(module, 'valid_task', lambda *args: True)
    module.main()
    assert calls[0][:2] == ('issue','close')
    assert calls[1] == ('recover',)


def test_malformed_and_untrusted_issues_do_not_block_controller(monkeypatch):
    import agent_watchdog as module
    import subprocess
    from types import SimpleNamespace
    monkeypatch.setattr(module, 'gh', lambda *args: '{"permission":"read"}')
    untrusted={'number':1,'title':'[AGENT] DATA-006','user':{'login':'attacker'}}
    malformed={'number':2,'title':'[AGENT] DATA-006','user':{'login':'github-actions[bot]'},'body':''}
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=1))
    monkeypatch.setattr(module, 'pages', lambda *args: [untrusted,malformed])
    assert module.active_count('synthetic/repository') == 0
    assert module.ledger_issues('synthetic/repository') == []


def test_ledger_history_retains_only_trusted_envelopes_and_normalizes_states(monkeypatch):
    import agent_watchdog as module
    issues=[{'number':1,'title':'[AGENT] DATA-006','state':'closed','state_reason':'not_planned'},
            {'number':2,'title':'[AGENT] DATA-007','state':'open','state_reason':None}]
    monkeypatch.setattr(module,'pages',lambda *args: issues)
    monkeypatch.setattr(module,'valid_task',lambda repo, issue: issue['number']==1)
    result=module.ledger_issues('synthetic/repository')
    assert len(result)==1 and result[0]['number']==1
    assert result[0]['state']=='CLOSED' and result[0]['stateReason']=='NOT_PLANNED'


def test_untrusted_predictable_child_title_cannot_suppress_recovery(monkeypatch):
    import recover_agent_task as module
    import agent_watchdog
    import json
    calls=[]
    body='Task ID: DATA-006\nClient context: jespersen-painting\nPermission tier: T1\nEnvironment: staging\nPublic-safe task package: yes\nObjective:\nSynthetic source\nRequested work:\nRepair source\nAcceptance:\nTests and independent QA\nConstraints:\nSynthetic only\nRollback:\nRevert source\n'
    monkeypatch.setenv('GITHUB_REPOSITORY','synthetic/repository')
    monkeypatch.setenv('ISSUE_NUMBER','3')
    monkeypatch.setattr(agent_watchdog,'pages',lambda *args: [{'number':4,'title':'[AGENT] DATA-006 — recovery 3.1','state':'closed'}])
    monkeypatch.setattr(agent_watchdog,'valid_task',lambda *args: False)
    def gh(*args):
        calls.append(args)
        if args[:2]==('issue','view'):
            return json.dumps({'state':'CLOSED','stateReason':'NOT_PLANNED','body':body})
        if args[:2]==('issue','create'):
            return 'https://github.com/synthetic/repository/issues/5'
        return ''
    monkeypatch.setattr(module,'gh',gh)
    module.main()
    assert any(c[:2]==('issue','create') for c in calls)
    assert any(c[:2]==('workflow','run') for c in calls)


@pytest.mark.parametrize('conclusion', ['success','failure','timed_out','cancelled'])
def test_exact_dispatched_run_gate_fails_closed(monkeypatch, conclusion):
    import wait_candidate_checks as module
    import json
    from datetime import datetime, timezone, timedelta
    monkeypatch.setenv('GITHUB_REPOSITORY','synthetic/repository')
    monkeypatch.setenv('PR_NUMBER','5')
    monkeypatch.setenv('CANDIDATE_SHA','accepted')
    calls=[]
    def gh(*args):
        calls.append(args)
        if args[0]=='api' and args[1].endswith('/pulls/5'):
            return json.dumps({'state':'open','head':{'sha':'accepted','repo':{'full_name':'synthetic/repository'}}})
        if args[0]=='api':
            return json.dumps({'workflow_runs':[{'id':12,'display_title':'Candidate checks PR #5 accepted',
                'created_at':(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat(),
                'status':'completed','conclusion':conclusion}]})
        return ''
    monkeypatch.setattr(module,'gh',gh)
    if conclusion == 'success':
        module.main()
        assert sum(1 for c in calls if c[0]=='api' and c[1].endswith('/pulls/5')) == 2
    else:
        with pytest.raises(RuntimeError):
            module.main()
    assert any(c[:2]==('workflow','run') for c in calls)
