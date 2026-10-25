# SPDX-License-Identifier: AGPL-3.0-only
"""Build the pinned headless Mesa repair in registered scratch; never install it."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from types import SimpleNamespace

try:
    from .build_hygiene import Context, no_alias
    from .prepare_software_vulkan import digest
except ImportError:
    from build_hygiene import Context, no_alias
    from prepare_software_vulkan import digest

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / 'compat/software-vulkan-build.json'


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, indent=2) + '\n').encode())


def validate_recipe(pin):
    required = {'--buildtype=release', '--wrap-mode=nofallback', '-Dopengl=false',
                '-Dgles1=disabled', '-Dgles2=disabled', '-Degl=disabled', '-Dglx=disabled',
                '-Dgbm=disabled', '-Dgallium-drivers=[]', '-Dvulkan-drivers=swrast',
                '-Dplatforms=[]', '-Dllvm=enabled', '-Dshared-llvm=enabled'}
    flags = pin.get('flags', [])
    if pin.get('schema') != 1 or not required.issubset(flags) or len(flags) != len(set(flags)):
        raise ValueError('recipe must retain the tested headless Vulkan-only configuration')
    names = [flag.split('=', 1)[0] for flag in flags]
    if len(names) != len(set(names)):
        raise ValueError('recipe contains conflicting configuration flags')


def project_source(archive_path, destination):
    """Project release bytes, recording aliases instead of creating them."""
    destination.mkdir()
    aliases = []
    with tarfile.open(archive_path, 'r:*') as archive:
        members = {member.name: member for member in archive.getmembers()}
        if sum(m.size for m in members.values() if m.isfile()) > 2 * 1024**3:
            raise ValueError('release projection exceeds its declared source allowance')

        def regular(member, seen=()):
            if member.isfile():
                return member
            if not (member.issym() or member.islnk()) or member.name in seen:
                raise ValueError('unsupported or cyclic release member: ' + member.name)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(member.name), member.linkname)
                                       if member.issym() else member.linkname)
            if not target.startswith('mesa-n/') or target not in members:
                raise ValueError('unresolved release link: ' + member.name)
            return regular(members[target], seen + (member.name,))

        for member in members.values():
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != 'mesa-n' or '..' in parts or '.git' in parts:
                raise ValueError('unexpected release layout: ' + member.name)
            target = destination.joinpath(*parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if (member.issym() and member.name == 'mesa-n/bin/ci/pipeline_message.py'
                    and member.linkname == '../../.marge/hooks/pipeline_message.py'):
                aliases.append({'member': member.name, 'target': member.linkname, 'projection': 'omitted non-build CI hook'})
                continue
            original = regular(member)
            data = archive.extractfile(original).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(original.mode & 0o777)
            if original.name != member.name:
                aliases.append({'member': member.name, 'regular_member': original.name,
                                'sha256': hashlib.sha256(data).hexdigest(), 'projection': 'regular byte-identical file'})
    return aliases


def control_cases(text, baseline):
    cases = [json.loads(line[5:]) for line in text.splitlines() if line.startswith('CASE ')]
    combinations = {(c['clipped'], c['noperspective']) for c in cases}
    if (len(cases) != 4 or combinations != {(False, False), (False, True), (True, False), (True, True)}
            or not all(c['covered'] > 0 for c in cases)):
        raise ValueError('incomplete independent Vulkan control')
    failures = [c for c in cases if c['mismatches']]
    if baseline:
        if len(failures) != 1 or not failures[0]['clipped'] or not failures[0]['noperspective']:
            raise ValueError('baseline does not reproduce exactly the retained clipping failure')
    elif failures:
        raise ValueError('patched independent Vulkan control fails')
    if 'device_waited=true objects_destroyed=true' not in text:
        raise ValueError('independent control lacks terminal device/object cleanup')
    return cases


def build(run_id, owner, output, *, workspace=ROOT, fetch=False):
    if sys.platform != 'linux':
        raise ValueError('software Vulkan source production requires Linux')
    context = Context(workspace, ROOT / 'compat/build-hygiene.json', None)
    scratch = context.scratch(run_id)
    context.marker(scratch, run_id, owner)
    pin = json.loads(PIN.read_bytes())
    validate_recipe(pin)
    if pin['schema'] != 1 or pin['expected_peak_bytes'] > context.limit:
        raise ValueError('source-build profile exceeds the shared policy')
    output = no_alias(Path(output).absolute())
    if output.exists() or any(output.is_relative_to(base / 'build/work') for base in (ROOT, context.workspace)):
        raise ValueError('source-build record must be new and outside scratch')
    output.parent.mkdir(parents=True, exist_ok=True)
    record = {'scope': pin['scope'], 'qualified': False, 'status': 'FAIL', 'run_id': run_id,
              'owner': owner, 'pin_sha256': digest(PIN), 'commands': [], 'retained': []}

    def keep(path, roles):
        path = Path(path).absolute()
        item = {'path': str(path), 'sha256': digest(path), 'roles': roles}
        if path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / 'build'):
            record.setdefault('source_inputs', []).append(item)
        else:
            record['retained'].append(item)
        return item

    def guard():
        context.preflight(SimpleNamespace(run_id=run_id, owner=owner, expected_peak_bytes=0, register=False))
        for base in (context.workspace, *context.capacity):
            if os.statvfs(base).f_flag & os.ST_RDONLY:
                raise RuntimeError('source-build filesystem is read-only: ' + str(base))
        if context.workspace != ROOT:
            other = ROOT / 'build/work'
            if other.exists() and any(other.iterdir()):
                raise RuntimeError('another coordinator scratch root became active')
        used = sum((Path(folder) / name).lstat().st_size
                   for folder, _, names in os.walk(scratch) for name in names)
        if used > pin['expected_peak_bytes']:
            raise RuntimeError('source build exceeds its bounded profile')

    env = os.environ.copy()
    for name in ('tmp', 'cache'):
        (scratch / name).mkdir(exist_ok=True)
    env.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(scratch / 'tmp'), XDG_CACHE_HOME=str(scratch / 'cache'),
               CC='/usr/bin/cc', CXX='/usr/bin/c++', CFLAGS='', CXXFLAGS='', LDFLAGS='',
               LLVM_CONFIG='/usr/bin/llvm-config-18', CCACHE_DISABLE='1',
               GIT_CEILING_DIRECTORIES=str(scratch))

    def command(name, argv, *, codes=(0,), cwd=ROOT, extra=None):
        guard()
        log = output.with_name(output.stem + '-' + name + '.log')
        child_env = dict(env)
        child_env.update(extra or {})
        started = time.monotonic()
        child = None
        with log.open('xb') as stream:
            try:
                child = subprocess.Popen(argv, cwd=cwd, env=child_env, stdout=stream,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                while True:
                    try:
                        code = child.wait(timeout=pin['disk_guard_seconds'])
                        break
                    except subprocess.TimeoutExpired:
                        guard()
            except BaseException:
                if child is not None and child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                raise
            finally:
                if child is not None:
                    record['commands'].append({'name': name, 'argv': argv, 'cwd': str(cwd),
                        'actual_exit': child.returncode, 'child_waited': child.returncode is not None,
                        'child_pid': child.pid, 'elapsed_seconds': time.monotonic() - started,
                        'log': str(log), 'log_sha256': digest(log)})
                    keep(log, ['evidence', 'repro'])
        print(name, code, flush=True)
        if code not in codes:
            raise RuntimeError(name + ' failed; see retained log')
        return log, code

    try:
        guard()
        for path in (Path(__file__), PIN, ROOT / pin['patch']['path'], ROOT / 'LICENSE',
                     ROOT / 'compat/patches/mesa-draw-clip-LICENSE.txt',
                     ROOT / 'tools/vulkan_interpolation_control.cpp',
                     ROOT / 'tools/build_hygiene.py', ROOT / 'tools/prepare_software_vulkan.py',
                     ROOT / 'compat/build-hygiene.json', ROOT / 'compat/mesa-build-requirements.txt'):
            keep(path, ['source', 'licenses', 'repro'])
        record['toolchain'] = {name: digest(Path(name)) for name in (
            '/usr/bin/cc', '/usr/bin/c++', '/usr/bin/ninja', '/usr/bin/llvm-config-18')}
        record['build_environment'] = {key: env[key] for key in (
            'CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LLVM_CONFIG', 'GIT_CEILING_DIRECTORIES')}
        source_input = pin['source']
        archive = ROOT / 'build/artifacts' / source_input['sha256'] / source_input['name']
        if not archive.exists():
            if not fetch:
                raise FileNotFoundError('retained Mesa source is absent; explicit --fetch is required')
            temporary = scratch / 'source-download.tar.xz'
            with urllib.request.urlopen(source_input['url'], timeout=60) as response, temporary.open('xb') as stream:
                count = 0
                while data := response.read(1024 * 1024):
                    count += len(data)
                    if count > source_input['size']:
                        raise ValueError('source download exceeds pinned size')
                    stream.write(data)
            if temporary.stat().st_size != source_input['size'] or digest(temporary) != source_input['sha256']:
                raise ValueError('source download differs from pinned release')
            archive.parent.mkdir(parents=True, exist_ok=True)
            with archive.open('xb') as stream:
                with temporary.open('rb') as original:
                    shutil.copyfileobj(original, stream)
        if archive.stat().st_size != source_input['size'] or digest(archive) != source_input['sha256']:
            raise ValueError('retained Mesa release changed')
        keep(archive, ['source', 'licenses', 'repro'])
        source = scratch / 'source'
        record['source_projection'] = project_source(archive, source)
        patch = ROOT / pin['patch']['path']
        clip = source / pin['patch']['file']
        if digest(patch) != pin['patch']['sha256'] or digest(clip) != pin['patch']['before_sha256']:
            raise ValueError('patch or original clip source differs')
        native = scratch / 'native'
        meson = [sys.executable, '-B', '-m', 'mesonbuild.mesonmain']
        command('configure', meson + ['setup', str(native), str(source), '--prefix=' + str(scratch / 'install')] + pin['flags'])
        log, _ = command('targets', meson + ['introspect', '--targets', str(native)])
        libraries = [Path(name) for target in json.loads(log.read_bytes()) for name in target['filename']
                     if Path(name).name == 'libvulkan_lvp.so']
        if len(libraries) != 1 or not libraries[0].is_relative_to(native):
            raise ValueError('expected one owned Lavapipe target')
        library = libraries[0]
        ninja = ['/usr/bin/ninja', '-C', str(native), '-j', str(pin['parallel_jobs']), str(library.relative_to(native))]
        command('baseline-build', ninja)
        control = scratch / 'vulkan_interpolation_control'
        command('control-build', ['/usr/bin/c++', '-std=c++20', '-O1',
            '-I' + str(ROOT / 'third_party/dawn/third_party/vulkan-headers/src/include'),
            '-I' + str(ROOT / 'third_party/dawn/third_party/spirv-headers/src/include'),
            str(ROOT / 'tools/vulkan_interpolation_control.cpp'), '-l:libvulkan.so.1', '-o', str(control)])

        def retain_library(label):
            directory = ROOT / 'build/artifacts' / digest(library)
            directory.mkdir(exist_ok=True)
            retained = directory / library.name
            if not retained.exists():
                shutil.copyfile(library, retained)
            if digest(retained) != digest(library):
                raise ValueError('retained library differs')
            return keep(retained, ['evidence', 'repro'])

        def controls(label, baseline):
            icd = scratch / (label + '-icd.json')
            write_json(icd, {'file_format_version': '1.0.0', 'ICD': {'library_path': str(library), 'api_version': '1.3.0'}})
            log, code = command(label + '-control', [str(control)], codes=(1,) if baseline else (0,),
                                extra={'VK_DRIVER_FILES': str(icd), 'VK_ICD_FILENAMES': str(icd)})
            return control_cases(log.read_text(), baseline)

        record['baseline_library'] = retain_library('baseline')
        record['baseline_cases'] = controls('baseline', True)
        command('patch-dry-run', ['/usr/bin/patch', '--dry-run', '--batch', '-p1', '-i', str(patch)], cwd=source)
        command('patch', ['/usr/bin/patch', '--batch', '-p1', '-i', str(patch)], cwd=source)
        record['patched_source_sha256'] = digest(clip)
        command('patched-build', ninja)
        record['library'] = retain_library('patched')
        if record['library']['sha256'] == record['baseline_library']['sha256']:
            raise ValueError('patch did not change the produced library')
        record['patched_cases'] = controls('patched', False)
        notices = output.with_name(output.stem + '-NOTICES.txt')
        notices.write_bytes((source / 'debian/copyright').read_bytes() +
                            b'\nLocal patch license:\n' + (ROOT / 'LICENSE').read_bytes())
        keep(notices, ['licenses'])
        icd = output.with_name(output.stem + '-icd.json')
        write_json(icd, {'file_format_version': '1.0.0', 'ICD': {'library_path': record['library']['path'], 'api_version': '1.3.0'}})
        keep(icd, ['evidence'])
        record['environment'] = {'VK_DRIVER_FILES': str(icd), 'VK_ICD_FILENAMES': str(icd)}
        record['status'] = 'SOURCE_FUNCTIONAL_NOT_ADMITTED'
    except BaseException as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        archive = output.with_name(output.stem + '-source-inputs.zip')
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for item in record.get('source_inputs', []):
                path = Path(item['path'])
                if digest(path) != item['sha256']:
                    raise ValueError('source input changed during production')
                bundle.write(path, path.relative_to(ROOT).as_posix())
        record['retained'].append({'path': str(archive), 'sha256': digest(archive),
                                   'roles': ['source', 'licenses', 'repro']})
        write_json(output, record)
    return record


def cleanup_record(run_id, owner, output, exit_code, *, workspace=ROOT):
    """Seal actual completed commands, retain their inputs, then clean this run."""
    output = no_alias(Path(output).absolute())
    record = json.loads(output.read_bytes())
    if record['run_id'] != run_id or record['owner'] != owner:
        raise ValueError('producer record owner/run differs')
    if any(not command['child_waited'] for command in record['commands']):
        raise ValueError('producer has an unawaited child')
    if exit_code == 0 and record['status'] != 'SOURCE_FUNCTIONAL_NOT_ADMITTED':
        raise ValueError('successful exit lacks complete source controls')
    context = Context(workspace, ROOT / 'compat/build-hygiene.json', None)
    retained = {}
    for item in list(record['retained']) + [{'path': str(output), 'sha256': digest(output),
                                           'roles': ['evidence', 'repro']}]:
        previous = retained.get(item['path'])
        if previous is not None:
            if previous['sha256'] != item['sha256']:
                raise ValueError('retained path has conflicting identities')
            previous['roles'] = sorted(set(previous['roles'] + item['roles']))
        else:
            retained[item['path']] = dict(item)
    manifest = output.with_name(output.stem + '-terminal.json')
    write_json(manifest, {'schema': 1, 'run_id': run_id, 'owner': owner,
        'state': 'succeeded' if exit_code == 0 else 'failed', 'process_exit': exit_code,
        'child_waited': True, 'scratch_root': str(context.scratch(run_id)), 'retained': list(retained.values())})
    plan = context.make_plan(manifest)
    if plan['scratch_root'] != str(context.scratch(run_id)):
        raise ValueError('cleanup target differs from registered run')
    plan_path = output.with_name(output.stem + '-cleanup-plan.json')
    write_json(plan_path, plan)
    result = context.apply(SimpleNamespace(plan=str(plan_path)))
    write_json(output.with_name(output.stem + '-cleanup-result.json'), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, default=ROOT)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--cleanup-exit', type=int,
                        help='Actual awaited producer exit; retain and clean instead of building')
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise KeyboardInterrupt('source producer interrupted by signal ' + str(signum))
    previous_handler = signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.cleanup_exit is not None:
            print(json.dumps(cleanup_record(args.run_id, args.owner, args.output,
                                           args.cleanup_exit, workspace=args.workspace)))
        else:
            build(args.run_id, args.owner, args.output, workspace=args.workspace, fetch=args.fetch)
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == '__main__':
    main()
