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
        if args[:2] == ('issue','list'):
            return json.dumps([{'title':'[AGENT] PRIVATE-DATA-006 — recovery 3.1','number':4,'state':'OPEN'}])
        raise AssertionError(args)
    monkeypatch.setattr(module,'gh',duplicate_gh)
    module.main()
    assert not any(c[:2] == ('issue','create') for c in calls)
