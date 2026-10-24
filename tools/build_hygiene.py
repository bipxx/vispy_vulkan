"""Bounded file lifecycle for explicitly owned, terminal build/work runs.

All commands are read-only unless --register, plan --output, or apply is explicit.
expected-peak-bytes means additional worst-case allocation, across the managed
scratch budget. This tool never adopts or cleans legacy build directories.
Registry capacity_roots checks explicitly listed backing storage too.
Concurrent writers are unsupported: child completion and one owner are required.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys


class Refusal(ValueError):
    pass


MARKER = '.build-hygiene-owner.json'
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'compat/build-hygiene.json'


def require(condition, message):
    if not condition:
        raise Refusal(message)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, name + ' must be an integer >= ' + str(minimum))
    return value


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read_json(path):
    with path.open(encoding='utf-8') as stream:
        value = json.load(stream)
    require(isinstance(value, dict), 'JSON object required: ' + str(path))
    require(type(value.get('schema')) is int and value['schema'] == 1, 'schema must be 1: ' + str(path))
    return value


def absolute(value, base):
    require(isinstance(value, (str, Path)) and str(value), 'A nonempty file path is required')
    path = Path(value)
    require('..' not in path.parts, 'Parent traversal is not admitted: ' + str(value))
    return Path(os.path.abspath(path if path.is_absolute() else base / path))


def no_alias(path):
    # Check existing ancestors too: resolve() alone would silently admit aliases.
    for component in reversed((path, *path.parents)):
        if os.name == 'nt' and component.name:
            name = component.name
            reserved = name.split('.')[0].upper()
            require(not name.endswith(('.', ' ')) and ':' not in name and
                    reserved not in {'CON', 'PRN', 'AUX', 'NUL'} and
                    not re.fullmatch(r'(COM|LPT)[1-9]', reserved), 'Windows filename alias is not admitted')
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and
                not getattr(info, 'st_file_attributes', 0) & 0x400,
                'Alias/reparse path is not admitted: ' + str(component))
    require(path.resolve() == path, 'Noncanonical path alias is not admitted: ' + str(path))
    return path


def inside(path, root):
    return path == root or root in path.parents


def overlaps(left, right):
    return inside(left, right) or inside(right, left)


def identity(path):
    info = path.stat()
    return {'device': info.st_dev, 'inode': info.st_ino, 'mtime_ns': info.st_mtime_ns}


def live_pid(pid):
    integer(pid, 'child_pid', 1)
    require(pid <= 0x7fffffff, 'child_pid is outside the admitted PID range')
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            require(ctypes.get_last_error() == 87, 'Cannot establish child PID completion')
            return False
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            require(result in (0, 258), 'Cannot establish child PID completion')
            return result == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError as error:
        raise Refusal('Cannot establish child PID completion') from error


class Context:
    def __init__(self, workspace, policy, registry):
        self.deleted = 0
        self.capacity_checks = []
        self.workspace = no_alias(absolute(workspace, Path.cwd()))
        require(self.workspace.is_dir(), 'Workspace must exist')
        self.build = self.workspace / 'build'
        self.work = self.build / 'work'
        self.policy_path = no_alias(absolute(policy, self.workspace))
        self.policy = read_json(self.policy_path)
        require(self.policy.get('managed_root', 'build/work') == 'build/work', 'Managed root must be build/work')
        self.limit = integer(self.policy.get('max_scratch_bytes'), 'max_scratch_bytes', 1)
        self.reserve = integer(self.policy.get('min_free_bytes'), 'min_free_bytes')
        self.registry_path = no_alias(absolute(registry, self.workspace)) if registry else None
        self.registry = read_json(self.registry_path) if registry else {}
        self.blocked = self.paths('blocked_roots')
        self.protected = self.paths('protected_roots')
        self.protected += [self.workspace / name for name in (
            '.git', 'src', 'cpp', 'cmake', 'compat', 'docs', 'tests', 'tools',
            'third_party', 'licenses', 'LICENSE', 'LICENSE-BSD', 'LICENSING.md')]
        self.protected += [self.policy_path] + ([self.registry_path] if self.registry_path else [])
        self.legacy = self.paths('legacy_roots')
        self.capacity = self.paths('capacity_roots')
        no_alias(self.work)

    def paths(self, name):
        values = self.registry.get(name, [])
        require(isinstance(values, list), name + ' must be a list of explicit paths')
        require(all(isinstance(x, str) and not any(c in x for c in '*?[]') for x in values),
                name + ' must contain explicit paths, not patterns')
        return [no_alias(absolute(x, self.workspace)) for x in values]

    def unknown(self):
        if 'legacy_roots' not in self.registry or not self.build.exists():
            return []
        admitted = {p.relative_to(self.build).parts[0] for p in self.legacy
                    if inside(p, self.build) and p != self.build}
        return sorted(str(p) for p in self.build.iterdir() if p.name != 'work' and p.name not in admitted)

    def admitted(self):
        unknown = self.unknown()
        require(not unknown, 'Unregistered top-level build roots: ' + ', '.join(unknown))

    def clean_target(self, path):
        no_alias(path)
        require(not any(p.name.lower() == '.git' for p in (path, *path.parents)), '.git cannot be a cleanup/output target')
        for protected in self.protected + self.blocked:
            require(not overlaps(path, protected), 'Target conflicts with protected/blocked path: ' + str(protected))

    def scratch(self, run_id):
        require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id), 'Invalid run_id')
        path = self.work / run_id
        self.clean_target(path)
        return path

    def marker(self, scratch, run_id, owner):
        require(isinstance(owner, str) and owner.strip() and len(owner) <= 200, 'A nonempty owner is required')
        marker = no_alias(scratch / MARKER)
        require(marker.is_file(), 'Run is unregistered; use preflight --register before writing scratch')
        content = read_json(marker)
        require(content == {'schema': 1, 'run_id': run_id, 'owner': owner}, 'Run owner/identity differs')

    def snapshot(self, root, hash_files=True):
        no_alias(root)
        require(root.is_dir(), 'Scratch root must be a real directory')
        directories, files = [], []
        for folder, children, names in os.walk(root, followlinks=False):
            folder = Path(folder)
            no_alias(folder)
            require(folder.name.lower() != '.git', '.git content is not disposable scratch')
            directories.append({'path': folder.relative_to(root).as_posix(), **identity(folder)})
            for child in children:
                no_alias(folder / child)
            for name in names:
                file = no_alias(folder / name)
                info = file.stat()
                require(name.lower() != '.git' and stat.S_ISREG(info.st_mode), 'Only ordinary scratch files are admitted')
                require(info.st_nlink == 1, 'Hardlinked scratch file is not admitted: ' + str(file))
                entry = {'path': file.relative_to(root).as_posix(), 'bytes': info.st_size, **identity(file)}
                if hash_files:
                    entry['sha256'] = digest(file)
                files.append(entry)
        return {'directories': sorted(directories, key=lambda x: x['path']),
                'files': sorted(files, key=lambda x: x['path'])}

    def total(self):
        if not self.work.exists():
            return 0
        return sum(x['bytes'] for x in self.snapshot(self.work, False)['files'])

    def check_capacity(self, extra, registration_bytes):
        roots = list(dict.fromkeys([self.workspace, *self.capacity]))
        self.capacity_checks = []
        for root in roots:
            no_alias(root)
            require(root.is_dir(), 'Capacity root must be an existing directory: ' + str(root))
            self.capacity_checks.append({'path': str(root), 'free_bytes': shutil.disk_usage(root).free,
                                         'min_free_bytes': self.reserve, 'expected_peak_bytes': extra,
                                         'registration_bytes': registration_bytes})
        for check in self.capacity_checks:
            require(check['free_bytes'] - extra - registration_bytes >= self.reserve,
                    'Expected peak would cross minimum disk reserve at ' + check['path'])

    def preflight(self, args):
        self.admitted()
        scratch = self.scratch(args.run_id)
        require(isinstance(args.owner, str) and args.owner.strip() and len(args.owner) <= 200,
                'A nonempty owner of at most 200 characters is required')
        extra = integer(args.expected_peak_bytes, 'expected_peak_bytes')
        total = self.total()
        marker_bytes = json.dumps({'schema': 1, 'run_id': args.run_id, 'owner': args.owner}).encode('utf-8')
        registration_bytes = len(marker_bytes) if args.register and not scratch.exists() else 0
        require(total + extra + registration_bytes <= self.limit, 'Expected peak exceeds managed scratch budget')
        self.check_capacity(extra, registration_bytes)
        if scratch.exists():
            self.marker(scratch, args.run_id, args.owner)
        elif args.register:
            # This is the sole registration mutation; no legacy adoption or force flag.
            no_alias(scratch.parent)
            scratch.mkdir(parents=True, exist_ok=False)
            with (scratch / MARKER).open('xb') as stream:
                stream.write(marker_bytes)
            self.marker(scratch, args.run_id, args.owner)
            # Account for actual directory/file allocation before permitting the build.
            self.check_capacity(extra, 0)
        return {'status': 'PASS_PREFLIGHT', 'scratch_root': str(scratch), 'registered': scratch.exists(),
                'owner': args.owner, 'managed_bytes': total + registration_bytes, 'expected_peak_bytes': extra,
                'free_bytes': self.capacity_checks[0]['free_bytes'], 'min_free_bytes': self.reserve,
                'max_scratch_bytes': self.limit, 'registration_bytes': registration_bytes,
                'capacity_checks': self.capacity_checks}

    def make_plan(self, manifest_path):
        self.admitted()
        manifest_path = no_alias(absolute(manifest_path, self.workspace))
        manifest = read_json(manifest_path)
        run_id, owner = manifest.get('run_id'), manifest.get('owner')
        scratch = self.scratch(run_id)
        require(not inside(manifest_path, scratch), 'Retention manifest must be outside scratch')
        require(absolute(manifest.get('scratch_root'), self.workspace) == scratch,
                'scratch_root must be exactly build/work/run_id')
        self.marker(scratch, run_id, owner)
        state = manifest.get('state')
        require(state in ('succeeded', 'failed', 'cancelled'), 'Run must have a terminal state')
        require(type(manifest.get('process_exit')) is int, 'process_exit must be an integer')
        require(state != 'succeeded' or manifest['process_exit'] == 0, 'Succeeded run must have process_exit 0')
        require(manifest.get('child_waited') is True, 'child_waited must be true')
        if 'child_pid' in manifest:
            require(not live_pid(manifest['child_pid']), 'Child PID is still live')
        retained = manifest.get('retained')
        require(isinstance(retained, list) and retained, 'Retained provenance is required')
        roles, records, seen = set(), [], set()
        for item in retained:
            require(isinstance(item, dict), 'Each retained item must be an object')
            path = no_alias(absolute(item.get('path'), self.workspace))
            require(not inside(path, scratch), 'Retained file must be outside scratch')
            require(path not in seen, 'Duplicate retained path; combine roles in one record')
            seen.add(path)
            require(path.is_file(), 'Retained content must exist: ' + str(path))
            expected = item.get('sha256')
            require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected), 'Invalid retained sha256')
            require(digest(path) == expected, 'Retained content hash differs: ' + str(path))
            item_roles = item.get('roles')
            require(isinstance(item_roles, list) and item_roles and
                    all(isinstance(x, str) and x for x in item_roles), 'Retained roles must be nonempty strings')
            roles.update(item_roles)
            records.append({'path': str(path), 'sha256': expected, 'roles': item_roles})
        required = {'source', 'evidence', 'licenses'} | ({'repro'} if state != 'succeeded' else set())
        require(required <= roles, 'Missing retained roles: ' + ', '.join(sorted(required - roles)))
        snapshot = self.snapshot(scratch)
        return {'schema': 1, 'kind': 'build-hygiene-cleanup-plan', 'workspace': str(self.workspace),
                'manifest': str(manifest_path), 'manifest_sha256': digest(manifest_path),
                'policy': str(self.policy_path), 'policy_sha256': digest(self.policy_path),
                'registry': str(self.registry_path) if self.registry_path else None,
                'registry_sha256': digest(self.registry_path) if self.registry_path else None,
                'run_id': run_id, 'owner': owner, 'scratch_root': str(scratch),
                'retained': records, 'snapshot': snapshot}

    def plan(self, args):
        plan = self.make_plan(args.manifest)
        output = absolute(args.output, self.workspace)
        self.clean_target(output)
        require(not inside(output, Path(plan['scratch_root'])), 'Plan must be outside scratch')
        if 'legacy_roots' in self.registry and inside(output, self.build):
            top = self.build / output.relative_to(self.build).parts[0]
            require(top != self.work and any(inside(p, top) for p in self.legacy),
                    'Plan output would create an unregistered top-level build root')
        require(output.parent.is_dir(), 'Plan output parent must exist')
        with output.open('x', encoding='utf-8') as stream:
            json.dump(plan, stream, indent=2)
            stream.write('\n')
        return {'status': 'PASS_PLAN', 'plan': str(output), 'files': len(plan['snapshot']['files']),
                'bytes': sum(x['bytes'] for x in plan['snapshot']['files']), 'deleted': 0}

    def apply(self, args):
        plan_path = no_alias(absolute(args.plan, self.workspace))
        plan = read_json(plan_path)
        require(plan.get('kind') == 'build-hygiene-cleanup-plan', 'Not a cleanup plan')
        require(plan == self.make_plan(plan.get('manifest')), 'Plan, scratch, retained content, policy or registry changed')
        scratch = Path(plan['scratch_root'])
        require(not inside(plan_path, scratch), 'Plan must be outside scratch')
        deleted = 0
        for file in plan['snapshot']['files']:
            path = no_alias(scratch / file['path'])
            require(identity(path) == {k: file[k] for k in ('device', 'inode', 'mtime_ns')} and
                    digest(path) == file['sha256'], 'Scratch changed during apply')
            path.unlink()
            deleted += 1
            self.deleted = deleted
        for directory in sorted(plan['snapshot']['directories'], key=lambda x: len(Path(x['path']).parts), reverse=True):
            path = no_alias(scratch / directory['path'])
            path.rmdir()  # Never recurse; an unexpected writer makes this fail.
        return {'status': 'PASS_APPLY', 'deleted': deleted, 'scratch_root': str(scratch), 'retained_verified': len(plan['retained'])}

    def audit(self):
        runs, data = [], []
        if self.work.exists():
            for path in sorted(self.work.iterdir()):
                snapshot = self.snapshot(path, False)
                marker = no_alias(path / MARKER)
                value = read_json(marker) if marker.is_file() else {}
                registered = (value.get('run_id') == path.name and isinstance(value.get('owner'), str)
                              and bool(value['owner'].strip()) and len(value['owner']) <= 200)
                size = sum(x['bytes'] for x in snapshot['files'])
                protected = any(overlaps(path, p) for p in self.protected + self.blocked)
                runs.append({'run_id': path.name, 'owner': value.get('owner'), 'registered': registered,
                             'bytes': size, 'files': len(snapshot['files']), 'disposable': False,
                             'cleanup_eligibility': 'Protected/blocked; not eligible' if protected else
                             'Unregistered; manual review required' if not registered else
                             'Requires terminal retained manifest and explicit validated plan'})
                if not protected and registered:
                    data.append({'path': str(path), 'bytes': size, 'cleanup_requires_plan': True})
        unknown = self.unknown()
        return {'status': 'REFUSED_AUDIT' if unknown else 'PASS_AUDIT', 'managed_runs': runs,
                'managed_disposable_data': data, 'total_managed_bytes': sum(x['bytes'] for x in runs),
                'protected_history': [{'path': str(p), 'kind': kind} for kind, paths in
                                      [('protected', self.protected), ('blocked', self.blocked), ('legacy', self.legacy)] for p in paths],
                'unknown_build_roots': unknown, 'deleted': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--policy', default=str(DEFAULT_POLICY))
    parser.add_argument('--registry')
    commands = parser.add_subparsers(dest='command')
    preflight = commands.add_parser('preflight')
    preflight.add_argument('--run-id', required=True)
    preflight.add_argument('--owner', required=True)
    preflight.add_argument('--expected-peak-bytes', type=int, required=True)
    preflight.add_argument('--register', action='store_true')
    plan = commands.add_parser('plan')
    plan.add_argument('--manifest', required=True)
    plan.add_argument('--output', required=True)
    apply = commands.add_parser('apply')
    apply.add_argument('--plan', required=True)
    commands.add_parser('audit')
    args = parser.parse_args(argv)
    try:
        context = Context(args.workspace, args.policy, args.registry)
        result = context.audit() if args.command in (None, 'audit') else getattr(context, args.command)(args)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'].startswith('PASS_') else 2
    except (Refusal, OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'status': 'REFUSED', 'error': str(error),
                          'deleted': context.deleted if 'context' in locals() else 0,
                          'capacity_checks': context.capacity_checks if 'context' in locals() else []}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
