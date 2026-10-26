# SPDX-License-Identifier: AGPL-3.0-only
"""Index orchestration controls; synthetic verifier seams never approve artifacts.

Individual validators retain their own real report/semantic control suites.
Virtual retained files here create no scratch or fabricated on-disk approvals.
"""
from copy import deepcopy
import json

import pytest

from tools import qualification_index as qi


def virtual(monkeypatch):
    objects = {}
    original_read = qi.read_json

    def put(name, value):
        raw = (json.dumps(value, sort_keys=True) + '\n').encode()
        path = qi.ROOT / name
        objects[path] = raw
        return {'path': name, 'sha256': qi.sha(raw)}

    def retained(root, reference):
        path = root / reference['path']
        assert qi.sha(objects[path]) == reference['sha256']
        return path

    monkeypatch.setattr(qi, 'retained_file', retained)
    monkeypatch.setattr(qi, 'read_json', lambda path: json.loads(objects[path]) if path in objects else original_read(path))
    return put


def retention_fixture(put, *, bad=None):
    name = 'unit-index-retention-not-created'
    workspace = 'C:/original-workspace'
    source = put('unit/source.json', {'unit_only': True})
    roles = ['source', 'evidence', 'licenses']
    if bad == 'roles': roles.remove('licenses')
    terminal = {'schema': 1, 'run_id': name, 'owner': 'unit-only', 'state': 'succeeded',
                'process_exit': 0, 'child_waited': bad != 'wait', 'scratch_root': 'build/work/' + name,
                'retained': [{**source, 'roles': roles}]}
    terminal_ref = put('unit/terminal.json', terminal)
    policy, registry = put('unit/policy.json', {}), put('unit/registry.json', {})
    absolute = lambda path: workspace + '/' + path
    plan = {'schema': 1, 'kind': 'build-hygiene-cleanup-plan', 'workspace': workspace,
            'manifest': absolute(terminal_ref['path']), 'manifest_sha256': terminal_ref['sha256'],
            'policy_sha256': policy['sha256'], 'registry_sha256': registry['sha256'],
            'run_id': name, 'owner': 'unit-only', 'scratch_root': absolute('build/work/' + name),
            'retained': [{'path': absolute(source['path']), 'sha256': source['sha256'], 'roles': list(roles)}],
            'snapshot': {'files': [{'path': 'owner.json'}]}}
    if bad == 'manifest': plan['manifest_sha256'] = '0' * 64
    elif bad == 'owner': plan['owner'] = 'other'
    elif bad == 'policy': plan['policy_sha256'] = '0' * 64
    elif bad == 'scope': plan['scratch_root'] = 'C:/outside/work/run'
    elif bad == 'retained': plan['retained'][0]['sha256'] = '0' * 64
    plan_ref = put('unit/plan.json', plan)
    applied = {'actual_exit': 0, 'child_waited': True,
               'command': ['python', 'tools/build_hygiene.py', 'apply', '--plan', absolute(plan_ref['path'])],
               'result': {'status': 'PASS_APPLY', 'deleted': 1, 'retained_verified': 1,
                          'scratch_root': absolute('build/work/' + name)}}
    if bad == 'unapplied': applied['result']['status'] = 'PASS_PLAN'
    elif bad == 'partial': applied['result']['deleted'] = 0
    elif bad == 'wrong-plan': applied['command'][-1] = absolute('unit/other-plan.json')
    elif bad == 'apply-wait': applied['child_waited'] = False
    return {'terminal': terminal_ref, 'plan': plan_ref, 'applied': put('unit/applied.json', applied),
            'policy': policy, 'registry': registry}, source


def test_original_retention_can_be_checked_after_scratch_is_gone(monkeypatch):
    put = virtual(monkeypatch)
    record, source = retention_fixture(put)
    assert qi.validate_retention(record) == {(source['path'], source['sha256'])}


@pytest.mark.parametrize('bad', ['wait', 'roles', 'manifest', 'owner', 'policy', 'scope', 'retained',
                                'unapplied', 'partial', 'wrong-plan', 'apply-wait'])
def test_resealed_retention_control_joins(monkeypatch, bad):
    record, _ = retention_fixture(virtual(monkeypatch), bad=bad)
    with pytest.raises(qi.InventoryError): qi.validate_retention(record)


def test_older_pass_cannot_hide_newer_failure_or_omit_original_history(monkeypatch):
    put = virtual(monkeypatch)
    passed = {'id': 'first', 'sequence': 1, 'outcome': 'passed', 'retention': None, 'resolution': None,
              'report': put('unit/pass.json', {'status': 'PASS_ALL_NO_OPENGL_GATES', 'process_exit': 0, 'child_waited': True})}
    failed = {'id': 'second', 'sequence': 2, 'outcome': 'failed', 'retention': None, 'resolution': None,
              'report': put('unit/fail.json', {'status': 'FAIL', 'process_exit': 1, 'child_waited': True})}
    history = {'schema': 1, 'kind': 'workflow-attempt-history', 'profile': 'unit', 'wheel_sha256': '1' * 64,
               'attempts': [{k: a[k] for k in ('id', 'sequence', 'outcome', 'report')} for a in (passed, failed)]}
    with pytest.raises(qi.InventoryError, match='latest success'):
        qi.validate_attempts([passed, failed], 'first', qi.ROOT, history, 'unit', '1' * 64)
    with pytest.raises(qi.InventoryError, match='original history'):
        qi.validate_attempts([passed], 'first', qi.ROOT, history, 'unit', '1' * 64)


def synthetic_subject(monkeypatch, bad=None):
    """Complete outer join with explicit validator seams, not real gate proof."""
    put = virtual(monkeypatch)
    covered = set()
    def retain(ref): covered.add((ref['path'], ref['sha256'])); return ref
    candidate = {'product_source_commit': '1' * 40}
    candidate_ref = put('unit/candidate.json', candidate)
    scope = qi.scope_digest(candidate)
    closure = [{'feature': 'unit', 'profile': 'unit-profile', 'criterion': 'unit.' + mode}
               for mode in ('failure', 'mutation', 'ordinary', 'recovery')]
    ledger_ref = put('unit/ledger.json', {})
    execution = {'manifest_sha256': '2' * 64, 'candidate': {'path': candidate_ref['path']},
                 'execution': {'path': ledger_ref['path']}}
    execution_ref = put('unit/execution.json', execution)
    selection = {'candidate': {'scope_sha256': scope},
                 'execution_map': {'path': execution_ref['path'], 'scope_sha256': '2' * 64},
                 'requested': closure, 'closure': closure}
    selection_ref = put('unit/selection.json', selection)
    runtime = retain(put('unit/runtime.json', {'status': 'PASS_ALL_NO_OPENGL_GATES', 'process_exit': 0, 'child_waited': True}))
    gate_ref = retain(put('unit/gate.json', {'raw_reports': {'runtime': runtime}}))
    receipt_ref = retain(put('unit/receipt.json', {'gates': {'execution-api': gate_ref}}))
    ledger_ref = put('unit/ledger.json', {'rows': [{'feature': 'unit', 'profile': 'unit-profile',
                         'state': 'qualified', 'receipt': receipt_ref, 'identity': {'wheel_sha256': '3' * 64}}]})
    archive_ref = retain(put('unit/archive.json', {'candidate': {'scope_sha256': scope}, 'profile': 'unit-profile'}))
    native_ref = retain(put('unit/native.json', {'kind': 'native-leaf-provenance', 'candidate': candidate_ref,
                                              'reuse': {'profile': 'unit-profile'}}))
    attempt = {'id': 'attempt-one', 'sequence': 1, 'outcome': 'passed', 'report': runtime,
               'retention': put('unit/retention.json', {}), 'resolution': None}
    history = retain(put('unit/history.json', {'schema': 1, 'kind': 'workflow-attempt-history', 'profile': 'unit-profile',
                       'wheel_sha256': '3' * 64, 'attempts': [{k: attempt[k] for k in ('id', 'sequence', 'outcome', 'report')}]}))
    profile = {'profile': 'unit-profile', 'archive': archive_ref, 'producer': native_ref,
               'producer_retention': attempt['retention'], 'attempts': [attempt], 'selected_attempt': 'attempt-one',
               'attempt_history': history}
    subject = qi.seal({'schema': 1, 'kind': 'qualification-subject', 'manifest_sha256': '0' * 64,
                       'product_source_commit': '1' * 40, 'qualification_head': '4' * 40,
                       'candidate': candidate_ref, 'selection': selection_ref, 'execution': execution_ref,
                       'ledger': ledger_ref, 'profiles': [profile]})
    monkeypatch.setattr(qi, 'validate_candidate', lambda *a, **kw: None)
    monkeypatch.setattr(qi, 'validate_execution', lambda *a, **kw: None)
    monkeypatch.setattr(qi, 'validate_selection', lambda *a, **kw: {'reviewed': bad != 'unreviewed'})
    monkeypatch.setattr(qi, 'validate_archive', lambda *a, **kw: {
        'wheel_sha256': '3' * 64, 'package_hashes': {'native': '5' * 64}})
    monkeypatch.setattr(qi, 'validate_native', lambda *a, **kw: {'native_output_hashes': {'native': '6' * 64 if bad == 'native' else '5' * 64}})
    monkeypatch.setattr(qi, 'validate_retention', lambda *a, **kw: covered)
    if bad == 'missing-profile': subject['profiles'].clear()
    elif bad == 'missing-archive': profile['archive'] = None
    elif bad == 'missing-producer': profile['producer'] = None
    elif bad == 'no-history': profile['attempt_history'] = None
    elif bad == 'unretained': covered.remove((gate_ref['path'], gate_ref['sha256']))
    qi.seal(subject)
    return put, subject


def test_complete_synthetic_outer_join_never_claims_global_completion(monkeypatch):
    _, subject = synthetic_subject(monkeypatch)
    result = qi.validate_subject(subject)
    assert result['subject_proved'] and len(result['proved']) == 4
    assert not any(result[k] for k in ('admitted', 'candidate_complete', 'full_inventory_complete', 'release_complete'))


@pytest.mark.parametrize('missing', [None, 'capture', 'state', 'plan', 'cleanup', 'raw'])
def test_linux_capture_raw_inputs_must_survive_contributing_run(monkeypatch, missing):
    put, subject = synthetic_subject(monkeypatch)
    covered = qi.validate_retention({})
    raw = {name: put('unit/linux-'+name+'.json', {'synthetic': name})
           for name in ('state', 'plan', 'cleanup', 'raw')}
    capture = put('unit/linux-capture.json', {'state': raw['state'], 'plan': raw['plan'],
        'cleanup': raw['cleanup'], 'files': [{'origin': '/synthetic/raw', 'file': raw['raw']}]})
    producer = put('unit/linux-producer.json', {'kind': 'original-linux-ci-native-reuse',
        'candidate': subject['candidate'], 'reuse': {'profile': 'unit-profile'}, 'capture': capture})
    subject['profiles'][0]['producer'] = producer
    for name, ref in {'capture': capture, 'producer': producer, **raw}.items():
        if name != missing: covered.add((ref['path'], ref['sha256']))
    qi.seal(subject)
    if missing:
        with pytest.raises(qi.InventoryError, match='artifact/native proof has unretained inputs'):
            qi.validate_subject(subject)
    else:
        result = qi.validate_subject(subject)
        assert result['subject_proved'] and not result['admitted']


@pytest.mark.parametrize('bad', ['native', 'missing-profile', 'unretained'])
def test_resealed_subject_semantic_controls(monkeypatch, bad):
    _, subject = synthetic_subject(monkeypatch, bad)
    with pytest.raises(qi.InventoryError): qi.validate_subject(subject)


@pytest.mark.parametrize('bad', ['unreviewed', 'missing-archive', 'missing-producer', 'no-history'])
def test_missing_proof_stays_explicitly_incomplete(monkeypatch, bad):
    _, subject = synthetic_subject(monkeypatch, bad)
    result = qi.validate_subject(subject)
    assert not result['subject_proved'] and len(result['missing']) == 4


@pytest.mark.parametrize('bad', [None, 'review-head', 'ci-head', 'basis-subject'])
def test_promotion_review_binds_exact_head_ci_and_subject(monkeypatch, bad):
    put, subject = synthetic_subject(monkeypatch)
    subject_ref = put('unit/subject.json', subject)
    policy = {'path': qi.CI_POLICY, 'sha256': qi.sha((qi.ROOT / qi.CI_POLICY).read_bytes())}
    # Virtual retained reference for the real policy bytes is not read by this join.
    policy = put('unit/policy.json', qi.read_json(qi.ROOT / qi.CI_POLICY))
    # Pin exact real bytes digest separately; original policy checker is tested elsewhere.
    original_sha = qi.sha
    monkeypatch.setattr(qi, 'sha', lambda data: policy['sha256'] if data == (qi.ROOT / qi.CI_POLICY).read_bytes() else original_sha(data))
    ci_ref = put('unit/ci.json', {'unit_only': True})
    monkeypatch.setattr(qi, 'validate_ci', lambda *a, **kw: {'qualification_head': '9' * 40 if bad == 'ci-head' else '4' * 40})
    impact = put('unit/impact.json', {'schema': 1, 'kind': 'change-impact', 'status': 'APPROVED', 'independent': True,
                                     'reviewer': 'synthetic-unit-only', 'subject_sha256': subject['manifest_sha256'], 'qualification_head': '4' * 40})
    basis = qi.seal({'schema': 1, 'kind': 'promotion-basis', 'manifest_sha256': '0' * 64,
                     'subject': subject_ref, 'repository': qi.REPOSITORY, 'qualification_head': '4' * 40,
                     'policy': policy, 'ci': ci_ref, 'impact': impact})
    if bad == 'basis-subject': basis['subject'] = {'path': 'other.json', 'sha256': '0' * 64}; qi.seal(basis)
    basis_ref = put('unit/basis.json', basis)
    review = put('unit/review.json', {'schema': 1, 'kind': 'promotion', 'status': 'APPROVED', 'independent': True,
                                     'reviewer': 'synthetic-unit-only', 'promotion_basis_sha256': '0' * 64 if bad == 'review-head' else basis['manifest_sha256']})
    envelope = {'schema': 1, 'kind': 'promotion-envelope', 'subject': subject_ref, 'basis': basis_ref, 'review': review}
    if bad:
        with pytest.raises(qi.InventoryError): qi.validate_envelope(envelope, strict=True)
    else:
        result = qi.validate_envelope(envelope, strict=True)
        assert result['admitted'] and not result['release_complete']


def test_real_subject_preserves_120_obligations_and_reports_missing_proof():
    before = qi.DEFAULT.read_bytes()
    result = qi.validate_subject(qi.read_json(qi.DEFAULT))
    assert len(result['requested']) == len(result['closure']) == len(result['missing']) == 120
    assert not result['proved'] and not result['blocked']
    assert not result['subject_proved'] and not result['admitted']
    assert len({entry['criterion']['profile'] for entry in result['missing']}) == 2
    assert qi.DEFAULT.read_bytes() == before


def test_strict_cli_cannot_admit_a_subject_without_detached_envelope(monkeypatch, capsys):
    monkeypatch.setattr(qi, 'validate_subject', lambda *a, **kw: {'subject_proved': True, 'admitted': False})
    assert qi.main(['--require-admitted']) == 1
    assert 'requires detached promotion envelope' in capsys.readouterr().out


@pytest.mark.parametrize('field', ['schema', 'kind', 'candidate_complete'])
def test_subject_cannot_add_or_override_completion_fields(monkeypatch, field):
    _, subject = synthetic_subject(monkeypatch)
    subject[field] = True
    qi.seal(subject)
    with pytest.raises(qi.InventoryError): qi.validate_subject(subject)


@pytest.mark.parametrize('change', ['no-wait', 'no-exit', 'wrong-resolution'])
def test_attempt_terminal_and_resolution_proof(monkeypatch, change):
    put = virtual(monkeypatch)
    raw = {'status': 'FAIL', 'process_exit': 1, 'child_waited': True}
    if change == 'no-wait': raw['child_waited'] = False
    elif change == 'no-exit': del raw['process_exit']
    attempt = {'id': 'failed', 'sequence': 1, 'outcome': 'failed', 'report': put('unit/failure.json', raw),
               'retention': None, 'resolution': None}
    if change == 'wrong-resolution':
        attempt['resolution'] = put('unit/resolution.json', {'schema': 1, 'kind': 'attempt-resolution',
            'status': 'APPROVED', 'independent': True, 'reviewer': 'synthetic-unit-only',
            'attempt_sha256': '0' * 64, 'profile': 'unit', 'wheel_sha256': '1' * 64, 'disposition': 'unit test'})
    with pytest.raises(qi.InventoryError): qi.validate_attempts([attempt], None, qi.ROOT, profile='unit', wheel='1' * 64)



@pytest.mark.parametrize('windows_separators', [False, True])
def test_original_absolute_terminal_paths_join_without_rewriting_records(monkeypatch, windows_separators):
    put = virtual(monkeypatch)
    record, source = retention_fixture(put)
    terminal = qi.read_json(qi.retained_file(qi.ROOT, record['terminal']))
    plan = qi.read_json(qi.retained_file(qi.ROOT, record['plan']))
    name = plan['workspace']+'/'+source['path']
    terminal['retained'][0]['path'] = name.replace('/', chr(92)) if windows_separators else name
    record['terminal'] = put('unit/terminal.json', terminal)
    plan['manifest_sha256'] = record['terminal']['sha256']
    record['plan'] = put('unit/plan.json', plan)
    before = deepcopy(terminal)
    assert qi.validate_retention(record) == {(source['path'], source['sha256'])}
    assert qi.read_json(qi.retained_file(qi.ROOT, record['terminal'])) == before


@pytest.mark.parametrize('name', ['C:/outside/source.json',
                                 'C:/original-workspace/../source.json',
                                 'D:/original-workspace/unit/source.json'])
def test_absolute_terminal_paths_cannot_escape_original_workspace(monkeypatch, name):
    put = virtual(monkeypatch)
    record, _ = retention_fixture(put)
    terminal = qi.read_json(qi.retained_file(qi.ROOT, record['terminal']))
    plan = qi.read_json(qi.retained_file(qi.ROOT, record['plan']))
    terminal['retained'][0]['path'] = name
    record['terminal'] = put('unit/terminal.json', terminal)
    plan['manifest_sha256'] = record['terminal']['sha256']
    record['plan'] = put('unit/plan.json', plan)
    with pytest.raises(qi.InventoryError, match='leaves original workspace'):
        qi.validate_retention(record)
