# SPDX-License-Identifier: AGPL-3.0-only
"""Validate retained Windows native leaf provenance without rebuilding it.

SDK reuse and generated project checks alone cannot establish a compiled leaf.
The original command, source/configuration, CTest and output joins are mandatory.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path, PureWindowsPath
import re
import xml.etree.ElementTree as ET

try:
    from .compatibility_candidate import scope_digest, validate_candidate
    from .compatibility_conservation import digest
    from .compatibility_inventory import ROOT, InventoryError, check, read_json, shape, unique_by
    from .qualification_artifact import (SDK_SHA, COMPILER_SHA, native_sdk, retained_file,
                                         sha, validate_sdk)
    from . import native_epoch
except ImportError:
    from compatibility_candidate import scope_digest, validate_candidate
    from compatibility_conservation import digest
    from compatibility_inventory import ROOT, InventoryError, check, read_json, shape, unique_by
    from qualification_artifact import SDK_SHA, COMPILER_SHA, native_sdk, retained_file, sha, validate_sdk
    import native_epoch

SCHEMA = 'compat/qualification-native.schema.json'
PHASES = ('dependency-before', 'configure', 'build', 'ctest', 'dependency-after')
NATIVE_TARGETS = {'_dawn', '_sdf_cpu', 'VkLayer_vispy_submit'}
DEPENDENCY_TARGETS = {'native_library_fixture', 'nanobind-static'}
MIN_TARGETS = native_epoch.REQUIRED_TARGETS | DEPENDENCY_TARGETS
MIN_TESTS = native_epoch.REQUIRED_TARGETS - NATIVE_TARGETS
ROLES = {'python', 'base-python', 'cmake', 'ctest', 'compiler'}
ENVIRONMENT = {name: '' for name in ('CL', '_CL_', 'CFLAGS', 'CXXFLAGS', 'CMAKE_TOOLCHAIN_FILE',
                                    'PYTHONPATH', 'PYTHONHOME')}
ENVIRONMENT.update(MSBUILDDISABLENODEREUSE='1', CL_MPCount='3')


def validate_shape(record, kind, root=ROOT):
    definitions = read_json(Path(root) / SCHEMA)['$defs']
    shape(record, definitions[kind], definitions)


def production_inputs(runtime):
    """Compiler/build inputs, excluding unrelated preparation/report helpers."""
    unused = {'cmake/prepare_cp310_candidate.py', 'cmake/prepare_cp311_candidate.py',
              'cmake/prepare_cpython312_candidate.py', 'cmake/prepare_newer_candidates.py',
              'cmake/snapshot_wheel_sources.py'}
    entries = [item for section in ('native', 'build', 'locks') for item in runtime[section]]
    return {name: item['sha256'] for name, item in unique_by(entries, lambda i: i['path'], 'native source input').items()
            if name not in unused}


def source_inputs(runtime, root=ROOT):
    result = production_inputs(runtime)
    root = Path(root)
    harness = {p for p in (root / 'tests').rglob('*') if p.is_file() and p.suffix in ('.cpp', '.hpp', '.h')}
    harness.update(p for p in (root / 'tests/shaders/corpus').rglob('*') if p.is_file())
    for path in harness:
        result[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    return result


def recipe_digest(recipe):
    return digest(recipe)


def production_identity(recipe, outputs):
    """Stable binary identity; candidate and test protocol remain separate edges."""
    return digest({'schema': 1, 'platform': recipe['platform'],
                   'production_inputs_sha256': recipe['production_inputs_sha256'],
                   'sdk_sha256': recipe['sdk_sha256'],
                   'sdk_record_sha256': recipe['sdk_record_sha256'],
                   'preparation_sha256': recipe['preparation_sha256'],
                   'toolchain': recipe['toolchain'], 'outputs': outputs})


def validate_recipe(recipe, root=ROOT):
    validate_shape(recipe, 'recipe', root)
    check(recipe['targets'] == sorted(set(recipe['targets'])) and MIN_TARGETS <= set(recipe['targets']),
          'native recipe omitted or duplicated required targets')
    check(all(target in NATIVE_TARGETS | DEPENDENCY_TARGETS or re.fullmatch(r'[a-z][a-z0-9_]*_contract', target)
              for target in recipe['targets']), 'vendor/unrecognized native build target')
    check(recipe['ctest_names'] == sorted(set(recipe['ctest_names'])) and MIN_TESTS <= set(recipe['ctest_names']),
          'native recipe omitted or duplicated required tests')
    tools = unique_by(recipe['toolchain'], lambda t: t['role'], 'native tool role')
    check(set(tools) == ROLES, 'incomplete native toolchain')
    check(all(PureWindowsPath(t['origin']).is_absolute()
              and '..' not in PureWindowsPath(t['origin']).parts
              and PureWindowsPath(t['origin']).as_posix() == t['origin'] for t in tools.values()),
          'native tool origins must be canonical absolute Windows paths')
    check(tools['compiler']['sha256'] == COMPILER_SHA, 'native compiler is not SDK-qualified')
    check(recipe['sdk_sha256'] == SDK_SHA, 'native recipe uses an unapproved SDK')
    return tools


def parse_cache(text):
    cache = {}
    for line in text.splitlines():
        if re.match(r'[^#/:][^:]*:[^=]+=', line):
            key, value = line.split('=', 1)
            key = key.split(':', 1)[0]
            check(key not in cache, 'duplicate CMake cache setting: ' + key)
            cache[key] = value
    return cache


def cache_policy(recipe, consumer, locations):
    tools = {t['role']: t for t in recipe['toolchain']}
    return {'CMAKE_GENERATOR': 'Visual Studio 17 2022', 'CMAKE_GENERATOR_PLATFORM': 'x64',
            'CMAKE_GENERATOR_TOOLSET': 'version=14.44.35207',
            'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_CONFIGURATION_TYPES': 'Release',
            'CMAKE_CXX_FLAGS': consumer['cxx_flags'], 'CMAKE_CXX_FLAGS_RELEASE': consumer['release_flags'],
            'CMAKE_MSVC_RUNTIME_LIBRARY': 'MultiThreadedDLL', 'VISPY_INPLACE': 'OFF',
            'VISPY_EXPORT_NATIVE_SDK': 'OFF', 'VISPY_VERIFY_DEPENDENCIES': 'ON',
            'VISPY_LEGACY_MSVC_CRT_MUTEX': 'ON', 'VISPY_BUILD_CONTRACT_TESTS': 'ON',
            'VISPY_CPU_CONTRACTS_ONLY': 'OFF', 'VISPY_NATIVE_SDK_MANIFEST_SHA256': SDK_SHA,
            'VISPY_CONTRACT_TESTS_ROOT': (PureWindowsPath(locations['source']) / 'tests').as_posix(),
            'VISPY_CONTRACT_DATASETS_ROOT': '', 'CMAKE_SYSTEM_VERSION': consumer['windows_sdk'],
            'VISPY_NATIVE_SDK': locations['sdk'], 'CMAKE_HOME_DIRECTORY': locations['source'],
            'CMAKE_CACHEFILE_DIR': locations['build'], 'Python_EXECUTABLE': tools['python']['origin']}


def commands(recipe, consumer, locations):
    tools = {t['role']: t['origin'] for t in recipe['toolchain']}
    source = PureWindowsPath(locations['source'])
    configure = [tools['cmake'], '-S', locations['source'], '-B', locations['build'],
                 '-G', 'Visual Studio 17 2022', '-A', 'x64', '-T', 'version=14.44.35207']
    skip = {'CMAKE_GENERATOR', 'CMAKE_GENERATOR_PLATFORM', 'CMAKE_GENERATOR_TOOLSET',
            'CMAKE_HOME_DIRECTORY', 'CMAKE_CACHEFILE_DIR'}
    configure.extend('-D' + key + '=' + str(value) for key, value in cache_policy(recipe, consumer, locations).items()
                     if key not in skip)
    dependency = [tools['python'], str(source / 'cmake/verify_dependencies.py')]
    return {'dependency-before': dependency, 'configure': configure,
            'build': [tools['cmake'], '--build', locations['build'], '--config', 'Release', '--parallel', '3',
                      '--target', *recipe['targets']],
            'ctest': [tools['ctest'], '--test-dir', locations['build'], '-C', 'Release', '--output-on-failure',
                      '--output-junit', locations['ctest_output']],
            'dependency-after': dependency}


def validate_proofs(recipe, raw, expected_sources, before, after, cache_before, cache_after,
                    consumer, projects, ctest_data, outputs, root=ROOT):
    """Semantic join of original, already hash-checked retained inputs."""
    validate_recipe(recipe, root)
    validate_shape(raw, 'result', root)
    check(raw['environment'] == ENVIRONMENT, 'native build environment has unreviewed flags or reusable nodes')
    locations = {key: PureWindowsPath(value) for key, value in raw['locations'].items()}
    check(all(value.is_absolute() and '..' not in value.parts and value.as_posix() == raw['locations'][key]
              for key, value in locations.items()),
          'native locations must be canonical absolute Windows paths')
    work = locations['source'] / 'build/work'
    check(locations['build'].is_relative_to(work) and len(locations['build'].relative_to(work).parts) == 2
          and locations['build'].name == 'native' and locations['ctest_output'].parent == locations['build'].parent,
          'native build must use one managed scratch run')
    check(not locations['sdk'].is_relative_to(work), 'native SDK cannot be copied into managed scratch')
    check(recipe_digest(recipe) == raw['recipe_sha256'], 'native result uses another recipe')
    check(recipe['source_inputs_sha256'] == digest(expected_sources), 'native recipe source identity changed')
    production = {name: value for name, value in expected_sources.items() if not name.startswith('tests/')}
    check(recipe['production_inputs_sha256'] == digest(production), 'native production identity changed')
    check(before == after == expected_sources, 'native source changed/missing before or after build')
    check(raw['source_before_sha256'] == digest(before) and raw['source_after_sha256'] == digest(after),
          'native raw result/source reports are unrelated')
    check(raw['cache_before_sha256'] == sha(cache_before)
          and raw['cache_after_sha256'] == sha(cache_after), 'native raw result/cache reports are unrelated')
    check(cache_before == cache_after, 'native cache changed during build')
    policy = cache_policy(recipe, consumer, raw['locations'])
    cache = parse_cache(cache_after.decode('utf-8-sig'))
    for name, value in policy.items():
        check(cache.get(name) == value, 'native cache differs from reviewed recipe: ' + name)
    expected_commands = commands(recipe, consumer, raw['locations'])
    check(tuple(command['phase'] for command in raw['commands']) == PHASES, 'native phases missing/duplicated/reordered')
    for command in raw['commands']:
        check(command['argv'] == expected_commands[command['phase']], 'native command differs from reviewed recipe')
        check(command['exit_code'] == 0 and command['child_waited'] is True, 'native child failed/unawaited')
    expected_projects = set(recipe['targets'])
    check(set(projects) == expected_projects, 'native project policy inventory differs from build targets')
    attested = {}
    for name, pair in projects.items():
        first = native_sdk.project_mutex_policy(pair[0], 'msvc-stl-init-in-situ-v1')
        last = native_sdk.project_mutex_policy(pair[1], 'msvc-stl-init-in-situ-v1')
        first_sha, last_sha = native_sdk.sha256(pair[0]), native_sdk.sha256(pair[1])
        check(first == last and first_sha == last_sha, 'native generated project changed during build: ' + name)
        check(name == '_sdf_cpu' or first['cpp_items'] > 0, 'native target has no observed C++ compilation items')
        attested[name] = first_sha
    check(raw['project_sha256'] == [{'target': name, 'sha256': attested[name]} for name in sorted(attested)],
          'native raw result/project policies are unrelated')
    native_epoch.check_ctest(io.BytesIO(ctest_data), recipe['ctest_names'])
    check(raw['ctest_sha256'] == sha(ctest_data), 'native raw result uses another CTest result')
    check(outputs and raw['outputs'] == [{'member': name, 'sha256': value} for name, value in sorted(outputs.items())],
          'native output bytes do not match the observed build')
    expected = {'vispy/_dawn.cp312-win_amd64.pyd', 'vispy/visuals/text/_sdf_cpu.cp312-win_amd64.pyd',
                'vispy/VkLayer_vispy_submit.dll', 'vispy/VkLayer_vispy_submit.json'}
    check(set(outputs) == expected, 'native build did not produce every shipping member')
    return {'status': 'PASS_NATIVE_BUILD_JOIN', 'recipe_sha256': recipe_digest(recipe),
            'production_sha256': production_identity(recipe, outputs),
            'native_output_hashes': outputs, 'native_build_verified': True,
            'artifact_admitted': False, 'hardware_qualified': False}


def validate_record(record, root=ROOT):
    root = Path(root)
    validate_shape(record, 'record', root)
    candidate = read_json(retained_file(root, record['candidate']))
    validate_candidate(candidate, root, require_reviewed=True)
    recipe = read_json(retained_file(root, record['recipe']))
    validate_recipe(recipe, root)
    reuse = record['reuse']
    check(reuse['candidate_scope_sha256'] == scope_digest(candidate), 'native reuse candidate scope changed')
    check(reuse['recipe_sha256'] == recipe_digest(recipe), 'native reuse recipe changed')
    profiles = {p['id']: p for p in candidate['profiles']}
    check(reuse['profile'] in profiles, 'native producer profile is not selected')
    profile = read_json(retained_file(root, profiles[reuse['profile']]['observation']))
    check(profile['kind'] == 'windows-gpu' and profile['architecture'] == 'x86_64'
          and profile['python_abi'] == 'cp312', 'native producer is unadmitted/experimental for this profile')
    for kind in ('source', 'scope'):
        approval = read_json(retained_file(root, candidate['reviews'][kind]))
        links = approval.get('native_reuse_links')
        check(type(links) is list and digest(reuse) in links, 'native reuse lacks bound independent review')
    inputs = read_json(retained_file(root, candidate['runtime_inputs']))
    # Historical harness bytes are retained inputs, not today's mutable tests.
    originals = unique_by(record['source_inputs'], lambda item: item['path'], 'original native source')
    expected = {name: sha(retained_file(root, item['file']).read_bytes()) for name, item in originals.items()}
    production = production_inputs(inputs)
    check({name: value for name, value in expected.items() if not name.startswith('tests/')} == production,
          'candidate native production inputs differ from retained build')
    check(any(name.startswith('tests/') for name in expected), 'original native harness inputs missing')
    tools = {t['role']: t for t in recipe['toolchain']}
    check(tools['python']['sha256'] == profile['interpreter_sha256']
          and tools['base-python']['sha256'] == profile['base_interpreter']['sha256'], 'native Python profile changed')
    for tool in tools.values():
        check(sha(Path(tool['origin']).read_bytes()) == tool['sha256'], 'native toolchain bytes changed: ' + tool['role'])
    check(record['preparation']['sha256'] == recipe['preparation_sha256'], 'native build preparation changed')
    prepared = native_epoch.check_preparation(root, {
        'preparation_sha256': recipe['preparation_sha256'], 'ctest_sha256': tools['ctest']['sha256']},
        retained_file(root, record['preparation']))
    installed = prepared['installed_environment']
    for role, origin, checksum in (
            ('python', installed['executable'], installed['executable_sha256']),
            ('base-python', installed['base_executable'], installed['base_executable_sha256']),
            ('cmake', prepared['cmake']['origin'], prepared['cmake']['sha256'])):
        check(PureWindowsPath(tools[role]['origin']) == PureWindowsPath(origin)
              and tools[role]['sha256'] == checksum, 'native command tool differs from locked preparation: ' + role)
    check(prepared['interpreter_pin'] == profile['python_version'].split()[0], 'native prepared Python version differs from profile')
    sdk_record = read_json(retained_file(root, record['sdk']))
    validate_sdk(sdk_record, root)
    check(record['sdk']['sha256'] == recipe['sdk_record_sha256'], 'native SDK consumer recipe changed')
    consumer = read_json(retained_file(root, sdk_record['consumer']))
    check(PureWindowsPath(consumer['compiler']) == PureWindowsPath(tools['compiler']['origin']),
          'native compiler origin differs from SDK consumer')
    raw = read_json(retained_file(root, record['result']))
    validate_shape(raw, 'result', root)
    check(PureWindowsPath(raw['locations']['sdk']) == PureWindowsPath(str(retained_file(root, sdk_record['manifest']).parent)),
          'native build used another SDK origin')
    for command in raw['commands']:
        retained_file(root, command['log'])
    projects = unique_by(record['projects'], lambda p: p['target'], 'retained native project')
    projects = {name: (retained_file(root, p['before']), retained_file(root, p['after'])) for name, p in projects.items()}
    outputs = unique_by(record['outputs'], lambda p: p['member'], 'retained native output')
    outputs = {name: sha(retained_file(root, p['file']).read_bytes()) for name, p in outputs.items()}
    result = validate_proofs(recipe, raw, expected,
                           read_json(retained_file(root, record['source_before'])), read_json(retained_file(root, record['source_after'])),
                           retained_file(root, record['cache_before']).read_bytes(),
                           retained_file(root, record['cache_after']).read_bytes(),
                           consumer, projects, retained_file(root, record['ctest']).read_bytes(), outputs, root)
    check(result['production_sha256'] == reuse['production_sha256'], 'native reuse output/production identity changed')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate_record(read_json(args.record), args.root) if args.record else {
            'status': 'NATIVE_PROVENANCE_REQUIRED', 'required_targets': sorted(MIN_TARGETS),
            'required_phases': PHASES, 'native_leaf_admitted': False, 'artifact_admitted': False}
    except (InventoryError, native_epoch.EpochError, native_sdk.SDKError, OSError, ValueError,
            KeyError, TypeError, IndexError, ET.ParseError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
