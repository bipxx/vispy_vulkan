# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only adapter for original native_epoch producer records.

Historical commands are validated as historical commands, not rewritten into
the managed-recipe protocol. Candidate reuse still needs independent approval.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path, PureWindowsPath

try:
    from . import native_epoch
    from .compatibility_candidate import scope_digest, validate_candidate
    from .compatibility_conservation import digest
    from .compatibility_inventory import ROOT, InventoryError, check, read_json, shape, unique_by
    from .qualification_artifact import SDK_SHA, native_sdk, retained_file, sha, validate_sdk
    from .qualification_native import production_inputs, parse_cache
except ImportError:
    import native_epoch
    from compatibility_candidate import scope_digest, validate_candidate
    from compatibility_conservation import digest
    from compatibility_inventory import ROOT, InventoryError, check, read_json, shape, unique_by
    from qualification_artifact import SDK_SHA, native_sdk, retained_file, sha, validate_sdk
    from qualification_native import production_inputs, parse_cache

SCHEMA = 'compat/qualification-epoch.schema.json'
MEMBERS = {'vispy/_dawn.cp312-win_amd64.pyd', 'vispy/visuals/text/_sdf_cpu.cp312-win_amd64.pyd',
           'vispy/VkLayer_vispy_submit.dll', 'vispy/VkLayer_vispy_submit.json'}


def validate_join(ownership, ownership_sha, frozen, status, terminal, commands, ctest, outputs, binaries):
    """Original protocol semantic join; no current candidate fields in producer."""
    check(ownership['schema'] == frozen['schema'] == 1 and ownership['sealed'] is True,
          'original native epoch is unsealed')
    check(type(ownership['epoch']) is int and ownership['epoch'] >= 26
          and ownership['epoch'] == frozen['epoch'] == status['epoch'], 'original epoch identity differs')
    check(frozen['snapshot_epoch'] == ownership['snapshot_epoch']
          and frozen['ownership_manifest_sha256'] == ownership_sha, 'original freeze belongs to another producer')
    check(frozen['source_files'] == ownership['source_files']
          and frozen['source_tree_sha256'] == native_epoch.tree_digest(ownership['source_files'])
          and status['source_tree_sha256'] == frozen['source_tree_sha256'], 'original source freeze differs')
    harness = {name: ref['sha256'] for name, ref in ownership['harness_inputs'].items()}
    check(frozen['harness_files'] == harness and frozen['harness_tree_sha256'] == native_epoch.tree_digest(harness),
          'original test harness freeze differs')
    check(frozen['protected_native_before'] == frozen['protected_native_after'], 'original producer changed protected binaries')
    check(status['status'] == 'build_and_ctest_passed' and status['sdk_manifest_sha256'] == ownership['sdk_manifest_sha256'] == SDK_SHA,
          'original build did not complete with admitted SDK')
    check(status['in_place_copy'] is False and status['gpu_qualified'] is False
          and status['sdk_tint_reader_enabled'] is False and frozen['sdk_tint_reader_enabled'] is False,
          'original qualification scope was relabelled')
    check(type(terminal['exit_code']) is int and terminal['exit_code'] == 0 and terminal['child_waited'] is True,
          'original producer exit/wait proof missing')
    check(terminal['ownership_manifest_sha256'] == ownership_sha
          and terminal['source_tree_sha256'] == frozen['source_tree_sha256'], 'original terminal producer identity differs')
    targets = ownership['targets']
    check(len(targets) == len(set(targets)) and native_epoch.REQUIRED_TARGETS <= set(targets),
          'original producer target inventory incomplete')
    check(set(commands) == {'configure', 'build', 'ctest', 'dependencies-after'}, 'original command records incomplete')
    for command in commands.values():
        check(type(command) is dict and set(command) == {'argv', 'CL_MPCount'}
              and command['CL_MPCount'] == '3' and type(command['argv']) is list and command['argv'],
              'original native command malformed')
    build = commands['build']['argv']
    check(build[1:] == ['--build', terminal['build_directory'], '--config', 'Release', '--parallel', '3',
                       '--target', *targets, '--', '/p:CL_MPCount=3'], 'original build command differs from original protocol')
    check(commands['ctest']['argv'][1:] == ['--test-dir', terminal['build_directory'], '-C', 'Release',
                                         '--output-on-failure', '--output-junit', terminal['ctest_output']],
          'original CTest command differs')
    configure = commands['configure']['argv']
    check(configure[1:5] == ['-S', terminal['source_directory'], '-B', terminal['build_directory']],
          'original configure used different source/build')
    check('-DVISPY_NATIVE_SDK_MANIFEST_SHA256=' + SDK_SHA in configure
          and '-DVISPY_INPLACE=OFF' in configure and '-DVISPY_VERIFY_DEPENDENCIES=ON' in configure,
          'original configure lacks SDK/source protections')
    tests = ownership['ctest_expected_names']
    check(tests and len(tests) == len(set(tests)), 'original CTest policy empty or duplicated')
    native_epoch.check_ctest(io.BytesIO(ctest), tests)
    check(set(outputs) == MEMBERS and all(binaries.get(PureWindowsPath(name).name) == value for name, value in outputs.items()),
          'retained native output differs from original binary inventory')
    return {'status': 'PASS_ORIGINAL_EPOCH_JOIN', 'ownership_sha256': ownership_sha,
            'source_tree_sha256': frozen['source_tree_sha256'], 'native_output_hashes': outputs,
            'native_build_verified': True, 'artifact_admitted': False, 'hardware_qualified': False}


def validate_record(record, root=ROOT):
    root = Path(root)
    schema = read_json(root / SCHEMA)
    shape(record, schema, schema['$defs'])
    candidate = read_json(retained_file(root, record['candidate']))
    validate_candidate(candidate, root, require_reviewed=True)
    reuse = record['reuse']
    check(reuse['candidate_scope_sha256'] == scope_digest(candidate), 'original reuse candidate scope changed')
    check(reuse['ownership_sha256'] == record['ownership']['sha256']
          and reuse['frozen_sha256'] == record['frozen']['sha256'], 'original reuse producer changed')
    profiles = {p['id']: p for p in candidate['profiles']}
    check(reuse['profile'] in profiles, 'original reuse profile missing')
    profile = read_json(retained_file(root, profiles[reuse['profile']]['observation']))
    check((profile['kind'], profile['architecture'], profile['python_abi']) == ('windows-gpu', 'x86_64', 'cp312'),
          'original epoch cannot admit another platform/ABI')
    for kind in ('source', 'scope'):
        review = read_json(retained_file(root, candidate['reviews'][kind]))
        check(type(review.get('native_reuse_links')) is list and digest(reuse) in review['native_reuse_links'],
              'original reuse lacks bound independent review')
    ownership = read_json(retained_file(root, record['ownership']))
    # Only adapt this known original protocol; do not execute code from a record.
    check(set(ownership['tool_files']) == native_epoch.TOOLS, 'original guard tool inventory differs')
    tools = unique_by(record['guard_tools'], lambda r: r['path'], 'original guard tool')
    check(set(tools) == native_epoch.TOOLS, 'original retained guard tools missing')
    for name, ref in tools.items():
        checksum = sha(retained_file(root, ref['file']).read_bytes())
        check(checksum == ownership['tool_files'][name] == sha((root / name).read_bytes()),
              'original protocol version unsupported; explicit adapter review required')
    # Retained source/harness maps verify original bytes without requiring old live scratch.
    for field, refs in (('source_files', record['source_inputs']), ('harness_files', record['harness_inputs'])):
        original = unique_by(refs, lambda r: r['path'], 'original producer input')
        observed = {name: sha(retained_file(root, ref['file']).read_bytes()) for name, ref in original.items()}
        expected = ownership['source_files'] if field == 'source_files' else {
            name: ref['sha256'] for name, ref in ownership['harness_inputs'].items()}
        check(observed == expected, 'original source/harness retained bytes differ')
    runtime = read_json(retained_file(root, candidate['runtime_inputs']))
    production = production_inputs(runtime)
    check(all(ownership['source_files'].get(name) == value for name, value in production.items()),
          'candidate production inputs differ from original epoch')
    prepared = native_epoch.check_preparation(root, ownership, retained_file(root, record['preparation']))
    check(record['preparation']['sha256'] == ownership['preparation_sha256'], 'original preparation differs')
    sdk = read_json(retained_file(root, record['sdk']))
    validate_sdk(sdk, root)
    consumer = read_json(retained_file(root, sdk['consumer']))
    cache = parse_cache(retained_file(root, record['cache']).read_text(encoding='utf-8-sig'))
    terminal = read_json(retained_file(root, record['terminal']))
    required = {'VISPY_INPLACE': 'OFF', 'VISPY_CPU_CONTRACTS_ONLY': 'OFF', 'VISPY_BUILD_CONTRACT_TESTS': 'ON',
                'VISPY_VERIFY_DEPENDENCIES': 'ON', 'VISPY_EXPORT_NATIVE_SDK': 'OFF',
                'VISPY_NATIVE_SDK_MANIFEST_SHA256': SDK_SHA, 'CMAKE_BUILD_TYPE': 'Release',
                'CMAKE_CONFIGURATION_TYPES': 'Release', 'CMAKE_MSVC_RUNTIME_LIBRARY': 'MultiThreadedDLL',
                'CMAKE_CXX_FLAGS': consumer['cxx_flags'], 'CMAKE_CXX_FLAGS_RELEASE': consumer['release_flags'],
                'CMAKE_HOME_DIRECTORY': terminal['source_directory'], 'CMAKE_CACHEFILE_DIR': terminal['build_directory']}
    check(all(cache.get(name) == value for name, value in required.items()), 'original configured cache differs')
    check(PureWindowsPath(cache['VISPY_NATIVE_SDK']) == PureWindowsPath(str(retained_file(root, sdk['manifest']).parent)),
          'original configured SDK origin differs')
    check(PureWindowsPath(cache['Python_EXECUTABLE']) == PureWindowsPath(prepared['installed_environment']['executable']),
          'original configured Python differs')
    projects = unique_by(record['projects'], lambda item: item['target'], 'original generated project')
    check(set(ownership['targets']) <= set(projects), 'original generated project evidence incomplete')
    for name, refs in projects.items():
        before, after = retained_file(root, refs['before']), retained_file(root, refs['after'])
        check(sha(before.read_bytes()) == sha(after.read_bytes()), 'original generated project changed')
        policy = native_sdk.project_mutex_policy(before, 'msvc-stl-init-in-situ-v1')
        check(name == '_sdf_cpu' or policy['cpp_items'] > 0, 'original generated C++ policy missing')
    outputs = unique_by(record['outputs'], lambda r: r['member'], 'original output')
    outputs = {name: sha(retained_file(root, ref['file']).read_bytes()) for name, ref in outputs.items()}
    check(digest(outputs) == reuse['outputs_sha256'], 'original reuse outputs changed')
    commands = unique_by(record['commands'], lambda r: r['phase'], 'original command phase')
    raw_commands = {}
    for phase, ref in commands.items():
        raw_commands[phase] = read_json(retained_file(root, ref['command']))
        retained_file(root, ref['log'])
    check(PureWindowsPath(raw_commands['build']['argv'][0]) == PureWindowsPath(prepared['cmake']['origin']),
          'original build command tool differs from preparation')
    for argument in raw_commands['configure']['argv']:
        if argument.startswith('-D'):
            name, separator, value = argument[2:].partition('=')
            check(separator and cache.get(name) == value, 'original configure/cache argument differs')
    return validate_join(ownership, record['ownership']['sha256'], read_json(retained_file(root, record['frozen'])),
                         read_json(retained_file(root, record['status'])), terminal,
                         raw_commands, retained_file(root, record['ctest']).read_bytes(), outputs,
                         read_json(retained_file(root, record['binaries'])))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_record(read_json(args.record), args.root)
    except (InventoryError, native_epoch.EpochError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
