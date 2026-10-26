# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic Metal build-only reuse joins; no native commands or GPU execution."""
import hashlib
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
