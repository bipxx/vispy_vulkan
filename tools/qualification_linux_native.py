# SPDX-License-Identifier: AGPL-3.0-only
"""Read original managed Linux CI evidence without replaying or rewriting it."""
from __future__ import annotations

import io
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import zipfile

try:
    from .compatibility_candidate import scope_digest, validate_candidate
    from .compatibility_conservation import digest
    from .compatibility_inventory import ROOT, check, read_json, shape, unique_by
    from .qualification_artifact import retained_file, sha, elf_image, validate_policy
    from .qualification_native import production_inputs, parse_cache
    from .run_linux_native_contracts import validate_reports, renderer_cache
except ImportError:
    from compatibility_candidate import scope_digest, validate_candidate
    from compatibility_conservation import digest
    from compatibility_inventory import ROOT, check, read_json, shape, unique_by
    from qualification_artifact import retained_file, sha, elf_image, validate_policy
    from qualification_native import production_inputs, parse_cache
    from run_linux_native_contracts import validate_reports, renderer_cache

SCHEMA = 'compat/qualification-native.schema.json'
PROTOCOL = {
    'tools/linux_ci_lifecycle.py': 'c5cc6aac71160ca1d3f784cb6988a95c2ce6313ea25079163380f1b99875c53f',
    'tools/build_hygiene.py': '0a4f8cbc161afa39dfaf25e840bb0c788fda4f709b84f7440bd52102f847fa84',
    'tools/run_linux_native_contracts.py': 'e07e6aede2b8f35b0c75533606f59f0669783c1b9822c59534d62d6ffee5caca',
    'tools/audit_linux_wheel.py': '3106c09f756ed53ac14d0190355c49a79ddc114271b06bbccd530999300457df',
    '.github/workflows/qualification_gate.py': '26969e912f921cc57200f66d62a6b17194541006a11b9d5b0bda95c63ac51e92',
    '.github/workflows/linux-vulkan.yml': '9237e98216a69e9245a9bc9771492e3c07669c0127ad6f9529c17b8570dc7864',
}
WORKFLOW_PATH = '.github/workflows/linux-vulkan.yml'
# Keep the exact successful full-build collector authority. The current collector
# adds bounded reuse; original build records are never rewritten as reuse runs.
# Unknown collector revisions remain unsupported.
LEGACY_COLLECTOR_SHA256 = '3d5bc8eb9f5fdcc52a390d57a29fc26107b73679253545504587efe3648480cc'
LEGACY_WORKFLOW_SHA256 = 'd1af4af2d0171452ef5519e9bb5893e64b206fa35c6ad07a18e8aeaa67201860'
MEMBERS = {
    'vispy/_dawn.cpython-312-x86_64-linux-gnu.so': '_dawn.cpython-312-x86_64-linux-gnu.so',
    'vispy/visuals/text/_sdf_cpu.cpython-312-x86_64-linux-gnu.so': '_sdf_cpu.cpython-312-x86_64-linux-gnu.so',
    'vispy/VkLayer_vispy_submit.so': 'VkLayer_vispy_submit.so',
    'vispy/VkLayer_vispy_submit.json': 'generated/VkLayer_vispy_submit.json',
}
NATIVE_PHASES = ('native-environment', 'dependency-before', 'wheel-build',
                 'native-contracts', 'archive', 'dependency-after')
BUILD_PACKAGES = {'cmake': '4.4.4', 'cython': '3.1.5', 'nanobind': '3.1.0',
                  'scikit-build-core': '0.11.6'}


def original_script(workflow, phase, identity):
    marker = "run --phase "+phase+" --script-stdin <<'PHASE'\n"
    check(workflow.count(marker) == 1, 'original Linux setup script absent')
    text = workflow.split(marker, 1)[1].split('          PHASE\n', 1)[0]
    check(text and all(line.startswith('          ') for line in text.splitlines()),
          'unsupported original Linux setup indentation')
    text = ''.join(line[10:]+'\n' for line in text.splitlines())
    for key in ('run_id', 'run_attempt'):
        field = 'attempt' if key == 'run_attempt' else key
        text = text.replace('${{ github.'+key+' }}', str(identity[field]))
    return text.encode()


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            check(key not in result, 'duplicate original Linux JSON field: '+key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def absolute(name):
    path = PurePosixPath(name)
    check(path.is_absolute() and '..' not in path.parts and str(path) == name,
          'noncanonical original Linux path')
    return path


def ctest_launcher_bytes(python):
    """Expected console entry point, never a replacement original executable.

    uv's generated CMake entry point calls the locked package's ctest function.
    Its digest includes the owned interpreter path, so another launcher/interpreter
    cannot borrow the measured ELF backend's identity.
    """
    return (f'#!{python}\n'
            '# -*- coding: utf-8 -*-\n'
            'import sys\n'
            'from cmake import ctest\n'
            'if __name__ == "__main__":\n'
            '    if sys.argv[0].endswith("-script.pyw"):\n'
            '        sys.argv[0] = sys.argv[0][:-11]\n'
            '    elif sys.argv[0].endswith(".exe"):\n'
            '        sys.argv[0] = sys.argv[0][:-4]\n'
            '    sys.exit(ctest())\n').encode()


def validate_ctest_tool(contract, tools, settings, environment, scratch, aliases):
    """Join the measured Python launcher and packaged CTest ELF separately."""
    scratch = absolute(str(scratch))
    package_bin = scratch/'env/lib/python3.12/site-packages/cmake/data/bin'
    backend = str(package_bin/'ctest')
    check(settings['CMAKE_CTEST_COMMAND'] == backend
          and settings['CMAKE_COMMAND'] == str(package_bin/'cmake')
          and tools['CMAKE_CTEST_COMMAND']['origin'] == backend
          and tools['CMAKE_CTEST_COMMAND']['resolved'] == backend,
          'Linux configured CTest backend differs from locked package')
    check(re.fullmatch('[0-9a-f]{64}', tools['CMAKE_CTEST_COMMAND']['sha256']) is not None,
          'Linux CTest backend hash missing')
    packages = {key.lower().replace('_', '-'): value for key, value in environment['packages'].items()}
    check(packages.get('cmake') == BUILD_PACKAGES['cmake'], 'Linux CTest package differs')
    interpreter = str(scratch/'env/bin/python3')
    copies = [row for row in aliases['actions'] if row['link'] == interpreter]
    check(len(copies) == 1 and copies[0]['action'] == 'copy-interpreter'
          and copies[0]['sha256'] == environment['python_executable_sha256']
          == environment['base_python_executable_sha256']
          and absolute(copies[0]['target']).parent == absolute(environment['base_python_executable']).parent
          and absolute(copies[0]['target']).name in ('python', 'python3', 'python3.12'),
          'Linux CTest launcher interpreter differs from prepared copy')
    check(contract['ctest'] == dict(origin=str(scratch/'env/bin/ctest'),
                                   sha256=sha(ctest_launcher_bytes(interpreter))),
          'Linux CTest tool differs from recorded console launcher')
    check(tools['CMAKE_CTEST_COMMAND']['sha256'] != contract['ctest']['sha256'],
          'Linux CTest backend and console identities were conflated')


def capture_from_inventory(inventory, root=ROOT):
    """Build portable references to original bytes; this grants no admission.

    Inventory members are paths relative to the original CI artifact's build
    directory. Local extraction paths can come from either host platform.
    """
    root = Path(root)
    members = unique_by(inventory['members'], lambda row: row['member'], 'Linux transport member')
    states = [name for name in members
              if re.fullmatch(r'runs/native-ci-[0-9]+-[0-9]+/state\.json', name)]
    check(len(states) == 1, 'Linux transport needs exactly one native state')

    def reference(member):
        check(member in members, 'Linux transport member missing: '+member)
        row = members[member]
        ref = dict(path=row['path'].replace('\\', '/'), sha256=row['sha256'])
        retained_file(root, ref)
        return ref

    state_ref = reference(states[0])
    state = decode(retained_file(root, state_ref).read_bytes())
    workspace = absolute(state['workspace'])
    prefix = 'runs/'+state['run_id']+'/'
    check(prefix+'state.json' == states[0], 'Linux transport state/run differs')
    terminal_ref = reference(prefix+'terminal.json')
    terminal = decode(retained_file(root, terminal_ref).read_bytes())
    rows = unique_by(terminal['retained'], lambda row: row['path'], 'Linux terminal file')
    files = []
    for origin, row in rows.items():
        path = absolute(origin)
        check(path.is_relative_to(workspace/'build')
              and not path.is_relative_to(workspace/'build/work'),
              'Linux transport origin is scratch or outside retained build storage')
        ref = reference(path.relative_to(workspace/'build').as_posix())
        check(ref['sha256'] == row['sha256'], 'Linux transport differs from original retained bytes')
        files.append(dict(origin=origin, file=ref))
    return dict(schema=1, kind='original-linux-ci-capture-v1', state=state_ref,
                terminal=terminal_ref, plan=reference(prefix+'cleanup-plan.json'),
                cleanup=reference(prefix+'cleanup-result.json'), files=files)


def validate_capture(capture, expected_production, root=ROOT):
    """Original v1 protocol join. A positive result never admits an artifact."""
    root = Path(root)
    definitions = read_json(root/SCHEMA)['$defs']
    shape(capture, definitions['linux-capture'], definitions)
    cache = {}

    def data(ref):
        key = (ref['path'], ref['sha256'])
        if key not in cache:
            cache[key] = retained_file(root, ref).read_bytes()
        return cache[key]

    state = decode(data(capture['state']))
    check(type(state['schema']) is int and state['schema'] == 1
          and state['owner'] == 'ci' and state['admitted'] is False and state['active'] is None,
          'Linux producer is active or relabelled')
    workspace, source = absolute(state['workspace']), absolute(state['source'])
    run_id = state['run_id']
    check(run_id and '/' not in run_id and run_id not in ('.', '..'), 'invalid original Linux run ID')
    scratch = workspace/'build/work'/run_id
    evidence = workspace/'build/runs'/run_id
    check(state['scratch'] == str(scratch) and state['evidence'] == str(evidence)
          and not source.is_relative_to(workspace/'build/work'), 'Linux producer scope differs')
    files = unique_by(capture['files'], lambda row: row['origin'], 'original Linux retained origin')
    for origin, row in files.items():
        path = absolute(origin)
        check(path.is_relative_to(workspace) and not path.is_relative_to(workspace/'build/work'),
              'Linux evidence origin is scratch or outside its workspace')
        data(row['file'])

    def original(name):
        name = str(name)
        check(name in files, 'original Linux evidence missing: '+name)
        return data(files[name]['file'])

    def document(name):
        return decode(original(name))

    check(files[str(evidence/'state.json')]['file'] == capture['state'], 'Linux state transport differs')
    before = document(evidence/'source-before.json')
    after = document(evidence/'source-after.json')
    check(before == after and state.get('source_changed', False) is False, 'Linux producer source changed')
    check(expected_production and all(before.get(name) == checksum for name, checksum in expected_production.items()),
          'candidate production differs from original Linux source')
    source_bytes = original(evidence/'source-inputs.zip')
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)) and set(names) == set(before), 'Linux source archive inventory differs')
        for name in names:
            path = PurePosixPath(name)
            check(not path.is_absolute() and '..' not in path.parts and path.as_posix() == name,
                  'noncanonical Linux source member')
            check(sha(archive.read(name)) == before[name], 'Linux preferred source bytes differ: '+name)
        for name, checksum in PROTOCOL.items():
            accepted = {checksum}
            if name == WORKFLOW_PATH: accepted.add(LEGACY_WORKFLOW_SHA256)
            if name == 'tools/linux_ci_lifecycle.py': accepted.add(LEGACY_COLLECTOR_SHA256)
            check(before.get(name) in accepted, 'unsupported original Linux capture protocol: '+name)
        policy_bytes = archive.read('compat/build-hygiene.json')
        workflow = archive.read('.github/workflows/linux-vulkan.yml').decode()
    check(state['policy_sha256'] == sha(policy_bytes), 'original Linux policy changed')
    policy = decode(policy_bytes)
    preflight = document(evidence/'preflight.json')
    check(policy['managed_root'] == 'build/work' and policy['min_free_bytes'] >= 10*1024**3
          and policy['max_scratch_bytes'] <= 20*1024**3, 'unsupported original Linux capacity profile')
    check(preflight['status'] == 'PASS_PREFLIGHT' and preflight['registered'] is True
          and preflight['owner'] == state['owner'] and preflight['scratch_root'] == str(scratch)
          and preflight['max_scratch_bytes'] == policy['max_scratch_bytes']
          and preflight['min_free_bytes'] == policy['min_free_bytes']
          and preflight['free_bytes'] >= preflight['expected_peak_bytes']+policy['min_free_bytes'],
          'Linux original capacity preflight differs')

    # Validate the actual in-process Context.apply result. Do not invent a CLI
    # command, child PID or exit for a Python method that returned synchronously.
    terminal = decode(data(capture['terminal']))
    plan = decode(data(capture['plan']))
    cleaned = decode(data(capture['cleanup']))
    check(plan['kind'] == 'build-hygiene-cleanup-plan' and type(plan['schema']) is type(terminal['schema']) is int
          and plan['schema'] == terminal['schema'] == 1,
          'wrong original Linux cleanup protocol')
    check(plan['workspace'] == str(workspace) and plan['scratch_root'] == str(scratch)
          and terminal['scratch_root'] == str(scratch), 'Linux cleanup scope differs')
    check(plan['manifest'] == str(evidence/'terminal.json')
          and plan['manifest_sha256'] == capture['terminal']['sha256'], 'Linux cleanup used another terminal')
    check(plan['policy_sha256'] == sha(policy_bytes)
          and original(evidence/'hygiene-policy.json') == policy_bytes, 'Linux cleanup policy differs')
    check(plan['registry'] is None and plan['registry_sha256'] is None
          and state['registry_required'] is False, 'unsupported original Linux registry protocol')
    check((plan['run_id'], plan['owner']) == (run_id, state['owner'])
          == (terminal['run_id'], terminal['owner']), 'Linux cleanup ownership differs')
    check(terminal['state'] in ('succeeded', 'failed', 'cancelled')
          and type(terminal['process_exit']) is int and terminal['child_waited'] is True,
          'Linux terminal exit/wait missing')
    check(terminal['state'] != 'succeeded' or terminal['process_exit'] == 0, 'Linux success has a failed exit')
    check(terminal['process_exit'] == state['exit_code'], 'Linux state/terminal exits differ')
    retained = unique_by(terminal['retained'], lambda row: row['path'], 'Linux terminal file')
    planned = unique_by(plan['retained'], lambda row: row['path'], 'Linux planned file')
    check(set(retained) == set(planned) == set(files), 'Linux transport/retention inventory differs')
    roles = set()
    for origin, row in retained.items():
        check(row['sha256'] == files[origin]['file']['sha256'] == planned[origin]['sha256']
              and row['roles'] == planned[origin]['roles'], 'Linux retained bytes or roles differ')
        roles.update(row['roles'])
    check({'source', 'evidence', 'licenses'} | ({'repro'} if terminal['state'] != 'succeeded' else set()) <= roles,
          'Linux original source/license/reproducer missing')
    for row in plan['snapshot']['files'] + plan['snapshot']['directories']:
        name = row['path']; path = PurePosixPath(name)
        check(not path.is_absolute() and '..' not in path.parts and path.as_posix() == name
              and '.git' not in (part.lower() for part in path.parts),
              'Linux cleanup snapshot leaves its scratch')
    check(cleaned['status'] == 'PASS_APPLY' and cleaned['scratch_root'] == str(scratch)
          and type(cleaned['deleted']) is int and cleaned['deleted'] == len(plan['snapshot']['files'])
          and cleaned['retained_verified'] == len(retained), 'Linux cleanup incomplete')
    check(all(type(row['bytes']) is int and row['bytes'] >= 0 for row in plan['snapshot']['files'])
          and sum(row['bytes'] for row in plan['snapshot']['files']) <= policy['max_scratch_bytes'],
          'Linux original scratch exceeded its budget')
    check(not (root/'build/work'/run_id).exists(), 'Linux imported scratch is still present')

    receipts = {}
    for ref in state['commands']:
        raw = original(ref['path'])
        check(sha(raw) == ref['sha256'], 'Linux original command receipt changed')
        receipt = decode(raw)
        name = PurePosixPath(ref['path']).name
        check(name.endswith('-process.json') and PurePosixPath(ref['path']).parent == evidence,
              'Linux command receipt origin differs')
        phase = name[:-len('-process.json')]
        check(phase not in receipts, 'duplicate Linux phase')
        check(receipt['cwd'] == str(source) and type(receipt['child_pid']) is int and receipt['child_pid'] > 0
              and receipt['child_waited'] is True and type(receipt['actual_exit']) is int,
              'Linux child not terminal/awaited')
        check(receipt['log_sha256'] == sha(original(evidence/(phase+'.log'))), 'Linux command log differs')
        receipts[phase] = receipt
    check(tuple(phase for phase in receipts if phase in NATIVE_PHASES) == NATIVE_PHASES,
          'Linux native phases missing, duplicated or reordered')
    for phase in NATIVE_PHASES:
        check(receipts[phase]['actual_exit'] == 0 and not receipts[phase].get('observer_error'),
              'Linux native phase failed: '+phase)
        for variable in ('CMAKE_TOOLCHAIN_FILE', 'CMAKE_ARGS', 'SKBUILD_CMAKE_ARGS', 'PYTHONHOME', 'PYTHONPATH'):
            check(receipts[phase]['environment'].get(variable) in (None, ''), 'unmodelled Linux build override: '+variable)

    python = str(scratch/'env/bin/python')
    build = str(scratch/'native')
    environment = document(evidence/'native-environment.json')
    check(environment['python_executable'] == python and environment['machine'] == 'x86_64'
          and environment['python'].split()[0].startswith('3.12.'), 'Linux build interpreter/architecture differs')
    check(all(type(environment[key]) is str and re.fullmatch('[0-9a-f]{64}', environment[key])
              for key in ('python_executable_sha256', 'base_python_executable_sha256')),
          'Linux interpreter hashes missing')
    packages = {key.lower().replace('_', '-'): value for key, value in environment['packages'].items()}
    check(all(packages.get(key) == value for key, value in BUILD_PACKAGES.items()) and packages.get('numpy'),
          'Linux original locked build packages differ')
    for name, filename in [('uv.lock', 'uv.lock'), ('pyproject.toml', 'pyproject.toml'),
                           ('cmake/dependencies.lock.json', 'cmake/dependencies.lock.json')]:
        check(environment['input_sha256'][filename] == before[name], 'Linux locked preparation differs')
    archive = document(evidence/'archive.json')
    revision = original(evidence/'source-revision.txt').decode().strip()
    identity = document(evidence/'ci-identity.json')
    check(re.fullmatch('[0-9a-f]{40}', revision)
          and identity['repository'] == 'bipxx/vispy_vulkan'
          and identity['checked_head'] == revision == archive['source_revision']
          == environment['commands']['git']['stdout'].strip()
          and identity['workflow'] == dict(path='.github/workflows/linux-vulkan.yml',
                                          sha256=before[WORKFLOW_PATH]),
          'Linux original checkout/CI/workflow identity differs')
    check(type(identity['run_id']) is int and type(identity['attempt']) is int
          and state['run_id'] == 'native-ci-'+str(identity['run_id'])+'-'+str(identity['attempt']),
          'Linux capture belongs to another CI attempt')
    for phase in ('prepare', 'driver'):
        check(phase in receipts and receipts[phase]['actual_exit'] == 0
              and receipts[phase]['argv'] == ['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail',
                                              str(evidence/(phase+'.sh'))]
              and original(evidence/(phase+'.sh')) == original_script(workflow, phase, identity),
              'Linux locked setup differs from original workflow: '+phase)
    check(archive['status'] == 'PASS_LINUX_RENDERER_WHEEL_ARCHIVE'
          and archive['hardware_qualified'] is False and archive['manylinux_qualified'] is False,
          'Linux archive scope relabelled')
    wheel = archive['wheel']
    check(absolute(wheel).parent == evidence/'wheels' and sha(original(wheel)) == archive['wheel_sha256'],
          'Linux wheel bytes/origin differ')
    expected_commands = {
        'native-environment': [python, '.github/workflows/qualification_gate.py', 'capture', '--without-package',
                               '--output', str(evidence/'native-environment.json')],
        'dependency-before': [python, 'cmake/verify_dependencies.py'],
        'dependency-after': [python, 'cmake/verify_dependencies.py'],
        'wheel-build': ['uv', 'build', '--python', python, '--no-build-isolation', '--wheel', '--out-dir', str(evidence/'wheels'),
                        '--config-setting', 'build-dir='+build, '--config-setting', 'cmake.define.VISPY_INPLACE=OFF',
                        '--config-setting', 'cmake.define.VISPY_CPU_CONTRACTS_ONLY=OFF', '--config-setting',
                        'cmake.define.VISPY_BUILD_CONTRACT_TESTS=ON', '--config-setting', 'cmake.define.VISPY_VERIFY_DEPENDENCIES=ON',
                        '--config-setting', 'cmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=ON'],
        'native-contracts': [python, '-B', 'tools/run_linux_native_contracts.py', '--build-dir', build,
                             '--ctest', str(scratch/'env/bin/ctest'), '--output', str(evidence/'native-contracts')],
        'archive': [python, '-B', 'tools/audit_linux_wheel.py', '--wheel', wheel, '--build-dir', build,
                    '--contracts', str(evidence/'native-contracts'), '--output', str(evidence/'archive.json')],
    }
    check(all(receipts[name]['argv'] == argv for name, argv in expected_commands.items()),
          'Linux original build command differs from supported protocol')
    first = document(evidence/'wheel-build-build-inputs-outputs.json')
    last = document(evidence/'archive-build-inputs-outputs.json')

    def artifact(ref):
        raw = original(ref['path'])
        check(sha(raw) == ref['sha256'], 'Linux generated configuration/output changed')
        return raw

    for name in ('CMakeCache.txt', 'build.ninja', 'compile_commands.json', 'CMakeFiles/rules.ninja', 'CTestTestfile.cmake'):
        check(artifact(first[name]) == artifact(last[name]), 'Linux build graph changed: '+name)
    cache_bytes = artifact(last['CMakeCache.txt'])
    renderer_cache(cache_bytes)
    settings = parse_cache(cache_bytes.decode())
    check(settings['CMAKE_HOME_DIRECTORY'] == str(source) and settings['CMAKE_CACHEFILE_DIR'] == build
          and settings['CMAKE_BUILD_TYPE'] == 'Release' and settings['VISPY_NATIVE_SDK'] == '',
          'Linux build used another source/configuration/SDK')
    check(settings.get('Python_EXECUTABLE', settings.get('_Python_EXECUTABLE')) == python,
          'Linux configured another Python interpreter')
    units = decode(artifact(last['compile_commands.json']))
    check(units and any('_dawn.dir/' in (u.get('output', '') or u.get('command', '')) for u in units),
          'Linux shipping module has no recorded compilation')
    for unit in units:
        check(absolute(unit['directory']).is_relative_to(scratch/'native')
              and any(absolute(unit['file']).is_relative_to(base) for base in (source, scratch/'native', scratch/'env')),
              'Linux compilation leaves original source/build')
        check(unit.get('arguments') or shlex.split(unit['command']), 'empty Linux compiler command')
    tools = document(evidence/'wheel-build-toolchain.json')
    check(tools == document(evidence/'archive-toolchain.json'), 'Linux observed toolchain changed')
    check({'CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER', 'CMAKE_COMMAND', 'CMAKE_CTEST_COMMAND', 'CMAKE_MAKE_PROGRAM', 'build-python',
           'python-environment'} <= set(tools), 'Linux toolchain observation incomplete')
    check(tools['build-python']['origin'] == python
          and tools['build-python']['sha256'] == environment['python_executable_sha256'], 'Linux Python bytes differ')
    for role in ('CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER', 'CMAKE_COMMAND', 'CMAKE_CTEST_COMMAND', 'CMAKE_MAKE_PROGRAM'):
        check(tools[role]['origin'] == settings[role], 'Linux configured tool differs: '+role)
        absolute(tools[role]['origin']); absolute(tools[role]['resolved'])
        check(re.fullmatch('[0-9a-f]{64}', tools[role]['sha256']), 'Linux tool hash missing')

    contract = document(evidence/'native-contracts/result.json')
    check(contract['status'] == 'PASS_LINUX_RENDERER_CONTRACTS' and contract['build'] == build
          and contract['cache_sha256'] == sha(cache_bytes), 'Linux contracts use another build')
    check(all(contract[name] is False for name in ('producer_admitted', 'artifact_admitted', 'hardware_qualified')),
          'Linux contract scope relabelled')
    names = validate_reports(original(evidence/'native-contracts/discovery.json'), original(evidence/'native-contracts/ctest.xml'))
    check(contract['tests'] == names and archive['native_contracts']['tests'] == names,
          'Linux contract inventories differ')
    check(archive['native_contracts']['sha256'] == sha(original(evidence/'native-contracts/result.json')),
          'Linux archive uses another contract report')
    check(set(contract['files']) == {'discovery.json', 'discovery.log', 'ctest.xml', 'ctest.log'},
          'Linux contract evidence inventory differs')
    for name, checksum in contract['files'].items():
        check(sha(original(evidence/'native-contracts'/name)) == checksum, 'Linux contract evidence changed')
    check(len(contract['commands']) == 2 and all(type(c['exit_code']) is int and c['exit_code'] == 0 and c['child_waited'] is True
          and type(c['child_pid']) is int and c['child_pid'] > 0 for c in contract['commands']),
          'Linux CTest child failed/unawaited')
    ctest = str(scratch/'env/bin/ctest')
    validate_ctest_tool(contract, tools, settings, environment, scratch,
                        document(evidence/'prepare-environment-aliases.json'))
    check(contract['ctest']['origin'] == ctest and contract['commands'][0]['argv'] ==
          [ctest, '--test-dir', build, '--show-only=json-v1'] and contract['commands'][1]['argv'] ==
          [ctest, '--test-dir', build, '--output-on-failure', '--no-tests=error', '--output-junit',
           str(evidence/'native-contracts/ctest.xml')], 'Linux CTest command was filtered or redirected')

    check(set(archive['native_origin']) == set(MEMBERS), 'Linux shipping output inventory differs')
    outputs = {}
    for member, name in MEMBERS.items():
        raw = artifact(last[name])
        check(raw == artifact(first[name]), 'Linux raw shipping output changed')
        shipping = original(evidence/'native-origin'/member)
        with zipfile.ZipFile(io.BytesIO(original(wheel))) as archive_file:
            check(archive_file.read(member) == shipping, 'Linux wheel bytes differ from controlled strip output')
        check(sha(raw) == archive['native_origin'][member]['raw_sha256']
              and sha(shipping) == archive['native_origin'][member]['wheel_stripped_sha256'],
              'Linux raw/strip/wheel output join differs')
        if not member.endswith('.json'):
            for blob in (raw, shipping):
                image = elf_image(blob)
                check(image['pointer_bytes'] == 8 and image['machine'] == 62, 'Linux output is not ELF x86-64')
        else: check(raw == shipping, 'Linux layer descriptor changed while stripping')
        outputs[member] = sha(shipping)
    production = digest(dict(schema=1, platform='linux-x86_64-cp312', inputs=expected_production,
                             toolchain=tools, outputs=outputs,
                             preparation={k: environment[k] for k in ('python', 'base_python_executable_sha256')},
                             packages={key: packages[key] for key in (*BUILD_PACKAGES, 'numpy')},
                             configuration={k: v for k, v in settings.items() if k.startswith(('DAWN_', 'TINT_', 'CMAKE_C_FLAGS', 'CMAKE_CXX_FLAGS'))}))
    return dict(status='PASS_ORIGINAL_LINUX_NATIVE_JOIN', production_sha256=production,
                native_output_hashes=outputs, native_build_verified=True,
                artifact_admitted=False, hardware_qualified=False), environment


def validate_record(record, root=ROOT):
    root = Path(root)
    definitions = read_json(root/SCHEMA)['$defs']
    shape(record, definitions['linux-record'], definitions)
    policy = validate_policy(root)
    check(policy['linux_scope'] == 'reviewed-full-source-native-proof-required', 'Linux producer policy is still blocked')
    candidate = read_json(retained_file(root, record['candidate']))
    validate_candidate(candidate, root, require_reviewed=True)
    reuse = record['reuse']
    check(reuse['candidate_scope_sha256'] == scope_digest(candidate)
          and reuse['capture_sha256'] == record['capture']['sha256'], 'Linux reuse scope/capture changed')
    profiles = {p['id']: p for p in candidate['profiles']}
    check(reuse['profile'] in profiles, 'Linux reuse profile is not selected')
    profile = read_json(retained_file(root, profiles[reuse['profile']]['observation']))
    check((profile['kind'], profile['architecture'], profile['python_abi']) == ('wsl-software', 'x86_64', 'cp312'),
          'Linux producer cannot admit another platform/ABI')
    for kind in ('source', 'scope'):
        approval = read_json(retained_file(root, candidate['reviews'][kind]))
        check(type(approval.get('native_reuse_links')) is list and digest(reuse) in approval['native_reuse_links'],
              'Linux reuse lacks exact independent review')
    inputs = read_json(retained_file(root, candidate['runtime_inputs']))
    result, environment = validate_capture(read_json(retained_file(root, record['capture'])), production_inputs(inputs), root)
    expected_abi = dict(tag='cp312', build_version=environment['python'].split()[0],
                        build_python_sha256=environment['python_executable_sha256'],
                        consumer_version=profile['python_version'].split()[0],
                        consumer_python_sha256=profile['interpreter_sha256'])
    check(reuse['abi'] == expected_abi and expected_abi['consumer_version'].startswith('3.12.'),
          'Linux build/consumer ABI facts differ from reviewed reuse')
    check(reuse['production_sha256'] == result['production_sha256'], 'Linux production identity changed')
    return result
