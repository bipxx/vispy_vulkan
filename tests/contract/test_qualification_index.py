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


def test_legacy_retention_cannot_silently_ignore_archive_reconstruction(monkeypatch):
    put = virtual(monkeypatch)
    record, source = retention_fixture(put)
    record['reconstructions'] = [dict(input=source, archive=put('unit/archive.json', {}), member='source')]
    with pytest.raises(qi.InventoryError, match='explicit evidence store'):
        qi.validate_retention(record)


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


@pytest.mark.parametrize('bad', [None, 'later-failure', 'wrong-workflow', 'missing-workflow',
                               'duplicate-workflow', 'legacy-and-workflow', 'omitted-history'])
def test_separate_workflow_attempts_keep_complete_history(monkeypatch, bad):
    put = virtual(monkeypatch)
    attempts = []
    for sequence, workflow in enumerate(('state', 'capture'), 1):
        attempts.append({'id': workflow + '-pass', 'sequence': sequence, 'outcome': 'passed',
            'retention': None, 'resolution': None, 'report': put('unit/' + workflow + '.json', {
                'status': 'PASS_ALL_NO_OPENGL_GATES', 'process_exit': 0, 'child_waited': True,
                'workflow': {'id': workflow}})})
    if bad == 'later-failure':
        attempts.append({'id': 'state-fail', 'sequence': 3, 'outcome': 'failed', 'retention': None,
            'resolution': None, 'report': put('unit/state-fail.json', {'status': 'FAIL',
                'process_exit': 1, 'child_waited': True, 'workflow': {'id': 'state'}})})
    history = {'schema': 1, 'kind': 'workflow-attempt-history', 'profile': 'unit',
        'wheel_sha256': '1' * 64,
        'attempts': [{k: a[k] for k in ('id', 'sequence', 'outcome', 'report')} for a in attempts]}
    entry = {'profile': 'unit', 'attempts': attempts, 'selected_attempt': None,
        'selected_workflow_attempts': [{'workflow': w, 'attempt': w + '-pass'} for w in ('state', 'capture')]}
    if bad == 'wrong-workflow': entry['selected_workflow_attempts'][0]['attempt'] = 'capture-pass'
    elif bad == 'missing-workflow': entry['selected_workflow_attempts'].pop()
    elif bad == 'duplicate-workflow': entry['selected_workflow_attempts'].append(entry['selected_workflow_attempts'][0])
    elif bad == 'legacy-and-workflow': entry['selected_attempt'] = 'state-pass'
    elif bad == 'omitted-history': history['attempts'].pop()
    if bad:
        with pytest.raises(qi.InventoryError):
            qi.validate_workflow_attempts(entry, {'state', 'capture'}, qi.ROOT, history, '1' * 64)
    else:
        selected = qi.validate_workflow_attempts(entry, {'state', 'capture'}, qi.ROOT, history, '1' * 64)
        assert {k: a['id'] for k, a in selected.items()} == {'state': 'state-pass', 'capture': 'capture-pass'}


@pytest.mark.parametrize('fault', [None, 'wrong-profile', 'wrong-wheel', 'workflow-mismatch',
                                 'missing-observation', 'unknown-workflow'])
def test_resolved_pre_workflow_failure_can_precede_latest_success(monkeypatch, fault):
    put = virtual(monkeypatch)
    failure = dict(id='early',sequence=1,outcome='failed',workflow='state',retention=None,
        resolution=None,report=put('unit/early.json',dict(status='FAIL',process_exit=1,child_waited=True)))
    failed_identity = qi.attempt_identity(failure)
    resolution = dict(schema=1,kind='attempt-resolution',status='APPROVED',independent=True,
        reviewer='synthetic-unit-only',attempt_sha256=qi.digest(failed_identity),profile='unit',
        wheel_sha256='1'*64,disposition='Original pre-observation failure retained; latest run is a separate success.')
    if fault=='wrong-profile': resolution['profile']='other'
    elif fault=='wrong-wheel': resolution['wheel_sha256']='2'*64
    failure['resolution']=put('unit/resolution.json',resolution)
    success=dict(id='latest',sequence=2,outcome='passed',workflow='state',retention=None,resolution=None,
        report=put('unit/latest.json',dict(status='PASS_ALL_NO_OPENGL_GATES',process_exit=0,child_waited=True,workflow={'id':'state'})))
    if fault=='workflow-mismatch': success['workflow']='capture'
    elif fault=='missing-observation': success['report']=put('unit/latest.json',dict(status='PASS_ALL_NO_OPENGL_GATES',process_exit=0,child_waited=True))
    elif fault=='unknown-workflow':
        failure['workflow']='outside'
        resolution['attempt_sha256']=qi.digest(qi.attempt_identity(failure))
        failure['resolution']=put('unit/resolution.json',resolution)
    attempts=[failure,success]
    history=dict(schema=1,kind='workflow-attempt-history',profile='unit',wheel_sha256='1'*64,
        attempts=[qi.attempt_identity(a) for a in attempts])
    entry=dict(profile='unit',attempts=attempts,selected_attempt=None,
        selected_workflow_attempts=[dict(workflow='state',attempt='latest')])
    if fault:
        messages={'wrong-profile':'failure resolution belongs','wrong-wheel':'failure resolution belongs',
            'workflow-mismatch':'bound and observed workflow identities differ',
            'missing-observation':'attempt lacks observed workflow identity',
            'unknown-workflow':'unselected candidate workflow'}
        with pytest.raises(qi.InventoryError,match=messages[fault]):
            qi.validate_workflow_attempts(entry,{'state'},qi.ROOT,history,'1'*64)
    else:
        assert qi.validate_workflow_attempts(entry,{'state'},qi.ROOT,history,'1'*64)['state']==success


@pytest.mark.parametrize('swapped', [False, True])
def test_subject_binds_each_row_to_its_workflow_attempt(monkeypatch, swapped):
    put, subject = synthetic_subject(monkeypatch)
    covered = qi.validate_retention({})
    def retain(reference):
        covered.add((reference['path'], reference['sha256']))
        return reference
    profile = subject['profiles'][0]
    state_runtime = retain(put('unit/state-runtime.json', {'status': 'PASS_ALL_NO_OPENGL_GATES',
        'process_exit': 0, 'child_waited': True, 'workflow': {'id': 'state'}}))
    capture_runtime = retain(put('unit/capture-runtime.json', {'status': 'PASS_ALL_NO_OPENGL_GATES',
        'process_exit': 0, 'child_waited': True, 'workflow': {'id': 'capture'}}))
    rows = []
    for feature, runtime in (('unit', state_runtime), ('crop', capture_runtime)):
        gate = retain(put('unit/' + feature + '-gate.json', {'raw_reports': {
            'runtime': state_runtime if swapped and feature == 'crop' else runtime}}))
        receipt = retain(put('unit/' + feature + '-receipt.json', {'gates': {'execution-api': gate}}))
        rows.append({'feature': feature, 'profile': profile['profile'], 'state': 'qualified',
            'workflow': {'id': 'state' if feature == 'unit' else 'capture'},
            'receipt': receipt, 'identity': {'wheel_sha256': '3' * 64}})
    subject['ledger'] = put('unit/ledger.json', {'rows': rows})
    # Replace the virtual selection with both workflows, preserving all joins.
    selection_path = qi.retained_file(qi.ROOT, subject['selection'])
    selection = qi.read_json(selection_path)
    crop = {'feature': 'crop', 'profile': profile['profile'], 'criterion': 'crop.ordinary'}
    selection['closure'].append(crop)
    subject['selection'] = put('unit/selection.json', selection)
    profile['attempts'] = [dict(profile['attempts'][0], id=name, sequence=i, report=report)
        for i, (name, report) in enumerate((('state-pass', state_runtime), ('capture-pass', capture_runtime)), 1)]
    profile['selected_attempt'] = None
    profile['selected_workflow_attempts'] = [{'workflow': w, 'attempt': w + '-pass'} for w in ('state', 'capture')]
    profile['attempt_history'] = retain(put('unit/history.json', {'schema': 1,
        'kind': 'workflow-attempt-history', 'profile': profile['profile'], 'wheel_sha256': '3' * 64,
        'attempts': [{k: a[k] for k in ('id', 'sequence', 'outcome', 'report')} for a in profile['attempts']]}))
    qi.seal(subject)
    if swapped:
        with pytest.raises(qi.InventoryError, match='selected original attempt'):
            qi.validate_subject(subject)
    else:
        result = qi.validate_subject(subject)
        assert result['subject_proved'] and len(result['proved']) == 5
        assert not result['admitted']


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


@pytest.mark.parametrize('missing', [None, 'raw', 'wrong-namespace'])
def test_store_native_and_archive_inputs_join_their_retention_namespace(monkeypatch, missing):
    put,subject=synthetic_subject(monkeypatch)
    covered=qi.validate_retention({})
    selector=put('compat/evidence-stores/secondary-v1.json',{'synthetic_unit_only':True})
    original_retained=qi.retained_file
    def root_check(root,reference):
        assert reference==selector
        return root
    monkeypatch.setattr(qi,'evidence_root',root_check)
    monkeypatch.setattr(qi,'evidence_file',lambda root,reference,binding: original_retained(root,reference))
    def stored(name,value):
        return put(qi.EVIDENCE_PREFIX+name,value)
    def plain(reference):
        return dict(reference,path=reference['path'].removeprefix(qi.EVIDENCE_PREFIX))
    raw=stored('unit/raw.json',{'unit_raw':True})
    capture=stored('unit/capture.json',{'files':[{'file':plain(raw)}]})
    wheel=stored('unit/wheel.json',{'unit_wheel':True})
    scope=qi.scope_digest(qi.read_json(qi.retained_file(qi.ROOT,subject['candidate'])))
    archive=put('unit/archive.json',{'kind':'archive-prerequisite','candidate':{'scope_sha256':scope},
        'profile':'unit-profile','wheel':plain(wheel),'native_outputs':[],'evidence_store':selector})
    producer=put('unit/native.json',{'kind':'original-linux-ci-native-reuse','candidate':subject['candidate'],
        'reuse':{'profile':'unit-profile','evidence_store':selector},'capture':plain(capture)})
    profile=subject['profiles'][0];profile['archive']=archive;profile['producer']=producer
    subject['evidence_store']=selector
    for reference in (archive,producer,wheel,capture,raw):
        if reference==raw and missing:
            if missing=='wrong-namespace':covered.add((plain(raw)['path'],raw['sha256']))
        else:covered.add((reference['path'],reference['sha256']))
    qi.seal(subject)
    if missing:
        with pytest.raises(qi.InventoryError,match='artifact/native proof has unretained inputs'):
            qi.validate_subject(subject)
    else:
        result=qi.validate_subject(subject)
        assert result['subject_proved'] and not result['admitted']
        # The store selector is a verified current declaration, not a file that
        # had to exist in an original producer's retained-input inventory.
        assert (selector['path'],selector['sha256']) not in covered


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


def test_historical_subject_preserves_120_obligations_and_rejects_current_toolset():
    before = qi.DEFAULT.read_bytes()
    subject = qi.read_json(qi.DEFAULT)
    selection = qi.read_json(qi.ROOT / subject['selection']['path'])
    assert len(selection['requested']) == len(selection['closure']) == 120
    assert len({entry['profile'] for entry in selection['closure']}) == 2
    # This exact historical packet pins an older preparation-tool inventory.
    # Its scope remains evidence; it must not approve today's changed tools.
    with pytest.raises(qi.InventoryError, match='incomplete preparation verifier/tool identities'):
        qi.validate_subject(subject)
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
