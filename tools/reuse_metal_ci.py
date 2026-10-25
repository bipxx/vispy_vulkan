# SPDX-License-Identifier: AGPL-3.0-only
"""Reuse exact original Metal build-only artifacts; never grant GPU admission."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import struct
import sys
import zipfile

try:
    from . import reuse_linux_ci as transport
    from .native_epoch import project_inventory
    from .qualification_native import parse_cache
except ImportError:
    import reuse_linux_ci as transport
    from native_epoch import project_inventory
    from qualification_native import parse_cache

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT/'compat/metal-ci-reuse.json'


def require(condition, message):
    if not condition: raise ValueError(message)


def source_inputs(source):
    result = project_inventory(source)
    for name in ('tools/audit_metal_wheel.py', 'compat/runtime-package.json'):
        result[name] = transport.digest(source/name)
    return result


def validate_inputs(inventory, pin, arch, source, workspace):
    require(arch in ('arm64', 'x86_64'), 'Unknown Metal architecture')
    require(source_inputs(source) == pin['source_inputs'],
            'Changed Metal production/package/auditor inputs; explicit fresh decision required')
    members = {row['member']: row for row in inventory['members']}
    require(len(members) == len(inventory['members']), 'Duplicate original Metal member')
    def retained(name):
        require(name in members, 'Missing original Metal input: '+name)
        row = members[name]; path = workspace/row['path']
        require(transport.digest(path) == row['sha256'], 'Changed original Metal input: '+name)
        return path
    prefix = 'metal-evidence-'+arch+'/'
    document = lambda name: transport.read(retained(prefix+name))
    identity = document('ci-identity.json')
    require(identity['repository'] == pin['repository'] and identity['run_id'] == pin['run_id']
            and identity['attempt'] == pin['attempt'] and identity['source_head'] == pin['source_head']
            and identity['checked_head'] == pin['checked_head']
            and pin['source_head'] in identity['parents']
            and identity['job_key'] == 'build'
            and identity['job_name'] == 'Metal wheel '+arch+' CPython 3.12.8'
            and identity['workflow'] == dict(path='.github/workflows/metal-wheel.yml',
                 sha256=pin['original_workflow_sha256']), 'Original Metal CI identity differs')
    require(retained(prefix+'source-revision.txt').read_text().strip() == pin['checked_head'],
            'Original Metal source revision differs')
    archive = document('archive.json'); consumer = document('consumer.json')
    require(archive['status'] == 'PASS_METAL_WHEEL_ARCHIVE_BUILD_ONLY'
            and archive['architecture'] == arch and archive['GPU_qualified'] is False
            and archive['source_revision'] == pin['checked_head'], 'Original Metal archive audit differs')
    require(consumer['status'] == 'PASS_INSTALLED_METAL_WHEEL_CPU_IMPORTS_ONLY'
            and consumer['architecture'] == arch and consumer['GPU_qualified'] is False
            and consumer['wheel_sha256'] == archive['wheel_sha256'], 'Original Metal consumer differs')
    wheel_name = PurePosixPath(archive['wheel']).name
    require(wheel_name.endswith('-cp312-cp312-macosx_13_0_'+arch+'.whl'), 'Original Metal wheel tag differs')
    wheel = retained(prefix+'wheels/'+wheel_name)
    require(transport.digest(wheel) == archive['wheel_sha256'], 'Original Metal wheel digest differs')
    cache = parse_cache(retained('metal-native-'+arch+'/CMakeCache.txt').read_text())
    for key, value in dict(VISPY_CPU_CONTRACTS_ONLY='OFF', VISPY_INPLACE='OFF',
            VISPY_VERIFY_DEPENDENCIES='ON', DAWN_ENABLE_METAL='ON', DAWN_ENABLE_VULKAN='OFF',
            DAWN_ENABLE_NULL='OFF', CMAKE_OSX_ARCHITECTURES=arch, CMAKE_OSX_DEPLOYMENT_TARGET='13.0').items():
        require(cache.get(key) == value, 'Original Metal configuration differs: '+key)
    sys.path.insert(0, str(source/'cmake'))
    from runtime_package import wheel_package_hashes
    hashes = wheel_package_hashes(wheel, root=source, suffix='.cpython-312-darwin.so', platform='darwin')
    require(hashes == archive['package_hashes'], 'Original Metal package audit differs')
    native = {'vispy/_dawn.cpython-312-darwin.so', 'vispy/visuals/text/_sdf_cpu.cpython-312-darwin.so'}
    require(set(archive['native']) == native, 'Original Metal native inventory differs')
    with zipfile.ZipFile(wheel) as stream:
        for name in native:
            record = archive['native'][name]
            raw = retained('metal-native-'+arch+'/'+PurePosixPath(name).name)
            stripped = retained(prefix+'native-origin/'+name)
            require(transport.digest(raw) == record['raw_sha256'], 'Original Metal raw leaf differs')
            require(transport.digest(stripped) == hashes[name] == record['wheel_sha256']
                    == record['controlled_stripped_sha256'], 'Original Metal stripped leaf differs')
            data = stream.read(name)
            require(len(data) >= 8 and struct.unpack_from('<II', data) ==
                    (0xfeedfacf, {'arm64': 0x0100000c, 'x86_64': 0x01000007}[arch]),
                    'Original Metal Mach-O architecture differs')
            for line in record['otool_dependencies'].splitlines()[1:]:
                require(line.strip().split(' (', 1)[0].startswith(('/usr/lib/', '/System/Library/')),
                        'Original Metal dependency audit differs')
    require(consumer['installed_members_verified'] == len(hashes), 'Original Metal installed inventory differs')
    for module, name in [('vispy._dawn', 'vispy/_dawn.cpython-312-darwin.so'),
                         ('vispy.visuals.text._sdf_cpu', 'vispy/visuals/text/_sdf_cpu.cpython-312-darwin.so')]:
        require(consumer['compiled_modules'][module]['sha256'] == hashes[name],
                'Original Metal installed native bytes differ')
    # New projection retains the original producer revision and hashes. It is
    # explicitly separate from the original archive.json, whose bytes stay intact.
    projection = dict(archive, wheel=str(wheel), original_archive_sha256=transport.digest(retained(prefix+'archive.json')),
                      reused_original_run=pin['run_id'], artifact_admitted=False)
    return dict(wheel=wheel, archive=projection, original_archive=retained(prefix+'archive.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--owner', default='ci')
    parser.add_argument('--arch', choices=('arm64', 'x86_64'), required=True)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    workspace = transport.no_alias(args.workspace.absolute())
    context = transport.Context(workspace, ROOT/'compat/build-hygiene.json', None)
    scratch = context.scratch(args.run_id); context.marker(scratch, args.run_id, args.owner)
    context.check_capacity(0, 0)
    evidence = workspace/'build/runs'/args.run_id; evidence.mkdir(parents=True, exist_ok=True)
    pin = transport.read(REFERENCE)
    require(pin['schema'] == 1 and pin['repository'] == 'bipxx/vispy_vulkan', 'Unknown Metal reuse reference')
    selected = dict(pin, **pin['architectures'][args.arch])
    path = args.archive or transport.download(selected, scratch, evidence,
                                               workflow_path='.github/workflows/metal-wheel.yml')
    inventory = transport.import_archive(path, selected, workspace)
    transport.write(evidence/'reuse-original-inventory.json', inventory)
    transport.transport_retention(inventory, workspace, evidence, kind='original-metal-ci-reuse-inputs')
    checked = validate_inputs(inventory, pin, args.arch, ROOT, workspace)
    transport.write(evidence/'reuse-archive.json', checked['archive'])
    transport.wheel_requirement(checked['wheel'], evidence)
    transport.write(evidence/'reuse-result.json', dict(status='VERIFIED_ORIGINAL_METAL_BUILD_ONLY',
                    architecture=args.arch, original_run=pin['run_id'], GPU_qualified=False, artifact_admitted=False))
    if os.environ.get('GITHUB_ENV'):
        with Path(os.environ['GITHUB_ENV']).open('a') as stream:
            stream.write('ARCHIVE_REPORT='+str(evidence/'reuse-archive.json')+'\n')
    print('VERIFIED_ORIGINAL_METAL_BUILD_ONLY; GPU qualification remains false')


if __name__ == '__main__': main()
