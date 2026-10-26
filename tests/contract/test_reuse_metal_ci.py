# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic Metal build-only reuse joins; no native commands or GPU execution."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile

import pytest
from tools import reuse_metal_ci as metal


@pytest.fixture(params=['arm64', 'x86_64'])
def original(tmp_path, monkeypatch, request):
    arch = request.param
    pin = dict(repository='bipxx/vispy_vulkan', run_id=123, attempt=1,
               source_head='a'*40, checked_head='b'*40, original_workflow_sha256='c'*64,
               source_inputs={'synthetic': 'd'*64})
    monkeypatch.setattr(metal, 'source_inputs', lambda root: {'synthetic': 'd'*64})
    sys.path.insert(0, str(metal.ROOT/'cmake'))
    import runtime_package
    prefix = 'metal-evidence-'+arch+'/'
    names = ['vispy/_dawn.cpython-312-darwin.so', 'vispy/visuals/text/_sdf_cpu.cpython-312-darwin.so']
    native = {}; hashes = {}; rows = []
    def put(member, data):
        path = tmp_path/'retained'/member
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        row = dict(member=member, path=path.relative_to(tmp_path).as_posix(),
                   sha256=hashlib.sha256(data).hexdigest())
        rows.append(row); return path
    def document(member, value):return put(member, json.dumps(value).encode())
    source = tmp_path/'source'; source.mkdir()
    (source/'cmake').mkdir()
    wheel_name = 'vispy-0.17.0+vulkan.1-cp312-cp312-macosx_13_0_'+arch+'.whl'
    wheel_path = tmp_path/wheel_name
    with zipfile.ZipFile(wheel_path, 'w') as stream:
        for name in names:
            data = struct.pack('<II', 0xfeedfacf, {'arm64':0x0100000c, 'x86_64':0x01000007}[arch])+b'synthetic stripped'
            raw = data+b'synthetic raw'; checksum = hashlib.sha256(data).hexdigest()
            stream.writestr(name, data); hashes[name] = checksum
            put('metal-native-'+arch+'/'+Path(name).name, raw)
            put(prefix+'native-origin/'+name, data)
            native[name] = dict(raw_sha256=hashlib.sha256(raw).hexdigest(), wheel_sha256=checksum,
                controlled_stripped_sha256=checksum, otool_dependencies='synthetic:\n /usr/lib/libSystem.B.dylib (compatibility version 1.0)')
    put(prefix+'wheels/'+wheel_name, wheel_path.read_bytes())
    monkeypatch.setattr(runtime_package, 'wheel_package_hashes', lambda *a, **kw: hashes)
    identity = dict(repository=pin['repository'], run_id=123, attempt=1, source_head='a'*40,
        checked_head='b'*40, parents=['a'*40], job_key='build', job_name='Metal wheel '+arch+' CPython 3.12.8',
        workflow=dict(path='.github/workflows/metal-wheel.yml', sha256='c'*64))
    documents = {}
    documents['ci-identity.json'] = identity
    documents['archive.json'] = dict(status='PASS_METAL_WHEEL_ARCHIVE_BUILD_ONLY', architecture=arch,
        GPU_qualified=False, source_revision='b'*40, wheel='/original/'+wheel_name,
        wheel_sha256=hashlib.sha256(wheel_path.read_bytes()).hexdigest(), package_hashes=hashes, native=native)
    documents['consumer.json'] = dict(status='PASS_INSTALLED_METAL_WHEEL_CPU_IMPORTS_ONLY', architecture=arch,
        GPU_qualified=False, wheel_sha256=documents['archive.json']['wheel_sha256'],
        installed_members_verified=2, compiled_modules={
            'vispy._dawn': {'sha256': hashes[names[0]]},
            'vispy.visuals.text._sdf_cpu': {'sha256': hashes[names[1]]}})
    for name, value in documents.items(): document(prefix+name, value)
    put(prefix+'source-revision.txt', b'b'*40+b'\n')
    settings = dict(VISPY_CPU_CONTRACTS_ONLY='OFF', VISPY_INPLACE='OFF', VISPY_VERIFY_DEPENDENCIES='ON',
        DAWN_ENABLE_METAL='ON', DAWN_ENABLE_VULKAN='OFF', DAWN_ENABLE_NULL='OFF',
        CMAKE_OSX_ARCHITECTURES=arch, CMAKE_OSX_DEPLOYMENT_TARGET='13.0')
    put('metal-native-'+arch+'/CMakeCache.txt', ''.join(k+':STRING='+v+'\n' for k,v in settings.items()).encode())
    return tmp_path, source, pin, arch, dict(members=rows), documents


def rewrite(root, inventory, member, change):
    row = next(row for row in inventory['members'] if row['member']==member)
    path = root/row['path']; value = json.loads(path.read_bytes()); change(value)
    path.write_bytes(json.dumps(value).encode()); row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_build_only_join_preserves_original_records(original):
    root, source, pin, arch, inventory, docs = original
    snapshot = {row['member']: (root/row['path']).read_bytes() for row in inventory['members']}
    result = metal.validate_inputs(inventory, pin, arch, source, root)
    assert result['archive']['artifact_admitted'] is False
    assert result['archive']['GPU_qualified'] is False
    assert result['archive']['source_revision'] == pin['checked_head']
    assert result['archive']['wheel'] == str(result['wheel'])
    assert snapshot == {row['member']: (root/row['path']).read_bytes() for row in inventory['members']}


@pytest.mark.parametrize('mutation,match', [
    ('source', 'Changed Metal production'), ('run', 'CI identity'), ('head', 'CI identity'),
    ('arch', 'archive audit'), ('gpu', 'archive audit'), ('consumer', 'consumer differs'),
    ('raw', 'raw leaf'), ('stripped', 'stripped leaf'), ('dependency', 'dependency audit'),
    ('installed', 'installed inventory'), ('installed-native', 'installed native'), ('missing', 'Missing original'),
])
def test_semantic_mutations_cannot_rebind_outer_transport_hashes(original, monkeypatch, mutation, match):
    root, source, pin, arch, inventory, docs = original
    prefix = 'metal-evidence-'+arch+'/'
    if mutation == 'source': monkeypatch.setattr(metal, 'source_inputs', lambda root: {'changed': '0'*64})
    elif mutation == 'missing': inventory['members'] = [row for row in inventory['members'] if not row['member'].endswith('source-revision.txt')]
    else:
        member = 'archive.json'
        if mutation in ('run', 'head'):
            member = 'ci-identity.json'
            change = lambda value: value.update({('run_id' if mutation=='run' else 'source_head'): (999 if mutation=='run' else '0'*40)})
        elif mutation == 'arch': change = lambda value: value.update(architecture='other')
        elif mutation == 'gpu': change = lambda value: value.update(GPU_qualified=True)
        elif mutation == 'consumer':
            member='consumer.json'; change=lambda value:value.update(status='FAILED_PRESERVED')
        elif mutation in ('raw', 'stripped', 'dependency'):
            def change(value):
                first = next(iter(value['native'].values()))
                key = {'raw':'raw_sha256', 'stripped':'controlled_stripped_sha256', 'dependency':'otool_dependencies'}[mutation]
                first[key] = '0'*64 if mutation!='dependency' else 'synthetic:\n /unbundled/lib.dylib (compatibility version 1.0)'
        elif mutation == 'installed':
            member='consumer.json'; change=lambda value:value.update(installed_members_verified=0)
        elif mutation == 'installed-native':
            member='consumer.json'
            def change(value):value['compiled_modules']['vispy._dawn']['sha256']='0'*64
        rewrite(root, inventory, prefix+member, change)
    with pytest.raises(ValueError, match=match):metal.validate_inputs(inventory, pin, arch, source, root)


@pytest.fixture
def python_original(original, monkeypatch):
    from tools import qualification_artifact as qa
    from test_qualification_artifact import sample, wheel_bytes
    root, source, pin, arch, inventory, docs = original
    # Restore actual inventory/package readers: this fixture now supplies their
    # complete synthetic inputs rather than the older isolated native stubs.
    monkeypatch.undo()
    entries, inputs = sample('darwin', arch)
    prefix = 'metal-evidence-' + arch + '/'
    def replace(member, payload):
        row = next(row for row in inventory['members'] if row['member'] == member)
        (root / row['path']).write_bytes(payload)
        row['sha256'] = hashlib.sha256(payload).hexdigest()
    for name, payload in entries.items():
        if name == qa.runtime_package.MEMBER:
            relative = 'compat/runtime-package.json'
        elif name in inputs['pure_hashes']:
            relative = 'src/' + name
        elif name in inputs['notices']:
            base = name.removeprefix('vispy/_licenses/')
            relative = base if base in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md') else 'third_party/licenses/' + base
        else:
            continue
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    for name, payload in {'CMakeLists.txt': b'synthetic', 'CMakePresets.json': b'{}',
                          'uv.lock': b'synthetic', 'README.md': b'Original README\n',
                          'cpp/render.cpp': b'original native',
                          'tools/audit_metal_wheel.py': b'synthetic auditor',
                          'pyproject.toml': b'license-files = ["LICENSE", "LICENSE-BSD", "LICENSING.md"]\n'}.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    pin['source_inputs'] = metal.source_inputs(source)
    pin['package_metadata_inputs'] = {'README.md': metal.transport.digest(source / 'README.md')}
    wheel = wheel_bytes(entries)
    wheel_name = Path(docs['archive.json']['wheel']).name
    replace(prefix + 'wheels/' + wheel_name, wheel)
    native = {}
    for name in inputs['native_hashes']:
        payload = entries[name]
        raw = payload + b'raw'
        replace('metal-native-' + arch + '/' + Path(name).name, raw)
        replace(prefix + 'native-origin/' + name, payload)
        native[name] = dict(docs['archive.json']['native'][name],
                            raw_sha256=qa.sha(raw), wheel_sha256=qa.sha(payload),
                            controlled_stripped_sha256=qa.sha(payload))
    hashes = {name: qa.sha(payload) for name, payload in entries.items() if name.startswith('vispy/')}
    rewrite(root, inventory, prefix + 'archive.json', lambda value: value.update(
        wheel_sha256=qa.sha(wheel), package_hashes=hashes, native=native))
    rewrite(root, inventory, prefix + 'consumer.json', lambda value: value.update(
        wheel_sha256=qa.sha(wheel), installed_members_verified=len(hashes), compiled_modules={
            'vispy._dawn': {'sha256': hashes['vispy/_dawn.cpython-312-darwin.so']},
            'vispy.visuals.text._sdf_cpu': {'sha256': hashes['vispy/visuals/text/_sdf_cpu.cpython-312-darwin.so']}}))
    return root, source, pin, arch, inventory


def test_explicit_metal_python_change_preserves_original_native_and_history(python_original):
    root, source, pin, arch, inventory = python_original
    snapshot = {row['member']: (root / row['path']).read_bytes() for row in inventory['members']}
    (source / 'src/vispy/__init__.py').write_bytes(b'# Updated Python\n')
    with pytest.raises(ValueError, match='Changed Metal production/package'):
        metal.validate_inputs(inventory, pin, arch, source, root)
    checked = metal.validate_inputs(inventory, pin, arch, source, root, package_current_python=True)
    assert checked['package_report']['changed_members'] == ['vispy/__init__.py']
    assert checked['archive']['GPU_qualified'] is False and checked['package_report']['artifact_admitted'] is False
    assert checked['archive']['source_revision'] == pin['checked_head']
    assert snapshot == {row['member']: (root / row['path']).read_bytes() for row in inventory['members']}
    with zipfile.ZipFile(io.BytesIO(checked['package_bytes'])) as archive:
        assert archive.read('vispy/__init__.py') == b'# Updated Python\n'


@pytest.mark.parametrize('name', ['cpp/render.cpp', 'tools/audit_metal_wheel.py', 'LICENSE-BSD',
                                 'compat/runtime-package.json', 'README.md'])
def test_explicit_metal_python_path_keeps_native_auditor_notice_manifest_and_metadata_guards(python_original, name):
    root, source, pin, arch, inventory = python_original
    path = source / name
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        metal.validate_inputs(inventory, pin, arch, source, root, package_current_python=True)


def test_metal_cli_installs_and_retains_current_wheel_without_relabelling_original(python_original, monkeypatch):
    root, source, pin, arch, inventory = python_original
    pin['schema'] = 1
    pin['architectures'] = {arch: {}}
    reference = root / 'pin.json'
    reference.write_text(json.dumps(pin))
    inventory = dict(inventory, run_id=pin['run_id'])
    (source / 'src/vispy/__init__.py').write_bytes(b'# CLI Python update\n')
    class Context:
        def __init__(self, *args): pass
        def scratch(self, run): return root / 'build/work' / run
        def marker(self, *args): pass
        def check_capacity(self, *args): pass
    monkeypatch.setattr(metal.transport, 'Context', Context)
    monkeypatch.setattr(metal.transport, 'import_archive', lambda *args: inventory)
    monkeypatch.setattr(metal, 'ROOT', source)
    monkeypatch.setattr(metal, 'REFERENCE', reference)
    monkeypatch.delenv('GITHUB_ENV', raising=False)
    monkeypatch.setattr(sys, 'argv', ['metal-reuse', '--workspace', str(root), '--run-id', 'unit',
                                    '--archive', 'synthetic-transport', '--arch', arch, '--package-current-python'])
    metal.main()
    evidence = root / 'build/runs/unit'
    original = json.loads((evidence / 'reuse-original-archive.json').read_bytes())
    current = json.loads((evidence / 'reuse-archive.json').read_bytes())
    assert original['source_revision'] == pin['checked_head']
    assert 'source_revision' not in current
    assert current['original_native_source_revision'] == pin['checked_head']
    assert current['GPU_qualified'] is False
    wheel = Path(current['wheel'])
    assert current['wheel_sha256'] == metal.transport.digest(wheel) != original['wheel_sha256']
    requirement = (evidence / 'wheel-requirements.txt').read_text()
    assert wheel.as_uri() in requirement and current['wheel_sha256'] in requirement
    retained = json.loads((evidence / 'reuse-inputs.json').read_bytes())['retained']
    assert retained == [dict(path=str(wheel), sha256=current['wheel_sha256'],
                             roles=['source', 'evidence', 'licenses', 'repro'])]
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read('vispy/__init__.py') == b'# CLI Python update\n'
