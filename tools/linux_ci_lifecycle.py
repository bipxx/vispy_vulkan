# SPDX-License-Identifier: AGPL-3.0-only
"""Managed Linux wheel CI lifecycle; captured evidence is not admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from types import SimpleNamespace
import zipfile

try:
    from .build_hygiene import Context, MARKER, digest, no_alias, overlaps
    from .native_epoch import project_inventory
except ImportError:
    from build_hygiene import Context, MARKER, digest, no_alias, overlaps
    from native_epoch import project_inventory

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'compat/build-hygiene.json'


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def source_inventory(source):
    result = project_inventory(source)
    inputs = [source/name for name in (
        'README.md', 'compat/runtime-package.json', 'compat/build-hygiene.json',
        'compat/software-vulkan-build.json', 'compat/software-vulkan-driver-clip-repair.json',
        'compat/mesa-build-requirements.txt', 'compat/qualification-ci.json',
        'compat/qualification-ci.schema.json')]
    inputs += list((source/'compat/patches').glob('mesa-*'))
    for path in inputs:
        if path.is_file():
            no_alias(path)
            result[path.relative_to(source).as_posix()] = digest(path)
    for base in ('tools', '.github/workflows', 'tests'):
        for path in (source / base).rglob('*'):
            if path.is_file() and (path.suffix in ('.py', '.cpp', '.hpp', '.h', '.yml')
                                  or 'corpus' in path.parts):
                if not any(p in ('__pycache__', '.git', 'build') for p in path.relative_to(source).parts):
                    no_alias(path)
                    result[path.relative_to(source).as_posix()] = digest(path)
    return result


def initialize(source, workspace, run_id, owner, peak, github_env=None):
    source = no_alias(Path(source).absolute())
    workspace = no_alias(Path(workspace).absolute())
    workspace.mkdir(parents=True, exist_ok=True)
    context = Context(workspace, POLICY, None)
    evidence = workspace/'build/runs'/run_id
    if evidence.exists() or context.scratch(run_id).exists():
        raise ValueError('Lifecycle run already exists; do not adopt or overwrite it')
    if source.is_relative_to(context.work):
        raise ValueError('Build from retained source outside managed scratch')
    result = context.preflight(SimpleNamespace(run_id=run_id, owner=owner,
                                               expected_peak_bytes=peak, register=True))
    scratch = Path(result['scratch_root'])
    if source.is_relative_to(scratch):
        raise ValueError('Build from retained source outside managed scratch')
    evidence.mkdir(parents=True, exist_ok=False)
    state_path = evidence/'state.json'
    state = dict(schema=1, source=str(source), workspace=str(workspace), run_id=run_id,
                 owner=owner, scratch=str(scratch), evidence=str(evidence),
                 policy_sha256=digest(POLICY), registry_required=context.registry_path is not None,
                 commands=[], exit_code=None, active=None, admitted=False)
    write(state_path, state)
    write(evidence/'preflight.json', result)
    try:
        inventory = source_inventory(source)
        write(evidence/'source-before.json', inventory)
        with zipfile.ZipFile(evidence/'source-inputs.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(inventory):
                archive.write(source/name, name)
        if context.registry_path:
            shutil.copyfile(context.registry_path, evidence/'registry-input.json')
        shutil.copyfile(POLICY, evidence/'hygiene-policy.json')
        environment = dict(CI_STATE=str(state_path), EVIDENCE=str(evidence),
                           DRIVER_WORKSPACE=str(workspace),
                           NATIVE_BUILD=str(scratch/'native'), BUILD_ENV=str(scratch/'env'),
                           BUILD_PYTHON=str(scratch/'env/bin/python'),
                           CONSUMER_PATH=str(scratch/'consumer'),
                           UV_CACHE_DIR=str(workspace/'build/cache'/run_id), UV_LINK_MODE='copy',
                           XDG_CACHE_HOME=str(scratch/'cache'), TMPDIR=str(scratch/'tmp'))
        (scratch/'tmp').mkdir()
        write(evidence/'environment-paths.json', environment)
        if github_env:
            with Path(github_env).open('a') as stream:
                for key, value in environment.items():
                    stream.write(key + '=' + value + '\n')
    except BaseException:
        state['exit_code'] = 1  # This CLI's explicit initialization failure exit.
        write(state_path, state)
        raise
    return state_path


def load(state_path):
    state = json.loads(Path(state_path).read_bytes())
    context = Context(state['workspace'], POLICY, None)
    expected = Path(state['workspace'])/'build/runs'/state['run_id']/'state.json'
    if Path(state_path).absolute() != expected or state['evidence'] != str(expected.parent):
        raise ValueError('Lifecycle state belongs to another run')
    if digest(POLICY) != state['policy_sha256']:
        raise ValueError('Lifecycle policy changed after registration')
    if state['registry_required'] and context.registry_path is None:
        raise ValueError('Original protected/blocked registry is missing')
    scratch = context.scratch(state['run_id'])
    context.marker(scratch, state['run_id'], state['owner'])
    if str(scratch) != state['scratch'] or state['admitted'] is not False:
        raise ValueError('Lifecycle identity changed')
    return state, context


def check_space(context):
    context.check_capacity(0, 0)
    # A running producer may temporarily own aliases. Count them without following
    # them; the original strict snapshot still controls every cleanup operation.
    total = 0
    for folder, directories, files in os.walk(context.work, followlinks=False):
        for name in files:
            info = (Path(folder)/name).lstat()
            total += info.st_size
    if total > context.limit:
        raise ValueError('Managed scratch exceeded its shared budget')


def checked_link(context, link):
    for protected in context.protected + context.blocked:
        if overlaps(link, protected):
            raise ValueError('Producer alias overlaps protected/blocked path: ' + str(link))


def normalize_environments(state, context, label):
    """Materialize uv interpreter aliases; remove only its redundant lib64 alias."""
    actions = []
    scratch = Path(state['scratch'])
    for name in ('env', 'consumer'):
        environment = scratch/name
        if environment.exists(): no_alias(environment)
        if (environment/'bin').exists(): no_alias(environment/'bin')
        config = environment/'pyvenv.cfg'
        values = {}
        if config.exists():
            values = dict(line.split(' = ', 1) for line in config.read_text().splitlines()
                          if ' = ' in line)
        candidates = [environment/'lib64'] + [environment/'bin'/n for n in ('python', 'python3', 'python3.12')]
        for link in candidates:
            if not link.is_symlink():
                continue
            checked_link(context, link)
            raw = os.readlink(link)
            target = link.resolve(strict=True)
            if link.name == 'lib64':
                if target != environment/'lib':
                    raise ValueError('Unexpected uv lib64 target')
                actions.append(dict(link=str(link), raw=raw, target=str(target), action='unlink-redundant-lib64'))
            else:
                home = Path(values['home']).resolve(strict=True)
                if target.parent not in (home, environment/'bin') or not target.is_file():
                    raise ValueError('Unexpected uv interpreter alias')
                actions.append(dict(link=str(link), raw=raw, target=str(target), action='copy-interpreter', sha256=digest(target)))
    # Audit the entire finite plan before changing any alias. Never touch targets.
    output = Path(state['evidence'])/(label+'-environment-aliases.json')
    write(output, dict(actions=actions, registry_sha256=digest(context.registry_path) if context.registry_path else None))
    for item in actions:
        link, target = Path(item['link']), Path(item['target'])
        if not link.is_symlink() or os.readlink(link) != item['raw']:
            raise ValueError('Producer alias changed after audit')
        if item['action'] == 'copy-interpreter':
            data = target.read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('Interpreter changed after audit')
            mode = stat.S_IMODE(target.stat().st_mode)
            link.unlink()
            with link.open('xb') as stream:
                stream.write(data)
            link.chmod(mode)
        else:
            link.unlink()


def retain_build(state, phase):
    build = Path(state['scratch'])/'native'
    store = Path(state['workspace'])/'build/artifacts'
    files = [build/n for n in ('CMakeCache.txt', 'build.ninja', 'compile_commands.json',
                              'CTestTestfile.cmake', 'cmake_install.cmake', 'install_manifest.txt',
                              'CMakeFiles/rules.ninja')]
    for name in ('CMakeCCompiler.cmake', 'CMakeCXXCompiler.cmake', 'CMakeSystem.cmake'):
        files += list((build/'CMakeFiles').glob('*/'+name))
    files += list(build.glob('_dawn*.so')) + list(build.glob('_sdf_cpu*.so'))
    files += [build/'VkLayer_vispy_submit.so', build/'generated/VkLayer_vispy_submit.json']
    retained = {}
    for path in files:
        if not path.is_file():
            continue
        checksum = digest(path)
        target = store/checksum/path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target) != checksum:
                raise ValueError('Retained build artifact changed')
        else:
            shutil.copyfile(path, target)
        retained[path.relative_to(build).as_posix()] = dict(path=str(target), sha256=checksum)
    write(Path(state['evidence'])/(phase+'-build-inputs-outputs.json'), retained)
    cache = build/'CMakeCache.txt'
    if cache.is_file():
        values = {}
        for line in cache.read_text().splitlines():
            if not line.startswith(('#', '//')) and ':' in line and '=' in line:
                key, value = line.split('=', 1)
                values[key.split(':', 1)[0]] = value
        tools = {key: values[key] for key in ('CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER',
                 'CMAKE_COMMAND', 'CMAKE_CTEST_COMMAND', 'CMAKE_MAKE_PROGRAM') if key in values}
        tools['build-python'] = str(Path(state['scratch'])/'env/bin/python')
        observed = {}
        for role, origin in tools.items():
            path = Path(origin)
            if path.is_file():
                observed[role] = dict(origin=origin, resolved=str(path.resolve()), sha256=digest(path))
        config = Path(state['scratch'])/'env/pyvenv.cfg'
        if config.is_file(): observed['python-environment'] = dict(content=config.read_text(), sha256=digest(config))
        write(Path(state['evidence'])/(phase+'-toolchain.json'), observed)


def run_command(state_path, phase, argv, interval=30):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,70}', phase):
        raise ValueError('Invalid phase name')
    state, context = load(state_path)
    if state['active'] is not None:
        raise ValueError('Previous child has no terminal wait record')
    evidence = Path(state['evidence'])
    receipt_path = evidence/(phase+'-process.json')
    if receipt_path.exists():
        raise ValueError('Phase already executed; preserve its original receipt')
    log_path = evidence/(phase+'.log')
    started = time.monotonic()
    code = None
    error = None
    with log_path.open('xb') as log:
        child = subprocess.Popen(argv, cwd=state['source'], stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=os.name != 'nt')
        try:
            state['active'] = dict(pid=child.pid, phase=phase, argv=argv)
            write(state_path, state)
            while True:
                try:
                    code = child.wait(timeout=interval)
                    break
                except subprocess.TimeoutExpired:
                    check_space(context)
                    print(phase, 'running', round(time.monotonic()-started), 'seconds', flush=True)
        except BaseException as exception:
            error = repr(exception)
            if child.poll() is None:
                try:
                    if os.name != 'nt': os.killpg(child.pid, signal.SIGTERM)
                    else: child.terminate()
                except ProcessLookupError:
                    pass
            try: code = child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name != 'nt': os.killpg(child.pid, signal.SIGKILL)
                else: child.kill()
                code = child.wait()
        finally:
            receipt = dict(argv=argv, cwd=state['source'], child_pid=child.pid,
                           actual_exit=code, child_waited=code is not None,
                           elapsed_seconds=time.monotonic()-started, log_sha256=digest(log_path))
            receipt['environment'] = {key: os.environ.get(key) for key in (
                'CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'PYTHONHOME',
                'PYTHONPATH', 'CMAKE_GENERATOR', 'CMAKE_BUILD_PARALLEL_LEVEL',
                'CMAKE_TOOLCHAIN_FILE', 'CMAKE_ARGS', 'SKBUILD_CMAKE_ARGS',
                'UV_LINK_MODE', 'UV_CACHE_DIR', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES')}
            if error: receipt['observer_error'] = error
            write(receipt_path, receipt)
            state['commands'].append(dict(path=str(receipt_path), sha256=digest(receipt_path)))
            state['active'] = None if code is not None else state['active']
            if state['exit_code'] in (None, 0): state['exit_code'] = code if code else 1 if error else 0
            write(state_path, state)
    normalize_environments(state, context, phase)
    if phase in ('wheel-build', 'native-contracts', 'archive'):
        retain_build(state, phase)
    if code or error:
        raise RuntimeError('Phase failed; original exit and logs retained: ' + phase)
    return receipt


def finish(state_path):
    state, context = load(state_path)
    if state['active'] is not None or state['exit_code'] is None:
        raise ValueError('No complete awaited process result; cleanup refused')
    evidence = Path(state['evidence'])
    # uv owns this one per-run cache; its documented clean command handles cache
    # aliases without changing the generic managed cleanup verifier.
    cache = Path(state['workspace'])/'build/cache'/state['run_id']
    if cache.exists():
        context.clean_target(cache)
        run_command(state_path, 'cache-clean', ['uv', 'cache', 'clean', '--cache-dir', str(cache)])
        state, context = load(state_path)
    normalize_environments(state, context, 'terminal')
    retain_build(state, 'terminal')
    before = json.loads((evidence/'source-before.json').read_bytes())
    after = source_inventory(Path(state['source']))
    write(evidence/'source-after.json', after)
    source_changed = before != after
    if source_changed:
        with zipfile.ZipFile(evidence/'changed-source.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
            for name, checksum in after.items():
                if before.get(name) != checksum: archive.write(Path(state['source'])/name, name)
        state['exit_code'] = state['exit_code'] or 1
        state['source_changed'] = True
        write(state_path, state)
    # CMake may create shared-library aliases. Audit only aliases inside this
    # owned build, with targets inside the same build. Never traverse them.
    build = Path(state['scratch'])/'native'
    links = []
    for folder, directories, files in os.walk(build, followlinks=False):
        for name in directories + files:
            link = Path(folder)/name
            if link.is_symlink():
                checked_link(context, link)
                target = link.resolve(strict=True)
                if not target.is_relative_to(build):
                    raise ValueError('Native build alias leaves its owned build')
                links.append(dict(link=str(link), raw=os.readlink(link), target=str(target)))
    write(evidence/'native-alias-cleanup.json', dict(links=links))
    for item in links:
        link = Path(item['link'])
        if not link.is_symlink() or os.readlink(link) != item['raw']: raise ValueError('Native alias changed')
        link.unlink()
    retained = []
    for path in sorted(evidence.rglob('*')):
        if path.is_file():
            roles = ['evidence', 'repro']
            if path.name in ('source-inputs.zip', 'changed-source.zip'): roles += ['source', 'licenses']
            elif path.suffix == '.sh': roles += ['source']
            retained.append(dict(path=str(path), sha256=digest(path), roles=roles))
    for report in evidence.glob('*-build-inputs-outputs.json'):
        for item in json.loads(report.read_bytes()).values():
            retained.append(dict(**item, roles=['evidence', 'repro']))
    retained = list({item['path']: item for item in retained}.values())
    manifest = evidence/'terminal.json'
    write(manifest, dict(schema=1, run_id=state['run_id'], owner=state['owner'],
                         state='succeeded' if state['exit_code'] == 0 else 'failed',
                         process_exit=state['exit_code'], child_waited=True,
                         scratch_root=state['scratch'], retained=retained))
    plan_path = evidence/'cleanup-plan.json'
    with plan_path.open('x') as stream:
        json.dump(context.make_plan(manifest), stream, indent=2)
    result = context.apply(SimpleNamespace(plan=str(plan_path)))
    write(evidence/'cleanup-result.json', result)
    if source_changed:
        raise RuntimeError('Source changed; failed run retained and cleaned')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--workspace', type=Path, required=True)
    init.add_argument('--run-id', required=True)
    init.add_argument('--owner', default='ci')
    init.add_argument('--expected-peak-bytes', type=int, required=True)
    run = sub.add_parser('run')
    run.add_argument('--phase', required=True)
    run.add_argument('--script-stdin', action='store_true')
    run.add_argument('argv', nargs=argparse.REMAINDER)
    sub.add_parser('finish')
    args = parser.parse_args()
    if sys.platform != 'linux': parser.error('CI lifecycle execution requires Linux')
    try:
        if args.command == 'init':
            initialize(ROOT, args.workspace, args.run_id, args.owner, args.expected_peak_bytes, os.getenv('GITHUB_ENV'))
        elif args.command == 'finish':
            print(json.dumps(finish(args.state)))
        else:
            argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
            if args.script_stdin:
                state, _ = load(args.state)
                path = Path(state['evidence'])/(args.phase+'.sh')
                with path.open('xb') as stream: stream.write(sys.stdin.buffer.read())
                argv = ['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', str(path)]
            if not argv: raise ValueError('An actual command is required')
            run_command(args.state, args.phase, argv)
    except Exception as error:
        if args.state and args.state.is_file() and args.command != 'finish':
            state = json.loads(args.state.read_bytes())
            state['exit_code'] = state['exit_code'] or 1
            state.setdefault('lifecycle_errors', []).append(str(error))
            write(args.state, state)
        print(json.dumps(dict(status='FAILED_PRESERVED', error=str(error))))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
