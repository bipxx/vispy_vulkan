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


def test_complete_native_fixture_needs_no_optional_yaml(tmp_path,monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,'yaml',None)
    project = Path(__file__).resolve().parents[2]
    definitions = json.loads((project/native.SCHEMA).read_bytes())['$defs']
    fixture = Capture(tmp_path,project,definitions)
    result,_ = native.validate_capture(fixture.finish(),fixture.production,fixture.root)
    assert result['status']=='PASS_ORIGINAL_LINUX_NATIVE_JOIN'


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


def test_native_dispatch_keeps_legacy_linux_policy_blocked(tmp_path):
    from tools.qualification_native import validate_record
    project=Path(__file__).resolve().parents[2]
    (tmp_path/'compat').mkdir()
    for name in ('qualification-native.schema.json','qualification-artifact.schema.json'):
        (tmp_path/'compat'/name).write_bytes((project/'compat'/name).read_bytes())
    policy=json.loads((project/'compat/qualification-producers.json').read_bytes())
    policy['linux_scope']='blocked-experimental-producer'
    (tmp_path/'compat/qualification-producers.json').write_text(json.dumps(policy))
    ref = dict(path='not-an-approved-candidate.json',sha256='0'*64)
    record = dict(schema=1,kind='original-linux-ci-native-reuse',candidate=ref,capture=ref,
        reuse=dict(profile='not-selected',candidate_scope_sha256='0'*64,capture_sha256='0'*64,
            production_sha256='0'*64,impact='Synthetic refusal control',
            abi=dict(tag='cp312',build_version='3.12.8',build_python_sha256='0'*64,
                     consumer_version='3.12.13',consumer_python_sha256='0'*64)))
    with pytest.raises(ValueError,match='Linux producer policy is still blocked'):
        validate_record(record,tmp_path)


def test_real_native_route_requires_actual_review_before_capture(monkeypatch, without_current_reviews):
    without_current_reviews(native)
    from tools.qualification_native import validate_record
    project=Path(__file__).resolve().parents[2]
    path='compat/candidates/tk-state-resource-1/candidate.json'
    candidate=dict(path=path,sha256=native.sha((project/path).read_bytes()))
    capture=dict(path='must-not-read-an-unapproved-capture.json',sha256='0'*64)
    record=dict(schema=1,kind='original-linux-ci-native-reuse',candidate=candidate,capture=capture,
        reuse=dict(profile='not-selected',candidate_scope_sha256='0'*64,capture_sha256='0'*64,
            production_sha256='0'*64,impact='Actual unreviewed candidate refusal control',
            abi=dict(tag='cp312',build_version='3.12.8',build_python_sha256='0'*64,
                     consumer_version='3.12.13',consumer_python_sha256='0'*64)))
    monkeypatch.setattr(native,'validate_capture',lambda *a,**kw:pytest.fail('unreviewed candidate reached capture'))
    with pytest.raises(ValueError,match='candidate source and scope review remain pending'):
        validate_record(record)


@pytest.fixture
def synthetic_reuse(full_capture, monkeypatch):
    """Exercise outer joins with a candidate-validation seam, never real approval."""
    fixture = full_capture
    project = Path(__file__).resolve().parents[2]
    capture = fixture.finish()
    result, _ = native.validate_capture(capture, fixture.production, fixture.root)
    objects = {}

    def put(name, value):
        objects[name] = value
        raw = json.dumps(value, sort_keys=True).encode()
        path = fixture.root/'outer'/name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        return dict(path=path.relative_to(fixture.root).as_posix(),sha256=native.sha(raw))

    schema = fixture.root/'compat/qualification-artifact.schema.json'
    schema.write_bytes((project/'compat/qualification-artifact.schema.json').read_bytes())
    policy = json.loads((project/'compat/qualification-producers.json').read_bytes())
    policy['linux_scope'] = 'reviewed-full-source-native-proof-required'
    (fixture.root/'compat/qualification-producers.json').write_text(json.dumps(policy))
    profile = dict(kind='wsl-software',architecture='x86_64',python_abi='cp312',
                   python_version='3.12.13 synthetic consumer',interpreter_sha256='e'*64)
    observation = put('profile.json',profile)
    runtime = put('runtime.json',dict(native=[dict(path=path,sha256=sha) for path,sha in fixture.production.items()],
                                    build=[],locks=[]))
    candidate = dict(id='synthetic-reuse-only',profiles=[dict(id='synthetic-profile',observation=observation)],
                     runtime_inputs=runtime,reviews={})
    capture_ref = put('capture.json',capture)
    reuse = dict(profile='synthetic-profile',candidate_scope_sha256=native.scope_digest(candidate),
        capture_sha256=capture_ref['sha256'],production_sha256=result['production_sha256'],
        impact='Synthetic fixture: unchanged production inputs; no real review or admission',
        abi=dict(tag='cp312',build_version='3.12.8',build_python_sha256='b'*64,
                 consumer_version='3.12.13',consumer_python_sha256='e'*64))
    for kind in ('source','scope'):
        candidate['reviews'][kind] = put(kind+'.json',dict(native_reuse_links=[native.digest(reuse)]))
    candidate_ref = put('candidate.json',candidate)
    record = dict(schema=1,kind='original-linux-ci-native-reuse',candidate=candidate_ref,capture=capture_ref,reuse=reuse)

    def reviewed(candidate, root, require_reviewed=False):
        assert candidate['id']=='synthetic-reuse-only'
        assert root==fixture.root and require_reviewed is True
    monkeypatch.setattr(native,'validate_candidate',reviewed)
    return fixture,record,objects,put


def test_synthetic_reuse_preserves_distinct_build_and_consumer_python(synthetic_reuse):
    fixture,record,_,_ = synthetic_reuse
    result = native.validate_record(record,fixture.root)
    assert result['status']=='PASS_ORIGINAL_LINUX_NATIVE_JOIN'
    assert result['artifact_admitted'] is result['hardware_qualified'] is False
    assert record['reuse']['abi']['build_version']=='3.12.8'
    assert record['reuse']['abi']['consumer_version']=='3.12.13'


@pytest.mark.parametrize('mutation,match', [
    ('scope-hash','reuse scope/capture changed'),
    ('capture-hash','reuse scope/capture changed'),
    ('unselected-profile','reuse profile is not selected'),
    ('source-review','lacks exact independent review'),
    ('scope-review','lacks exact independent review'),
    ('string-review','lacks exact independent review'),
    ('build-version','ABI facts differ'),
    ('build-python','ABI facts differ'),
    ('consumer-version','ABI facts differ'),
    ('consumer-python','ABI facts differ'),
    ('production','production identity changed'),
    ('other-platform','cannot admit another platform/ABI'),
    ('other-architecture','cannot admit another platform/ABI'),
    ('other-abi','cannot admit another platform/ABI'),
    ('unreviewed-candidate','synthetic candidate review refusal'),
])
def test_reuse_requires_exact_review_and_abi_links(synthetic_reuse,monkeypatch,mutation,match):
    fixture,record,objects,put = synthetic_reuse
    reuse = record['reuse']
    candidate = objects['candidate.json']
    if mutation in ('scope-hash','capture-hash'):
        reuse['candidate_scope_sha256' if mutation=='scope-hash' else 'capture_sha256']='0'*64
    elif mutation=='unselected-profile':reuse['profile']='not-selected'
    elif mutation.endswith('-review'):
        kind='source' if mutation!='scope-review' else 'scope'
        candidate['reviews'][kind]=put(kind+'.json',dict(native_reuse_links=
            native.digest(reuse) if mutation=='string-review' else ['0'*64]))
        record['candidate']=put('candidate.json',candidate)
    elif mutation=='unreviewed-candidate':
        def reject(*args,**kwargs):raise ValueError('synthetic candidate review refusal')
        monkeypatch.setattr(native,'validate_candidate',reject)
    else:
        if mutation=='production':reuse['production_sha256']='0'*64
        elif mutation in ('build-version','build-python','consumer-version','consumer-python'):
            key={'build-version':'build_version','build-python':'build_python_sha256',
                 'consumer-version':'consumer_version','consumer-python':'consumer_python_sha256'}[mutation]
            reuse['abi'][key]='3.12.0' if key.endswith('version') else '0'*64
        else:
            profile=objects['profile.json']
            key,value={'other-platform':('kind','linux-gpu'),'other-architecture':('architecture','aarch64'),
                       'other-abi':('python_abi','cp313')}[mutation]
            profile[key]=value
            candidate['profiles'][0]['observation']=put('profile.json',profile)
        # Keep every unrelated outer edge valid so rejection reaches the changed
        # ABI/production/profile field rather than an earlier checksum mismatch.
        reuse['candidate_scope_sha256']=native.scope_digest(candidate)
        for kind in ('source','scope'):
            candidate['reviews'][kind]=put(kind+'.json',dict(native_reuse_links=[native.digest(reuse)]))
        record['candidate']=put('candidate.json',candidate)
    with pytest.raises(ValueError,match=match):native.validate_record(record,fixture.root)


@pytest.fixture
def recorded_ctest_tools():
    """Actual tool-format excerpt, CI 40231008361/artifact 12613888894.

    The complete original run failed shader_contract. These observations only
    test its launcher/backend representation; they do not approve that run.
    """
    scratch='/home/runner/work/_temp/vispy-linux-vulkan-40231008361-1/build/work/native-ci-40231008361-1'
    package=scratch+'/env/lib/python3.12/site-packages/cmake/data/bin/'
    base='/home/runner/work/_temp/uv-python-dir/cpython-3.12.8-linux-x86_64-gnu/bin/'
    python_sha='0dc3a692fa85fcdb7f1a5877d2adf179809ac417a07ffde2373c832863800a15'
    contract=dict(ctest=dict(origin=scratch+'/env/bin/ctest',
        sha256='83e1e1363a2f3d4c78f5a37964030154f8722e2a564a8d16212be49cf7ea14fa'))
    tools=dict(CMAKE_CTEST_COMMAND=dict(origin=package+'ctest',resolved=package+'ctest',
        sha256='5dc0f9c7dd3905390cc684708867c0597d4b99a09a93e74950f868af41b73b97'))
    settings=dict(CMAKE_CTEST_COMMAND=package+'ctest',CMAKE_COMMAND=package+'cmake')
    environment=dict(packages=dict(cmake='4.4.4'),python_executable_sha256=python_sha,
                     base_python_executable_sha256=python_sha,base_python_executable=base+'python')
    aliases=dict(actions=[dict(link=scratch+'/env/bin/python3',raw='python',target=base+'python3.12',
                              action='copy-interpreter',sha256=python_sha)])
    return contract,tools,settings,environment,scratch,aliases


def test_recorded_ctest_launcher_and_packaged_elf_have_distinct_hashes(recorded_ctest_tools):
    contract,tools,settings,environment,scratch,aliases=recorded_ctest_tools
    assert contract['ctest']['sha256']!=tools['CMAKE_CTEST_COMMAND']['sha256']
    native.validate_ctest_tool(contract,tools,settings,environment,scratch,aliases)


@pytest.mark.parametrize('mutation,match', [
    ('launcher-hash','tool differs'),('launcher-origin','tool differs'),
    ('launcher-python','tool differs'),('backend-origin','backend differs'),
    ('backend-resolved','backend differs'),('backend-hash','backend hash missing'),
    ('cmake-origin','backend differs'),('package-version','package differs'),
    ('missing-copy','interpreter differs'),('duplicate-copy','interpreter differs'),
    ('copy-hash','interpreter differs'),('copy-action','interpreter differs'),
    ('copy-parent','interpreter differs'),('copy-name','interpreter differs'),
    ('base-hash','interpreter differs'),('base-parent','interpreter differs'),
    ('conflated-hashes','identities were conflated'),
])
def test_recorded_launcher_toolchain_rejects_changed_identity(recorded_ctest_tools,mutation,match):
    contract,tools,settings,environment,scratch,aliases=recorded_ctest_tools
    if mutation=='launcher-hash':contract['ctest']['sha256']='0'*64
    elif mutation=='launcher-origin':contract['ctest']['origin']=settings['CMAKE_CTEST_COMMAND']
    elif mutation=='launcher-python':contract['ctest']['sha256']=native.sha(native.ctest_launcher_bytes(scratch+'/env/bin/python'))
    elif mutation=='backend-origin':tools['CMAKE_CTEST_COMMAND']['origin']=scratch+'/env/bin/ctest'
    elif mutation=='backend-resolved':tools['CMAKE_CTEST_COMMAND']['resolved']='/other/bin/ctest'
    elif mutation=='backend-hash':tools['CMAKE_CTEST_COMMAND']['sha256']='not-a-sha256'
    elif mutation=='cmake-origin':settings['CMAKE_COMMAND']='/other/bin/cmake'
    elif mutation=='package-version':environment['packages']['cmake']='4.0.0'
    elif mutation=='missing-copy':aliases['actions'].clear()
    elif mutation=='duplicate-copy':aliases['actions'].append(copy.deepcopy(aliases['actions'][0]))
    elif mutation=='copy-hash':aliases['actions'][0]['sha256']='0'*64
    elif mutation=='copy-action':aliases['actions'][0]['action']='unverified-symlink'
    elif mutation=='copy-parent':aliases['actions'][0]['target']='/other/bin/python3.12'
    elif mutation=='copy-name':aliases['actions'][0]['target']=aliases['actions'][0]['target'].replace('python3.12','other')
    elif mutation=='base-hash':environment['base_python_executable_sha256']='0'*64
    elif mutation=='base-parent':environment['base_python_executable']='/other/bin/python'
    else:tools['CMAKE_CTEST_COMMAND']['sha256']=contract['ctest']['sha256']
    with pytest.raises(ValueError,match=match):
        native.validate_ctest_tool(contract,tools,settings,environment,scratch,aliases)
