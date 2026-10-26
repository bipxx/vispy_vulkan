# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic CI exports test joins; these records are never real CI approval."""
from copy import deepcopy
import io
import json

import pytest

from tools import qualification_ci as ci

HEAD = 'a' * 40
MERGE = 'b' * 40


def fixture():
    policy = ci.validate_policy()
    attempts, entries, history = [], [], []
    job_id = 100
    for run_id, workflow in enumerate(policy['workflows'], 10):
        run = {'id': run_id, 'run_attempt': 1, 'path': workflow['path'],
               'head_sha': HEAD, 'repository': {'full_name': ci.REPOSITORY},
               'head_repository': {'full_name': ci.REPOSITORY}, 'event': 'pull_request',
               'status': 'completed', 'conclusion': 'success'}
        entry = {'workflow': workflow['path'], 'run_id': run_id, 'attempt': 1,
                 'run': {'path': 'unit-run.json', 'sha256': '0' * 64},
                 'jobs': {'path': 'unit-jobs.json', 'sha256': '0' * 64}, 'identities': []}
        jobs, identities = [], {}
        for name in workflow['jobs']:
            job_id += 1
            jobs.append({'id': job_id, 'name': name, 'run_id': run_id, 'run_attempt': 1,
                         'head_sha': HEAD, 'status': 'completed', 'conclusion': 'success'})
            identities[job_id] = {'schema': 1, 'kind': 'ci-job-identity', 'repository': ci.REPOSITORY,
                                  'run_id': run_id, 'attempt': 1, 'job_key': workflow['job_key'],
                                  'job_name': name, 'event': 'pull_request', 'source_head': HEAD,
                                  'checked_head': MERGE, 'parents': [HEAD, 'c' * 40],
                                  'workflow': {'path': workflow['path'], 'sha256': workflow['sha256']},
                                  'collector_sha256': policy['collector_sha256']}
            entry['identities'].append({'job_id': job_id,
                                        'report': {'path': 'unit-identity.json', 'sha256': '0' * 64}})
        attempts.append((entry, run, {'total_count': len(jobs), 'jobs': jobs}, identities))
        entries.append(entry)
        history.append(deepcopy(run))
    bundle = {'schema': 1, 'kind': 'required-ci-evidence', 'repository': ci.REPOSITORY,
              'qualification_head': HEAD, 'policy_sha256': ci.sha(ci.ROOT / ci.POLICY),
              'run_history': {'path': 'unit-history.json', 'sha256': '0' * 64}, 'runs': entries}
    return policy, bundle, attempts, {'total_count': len(history), 'workflow_runs': history}


def test_complete_synthetic_ci_join_is_not_artifact_admission():
    policy, bundle, attempts, history = fixture()
    result = ci.validate_attempts(bundle, policy, attempts, history)
    assert len(result['jobs']) == 23
    assert not result['artifact_admitted'] and not result['hardware_qualified']
    assert {job['checked_head'] for job in result['jobs']} == {MERGE}


@pytest.mark.parametrize('change', [
    'repo', 'head', 'reduced-policy', 'missing-workflow', 'duplicate-attempt',
    'wrong-attempt', 'raw-repo', 'raw-head', 'raw-path', 'partial-jobs',
    'missing-job', 'duplicate-job', 'extra-job', 'mixed-attempt', 'job-head',
    'job-failed', 'job-skipped', 'job-cancelled', 'run-pending', 'run-failed',
    'missing-identity', 'identity-job', 'identity-head', 'identity-parents',
    'identity-workflow', 'identity-collector', 'identity-event', 'bool-id',
    'history-pagination', 'omitted-newer-failure', 'omitted-rerun-attempt',
    'history-source', 'history-run-status', 'unknown-field',
])
def test_ci_semantic_controls(change):
    policy, bundle, attempts, history = fixture()
    entry, run, jobs, identities = attempts[0]
    job = jobs['jobs'][0]
    identity = identities[job['id']]
    if change == 'repo': bundle['repository'] = 'another/repo'
    elif change == 'head': bundle['qualification_head'] = 'd' * 40
    elif change == 'reduced-policy': bundle['policy_sha256'] = '0' * 64
    elif change == 'missing-workflow':
        attempts.pop(); bundle['runs'].pop()
    elif change == 'duplicate-attempt':
        attempts.append(deepcopy(attempts[0])); bundle['runs'].append(deepcopy(entry))
    elif change == 'wrong-attempt': entry['attempt'] = 2
    elif change == 'raw-repo': run['head_repository']['full_name'] = 'another/repo'
    elif change == 'raw-head': run['head_sha'] = 'd' * 40
    elif change == 'raw-path': run['path'] = 'other.yml'
    elif change == 'partial-jobs': jobs['total_count'] += 1
    elif change == 'missing-job': jobs['jobs'].pop(); jobs['total_count'] -= 1
    elif change == 'duplicate-job': jobs['jobs'].append(deepcopy(job)); jobs['total_count'] += 1
    elif change == 'extra-job':
        other = deepcopy(job); other['name'] = 'unrequested'; jobs['jobs'].append(other); jobs['total_count'] += 1
    elif change == 'mixed-attempt': job['run_attempt'] = 2
    elif change == 'job-head': job['head_sha'] = 'd' * 40
    elif change.startswith('job-'): job['conclusion'] = change.removeprefix('job-')
    elif change == 'run-pending':
        run.update(status='in_progress', conclusion=None); history['workflow_runs'][0].update(run)
    elif change == 'run-failed':
        run['conclusion'] = 'failure'; history['workflow_runs'][0].update(run)
    elif change == 'missing-identity': identities.pop(job['id'])
    elif change == 'identity-job': identity['job_name'] = 'other'
    elif change == 'identity-head': identity['source_head'] = 'd' * 40
    elif change == 'identity-parents': identity['parents'] = ['c' * 40]
    elif change == 'identity-workflow': identity['workflow']['sha256'] = '0' * 64
    elif change == 'identity-collector': identity['collector_sha256'] = '0' * 64
    elif change == 'identity-event': identity['event'] = 'push'
    elif change == 'bool-id': job['id'] = True
    elif change == 'history-pagination': history['total_count'] += 1
    elif change == 'omitted-newer-failure':
        later = deepcopy(run); later.update(id=999, conclusion='failure')
        history['workflow_runs'].append(later); history['total_count'] += 1
    elif change == 'omitted-rerun-attempt': history['workflow_runs'][0]['run_attempt'] = 2
    elif change == 'history-source': history['workflow_runs'][0]['head_sha'] = 'd' * 40
    elif change == 'history-run-status': history['workflow_runs'][0]['conclusion'] = 'failure'
    elif change == 'unknown-field': bundle['admitted'] = True
    with pytest.raises(ci.InventoryError):
        ci.validate_attempts(bundle, policy, attempts, history)


def test_later_complete_rerun_preserves_first_failure_and_does_not_mix_attempts():
    policy, bundle, attempts, history = fixture()
    first = attempts[0]
    later = deepcopy(first)
    first[1]['conclusion'] = 'failure'
    # A pre-collector failure has no checkout identity and possibly no jobs.
    # Preserve it without inventing a report; only the later success can qualify.
    first[0]['identities'].clear()
    first[2].update(total_count=0, jobs=[])
    first[3].clear()
    later[0]['attempt'] = later[1]['run_attempt'] = 2
    for job in later[2]['jobs']:
        job['run_attempt'] = 2
    for identity in later[3].values():
        identity['attempt'] = 2
    history['workflow_runs'][0] = deepcopy(later[1])
    attempts.append(later); bundle['runs'].append(later[0])
    result = ci.validate_attempts(bundle, policy, attempts, history)
    assert all(job['attempt'] == 2 for job in result['jobs'] if job['workflow'] == first[0]['workflow'])
    assert first[1]['conclusion'] == 'failure'
    assert not first[3]


def test_old_failure_cannot_reference_another_attempts_job_export():
    policy, bundle, attempts, history = fixture()
    first = attempts[0]
    later = deepcopy(first)
    first[1]['conclusion'] = 'failure'
    later[0]['attempt'] = later[1]['run_attempt'] = 2
    for job in later[2]['jobs']: job['run_attempt'] = 2
    for report in later[3].values(): report['attempt'] = 2
    history['workflow_runs'][0] = deepcopy(later[1])
    attempts.append(later); bundle['runs'].append(later[0])
    first[2]['jobs'][0]['run_attempt'] = 2
    with pytest.raises(ci.InventoryError, match='original CI attempt job'):
        ci.validate_attempts(bundle, policy, attempts, history)


def test_policy_default_is_read_only_and_cannot_admit(capsys):
    before = (ci.ROOT / ci.POLICY).read_bytes()
    assert ci.main([]) == 0
    assert (ci.ROOT / ci.POLICY).read_bytes() == before
    assert '"required_jobs": 23' in capsys.readouterr().out


@pytest.mark.parametrize('change', ['reduced-jobs', 'missing-workflow', 'stale-workflow', 'stale-collector'])
def test_authoritative_policy_cannot_be_reduced_or_resealed_to_stale_inputs(monkeypatch, change):
    policy = deepcopy(ci.validate_policy())
    if change == 'reduced-jobs': policy['workflows'][0]['jobs'].pop()
    elif change == 'missing-workflow': policy['workflows'].pop()
    elif change == 'stale-workflow': policy['workflows'][0]['sha256'] = '0' * 64
    else: policy['collector_sha256'] = '0' * 64
    read = ci.read_json
    monkeypatch.setattr(ci, 'read_json', lambda path: policy if path == ci.ROOT / ci.POLICY else read(path))
    with pytest.raises(ci.InventoryError):
        ci.validate_policy()


def test_capture_retains_actual_merge_parents_even_for_shallow_checkout(monkeypatch):
    # Intercept only the output stream; no environment, scratch or file created.
    output = ci.ROOT / 'unit-only-ci-identity-not-written.json'
    assert not output.exists()
    saved = []

    class Captured(io.BytesIO):
        def close(self):
            saved.append(self.getvalue())
            super().close()

    original_open = ci.Path.open
    monkeypatch.setattr(ci.Path, 'open', lambda path, *a, **kw:
                        Captured() if path == output else original_open(path, *a, **kw))
    read = ci.read_json
    monkeypatch.setattr(ci, 'read_json', lambda path:
                        {'pull_request': {'head': {'sha': HEAD}}} if path == 'unit-event' else read(path))
    for name, value in {'GITHUB_EVENT_PATH': 'unit-event', 'GITHUB_EVENT_NAME': 'pull_request',
                        'GITHUB_REPOSITORY': ci.REPOSITORY, 'GITHUB_RUN_ID': '10',
                        'GITHUB_RUN_ATTEMPT': '2', 'GITHUB_JOB': 'cpu'}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(ci.subprocess, 'check_output', lambda cmd, **kw:
                        MERGE + '\n' if cmd[1] == 'rev-parse' else
                        'tree ' + 'd' * 40 + '\nparent ' + HEAD + '\nparent ' + 'c' * 40 + '\n\nmessage\n')
    ci.capture(ci.CPU, 'CPU windows-x86_64 CPython 3.12.8', output)
    report = json.loads(saved[0])
    assert report['checked_head'] == MERGE and report['source_head'] == HEAD
    assert report['parents'] == [HEAD, 'c' * 40] and report['attempt'] == 2
    assert not output.exists()
