# SPDX-License-Identifier: AGPL-3.0-only
"""Draft Linux transport controls; synthetic records grant no admission."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools import qualification_linux_native as native
from tools.native_epoch import EpochError
from linux_native_fixture import Capture


@pytest.fixture
def transport(tmp_path):
    prefix = 'runs/native-ci-123-1/'
    workspace = '/ci/workspace'
    members = []

    def store(member, value):
        path = tmp_path/'retained'/member
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(value).encode()
        path.write_bytes(raw)
        row = dict(member=member, path=path.relative_to(tmp_path).as_posix(),
                   sha256=hashlib.sha256(raw).hexdigest())
        members.append(row)
        return row

    state = store(prefix+'state.json', dict(workspace=workspace, run_id='native-ci-123-1'))
    payload = store(prefix+'payload.json', dict(synthetic=True))
    retained = [dict(path=workspace+'/build/'+row['member'], sha256=row['sha256'])
                for row in (state, payload)]
    store(prefix+'terminal.json', dict(retained=retained))
    store(prefix+'cleanup-plan.json', dict(synthetic=True))
    store(prefix+'cleanup-result.json', dict(synthetic=True))
    return tmp_path, dict(members=members)


@pytest.mark.parametrize('windows_paths', [False, True])
def test_transport_references_are_portable(transport, windows_paths):
    root, inventory = transport
    if windows_paths:
        for row in inventory['members']:
            row['path'] = row['path'].replace('/', '\\')
    before = copy.deepcopy(inventory)
    capture = native.capture_from_inventory(inventory, root)
    assert inventory == before
    assert capture['kind'] == 'original-linux-ci-capture-v1'
    assert len(capture['files']) == 2
    for ref in [capture[key] for key in ('state', 'terminal', 'plan', 'cleanup')]:
        assert '\\' not in ref['path']
        assert hashlib.sha256((root/ref['path']).read_bytes()).hexdigest() == ref['sha256']
    assert not any(key.endswith('admitted') for key in capture)


@pytest.mark.parametrize('mutation,match', [
    ('duplicate-member', 'duplicate Linux transport member'),
    ('missing-state', 'exactly one native state'),
    ('second-state', 'exactly one native state'),
    ('missing-terminal', 'member missing'),
    ('missing-cleanup', 'member missing'),
    ('missing-payload', 'member missing'),
    ('wrong-hash', 'changed evidence'),
    ('changed-bytes', 'changed evidence'),
    ('escaping-path', 'invalid relative file'),
    ('outside-origin', 'outside retained build storage'),
    ('scratch-origin', 'scratch or outside'),
    ('duplicate-origin', 'duplicate Linux terminal file'),
    ('wrong-run', 'state/run differs'),
])
def test_transport_rejects_changed_or_incomplete_inputs(transport, mutation, match):
    root, inventory = transport
    rows = inventory['members']

    def rewrite(row, change):
        path = root/row['path']
        data = json.loads(path.read_bytes())
        change(data)
        raw = json.dumps(data).encode()
        path.write_bytes(raw)
        row['sha256'] = hashlib.sha256(raw).hexdigest()

    if mutation == 'duplicate-member': rows.append(copy.deepcopy(rows[0]))
    elif mutation == 'missing-state': rows.pop(0)
    elif mutation == 'second-state':
        row = copy.deepcopy(rows[0]); row['member'] = 'runs/native-ci-124-1/state.json'; rows.append(row)
    elif mutation.startswith('missing-'):
        ending = {'missing-terminal': 'terminal.json', 'missing-cleanup': 'cleanup-result.json',
                  'missing-payload': 'payload.json'}[mutation]
        rows[:] = [row for row in rows if not row['member'].endswith('/'+ending)]
    elif mutation == 'wrong-hash': rows[0]['sha256'] = '0'*64
    elif mutation == 'changed-bytes': (root/rows[0]['path']).write_bytes(b'changed')
    elif mutation == 'escaping-path': rows[0]['path'] = '../state.json'
    elif mutation == 'wrong-run': rewrite(rows[0], lambda d: d.update(run_id='native-ci-124-1'))
    else:
        terminal = next(row for row in rows if row['member'].endswith('/terminal.json'))
        def change(data):
            if mutation == 'duplicate-origin': data['retained'].append(copy.deepcopy(data['retained'][0]))
            else: data['retained'][0]['path'] = ('/outside/state.json' if mutation == 'outside-origin'
                                                else '/ci/workspace/build/work/active/state.json')
        rewrite(terminal, change)
    with pytest.raises(ValueError, match=match):
        native.capture_from_inventory(inventory, root)


@pytest.fixture
def full_capture(tmp_path):
    project = Path(__file__).resolve().parents[2]
    definitions = json.loads((project/native.SCHEMA).read_bytes())['$defs']
    return Capture(tmp_path, project, definitions)


def test_complete_synthetic_native_join(full_capture):
    fixture = full_capture
    result, environment = native.validate_capture(fixture.finish(), fixture.production, fixture.root)
    assert result['status'] == 'PASS_ORIGINAL_LINUX_NATIVE_JOIN'
    assert result['native_build_verified'] is True
    assert result['artifact_admitted'] is result['hardware_qualified'] is False
    assert environment['python'] == '3.12.8 synthetic'
    assert set(result['native_output_hashes']) == set(native.MEMBERS)


@pytest.mark.parametrize('mutation,match', [
    ('active', 'active or relabelled'),
    ('owner', 'active or relabelled'),
    ('source-change', 'source changed'),
    ('production-change', 'candidate production differs'),
    ('registry-removed', 'registry protocol'),
    ('state-exit', 'state/terminal exits differ'),
    ('missing-phase', 'native phases missing'),
    ('reordered-phases', 'native phases missing'),
    ('child-exit', 'native phase failed'),
    ('child-wait', 'child not terminal'),
    ('child-bool-pid', 'child not terminal'),
    ('filtered-build', 'original build command differs'),
    ('build-override', 'unmodelled Linux build override'),
    ('log-hash', 'command log differs'),
    ('build-package', 'locked build packages differ'),
    ('python-origin', 'build interpreter/architecture differs'),
    ('lock-hash', 'locked preparation differs'),
    ('ci-head', 'checkout/CI/workflow identity differs'),
    ('toolchain-changed', 'observed toolchain changed'),
    ('wrong-contract-build', 'contracts use another build'),
    ('contract-admitted', 'contract scope relabelled'),
    ('contract-inventory', 'contract inventories differ'),
    ('ctest-exit', 'CTest child failed'),
    ('ctest-wait', 'CTest child failed'),
    ('ctest-bool-pid', 'CTest child failed'),
    ('ctest-filter', 'CTest command was filtered'),
    ('ctest-tool', 'CTest tool differs'),
    ('missing-ctest', 'Incomplete or duplicate renderer contract discovery'),
    ('skipped-ctest', 'skipped'),
    ('strip-hash', 'raw/strip/wheel output join differs'),
    ('shipping-members', 'shipping output inventory differs'),
])
def test_semantic_native_join_rejects_rebound_changes(full_capture, mutation, match):
    """Recompute transport hashes so each rejection exercises the deeper join."""
    fixture = full_capture
    expected = dict(fixture.production)
    edit = fixture.edit
    if mutation == 'active': edit('state.json', lambda d:d.update(active=dict(pid=999)))
    elif mutation == 'owner': edit('state.json', lambda d:d.update(owner='another-owner'))
    elif mutation == 'source-change': edit('source-after.json', lambda d:d.update(extra='0'*64))
    elif mutation == 'production-change': expected['src/renderer.cpp'] = '0'*64
    elif mutation == 'registry-removed': edit('state.json', lambda d:d.update(registry_required=True))
    elif mutation == 'state-exit': edit('state.json', lambda d:d.update(exit_code=1))
    elif mutation == 'missing-phase': edit('state.json', lambda d:d['commands'].pop(3))
    elif mutation == 'reordered-phases': edit('state.json', lambda d:d['commands'].reverse())
    elif mutation in ('child-exit','child-wait','child-bool-pid','filtered-build','build-override','log-hash'):
        def change(d):
            if mutation == 'child-exit':d['actual_exit'] = 1
            elif mutation == 'child-wait':d['child_waited'] = False
            elif mutation == 'child-bool-pid':d['child_pid'] = True
            elif mutation == 'filtered-build':d['argv'].append('--unmodelled-option')
            elif mutation == 'build-override':d['environment']['CMAKE_TOOLCHAIN_FILE'] = '/other/toolchain'
            else:d['log_sha256'] = '0'*64
        edit('wheel-build-process.json',change);fixture.refresh_receipts()
    elif mutation == 'build-package':edit('native-environment.json',lambda d:d['packages'].update(cmake='0.0'))
    elif mutation == 'python-origin':edit('native-environment.json',lambda d:d.update(machine='aarch64'))
    elif mutation == 'lock-hash':edit('native-environment.json',lambda d:d['input_sha256'].update({'uv.lock':'0'*64}))
    elif mutation == 'ci-head':edit('ci-identity.json',lambda d:d.update(checked_head='b'*40))
    elif mutation == 'toolchain-changed':edit('archive-toolchain.json',lambda d:d['build-python'].update(sha256='0'*64))
    elif mutation == 'missing-ctest':edit('native-contracts/discovery.json',lambda d:d['tests'].pop())
    elif mutation == 'skipped-ctest':
        fixture.put('native-contracts/ctest.xml',fixture.data[str(fixture.evidence/'native-contracts/ctest.xml')].replace(b'/>',b'><skipped/></testcase>',1))
    elif mutation == 'strip-hash':edit('archive.json',lambda d:next(iter(d['native_origin'].values())).update(raw_sha256='0'*64))
    elif mutation == 'shipping-members':edit('archive.json',lambda d:d['native_origin'].pop(next(iter(d['native_origin']))))
    else:
        def change(d):
            if mutation == 'wrong-contract-build':d['build'] = '/other/build'
            elif mutation == 'contract-admitted':d['producer_admitted'] = True
            elif mutation == 'contract-inventory':d['tests'].pop()
            elif mutation == 'ctest-exit':d['commands'][1]['exit_code'] = 1
            elif mutation == 'ctest-wait':d['commands'][1]['child_waited'] = False
            elif mutation == 'ctest-bool-pid':d['commands'][1]['child_pid'] = True
            elif mutation == 'ctest-filter':d['commands'][1]['argv'].append('-R=shader')
            elif mutation == 'ctest-tool':d['ctest']['sha256'] = '0'*64
            else:raise AssertionError(mutation)
        edit('native-contracts/result.json',change);fixture.refresh_contract_link()
    with pytest.raises((ValueError,EpochError),match=match):
        native.validate_capture(fixture.finish(),expected,fixture.root)


def test_native_dispatch_keeps_real_linux_policy_blocked():
    from tools.qualification_native import validate_record
    ref = dict(path='not-an-approved-candidate.json',sha256='0'*64)
    record = dict(schema=1,kind='original-linux-ci-native-reuse',candidate=ref,capture=ref,
        reuse=dict(profile='not-selected',candidate_scope_sha256='0'*64,capture_sha256='0'*64,
            production_sha256='0'*64,impact='Synthetic refusal control',
            abi=dict(tag='cp312',build_version='3.12.8',build_python_sha256='0'*64,
                     consumer_version='3.12.13',consumer_python_sha256='0'*64)))
    with pytest.raises(ValueError,match='Linux producer policy is still blocked'):
        validate_record(record)
