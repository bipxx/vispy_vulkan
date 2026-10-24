"""Read an installed consumer's exact package/native-file inventory."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import sysconfig
import subprocess
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from no_opengl.policy import library_reason


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(wheel):
    wheel = Path(wheel).resolve(strict=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cmake'))
    from runtime_package import wheel_package_hashes
    members = wheel_package_hashes(wheel)
    prefix = Path(sys.prefix).resolve()
    distribution = importlib.metadata.distribution('vispy')
    package = Path(distribution.locate_file('vispy')).resolve(strict=True)
    if not package.is_relative_to(prefix):
        raise RuntimeError('Candidate package is outside the consumer prefix')
    with zipfile.ZipFile(wheel) as archive:
        for name in members:
            if (package / Path(name).relative_to('vispy')).read_bytes() != archive.read(name):
                raise RuntimeError('Installed candidate differs from wheel: ' + name)
    distributions, requirements, errors = [], [], []
    try:
        from packaging.requirements import Requirement
    except ImportError:
        Requirement = None
        errors.append('packaging is missing; active dependency markers cannot be evaluated')
    for item in importlib.metadata.distributions():
        metadata = item.read_text('METADATA') or ''
        name = item.metadata.get('Name', '')
        required = item.requires or []
        distributions.append({'name': name, 'version': item.version,
                              'metadata_sha256': hashlib.sha256(metadata.encode()).hexdigest(),
                              'requires': sorted(required)})
        for text in required:
            if Requirement:
                requirement = Requirement(text)
                if requirement.marker and not requirement.marker.evaluate({'extra': ''}):
                    continue
                target = requirement.name
            else:
                target = re.split(r'[\s(<>=!;\[]', text, 1)[0]
            if target.casefold().replace('_', '-') in ('pyopengl', 'pyopengl-accelerate', 'moderngl', 'glcontext'):
                requirements.append({'distribution': name, 'requirement': text})
        if name.casefold().replace('_', '-') in ('pyopengl', 'pyopengl-accelerate', 'moderngl', 'glcontext'):
            requirements.append({'distribution': name, 'reason': 'Installed OpenGL implementation'})
    native, gl_files = [], []
    directories = {Path(sysconfig.get_path(key)).resolve() for key in ('purelib', 'platlib')}
    for directory in directories:
        if not directory.is_relative_to(prefix):
            raise RuntimeError('Package directory outside consumer: ' + str(directory))
        for path in directory.rglob('*'):
            if path.is_file() and (path.suffix.casefold() in ('.dll', '.pyd', '.dylib') or re.search(r'\.so(?:\.\d+)*$', path.name)):
                entry = {'path': str(path.resolve()), 'sha256': digest(path)}
                native.append(entry)
                if library_reason(path):
                    gl_files.append(entry)
    system_inventory = None
    if sys.platform.startswith('linux'):
        scan_roots = [Path(value) for value in ('/lib', '/usr/lib', '/usr/local/lib', '/opt') if Path(value).is_dir()]
        system_gl_files = sorted({str(path.resolve()) for directory in scan_roots for path in directory.rglob('*')
                                  if path.is_file() and library_reason(path)})
        packages = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n'], capture_output=True, text=True)
        if packages.returncode:
            errors.append('dpkg inventory unavailable: ' + packages.stderr)
        gl_packages = [line for line in packages.stdout.splitlines() if re.match(
            r'^(?:libgl1|libglx0|libglx-mesa0|libegl1|libegl-mesa0|libgles1|libgles2|libosmesa6|libglvnd0)(?::[^\t]+)?\t', line)]
        system_inventory = {'scan_roots': [str(path) for path in scan_roots], 'gl_runtime_files': system_gl_files,
                            'package_inventory': packages.stdout.splitlines(), 'gl_packages': gl_packages,
                            'os_release': Path('/etc/os-release').read_text()}
    identity = {'prefix': str(prefix), 'base_prefix': str(Path(sys.base_prefix).resolve()),
                'executable': str(Path(sys.executable).resolve()), 'executable_sha256': digest(sys.executable),
                'python': sys.version, 'platform': sys.platform, 'os_version': str(sys.getwindowsversion()) if sys.platform == 'win32' else os.uname().release,
                'wheel_sha256': digest(wheel), 'wheel_members_verified': len(members),
                'distributions': sorted(distributions, key=lambda row: (row['name'].casefold(), row['version'])),
                'native_files': sorted(native, key=lambda row: row['path']), 'system_inventory': system_inventory}
    identity['environment_id'] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {**identity, 'gl_runtime_files': gl_files, 'gl_requirements': requirements, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Fresh inventory report required')
    try:
        value = collect(args.wheel)
        system = value.get('system_inventory') or {}
        value['status'] = 'PASS_INVENTORY' if not any(value[key] for key in ('gl_runtime_files', 'gl_requirements', 'errors')) and not system.get('gl_runtime_files') and not system.get('gl_packages') else 'FAIL_INVENTORY'
    except BaseException as error:
        import traceback
        value = {'status': 'FAILED_INVENTORY', 'error': str(error), 'traceback': traceback.format_exc(),
                 'prefix': sys.prefix, 'base_prefix': sys.base_prefix, 'executable': sys.executable}
    args.output.write_text(json.dumps(value, indent=2) + '\n')
    return 0 if value['status'] == 'PASS_INVENTORY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
