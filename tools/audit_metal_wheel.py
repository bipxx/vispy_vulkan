"""Audit a native Metal wheel and its installed CPU extensions without a GPU."""

import argparse
from email.parser import BytesParser
import hashlib
import importlib.machinery
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import sysconfig
import traceback
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cmake'))
from runtime_package import source_package_hashes, wheel_package_hashes


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def wheel_hashes(wheel):
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate archive member')
        return {name: digest(archive.read(name)) for name in names
                if name.startswith('vispy/') and not name.endswith('/')}


def archive_audit(args):
    wheel = args.wheel.resolve(strict=True)
    require(wheel.stat().st_size <= 100 * 1024 ** 2, 'Compressed wheel exceeds 100 MiB')
    require(wheel.name.endswith('-macosx_13_0_' + args.arch + '.whl'),
            'Expected a macOS 13 wheel for ' + args.arch)
    build = args.build_dir.resolve(strict=True)
    cache = {}
    for line in (build / 'CMakeCache.txt').read_text().splitlines():
        if line and not line.startswith(('#', '//')) and ':' in line and '=' in line:
            key, value = line.split('=', 1)
            cache[key.split(':', 1)[0]] = value
    for key, expected in {
        'VISPY_CPU_CONTRACTS_ONLY': 'OFF', 'VISPY_INPLACE': 'OFF',
        'VISPY_VERIFY_DEPENDENCIES': 'ON', 'DAWN_ENABLE_METAL': 'ON',
        'DAWN_ENABLE_VULKAN': 'OFF', 'DAWN_ENABLE_NULL': 'OFF',
        'CMAKE_OSX_ARCHITECTURES': args.arch, 'CMAKE_OSX_DEPLOYMENT_TARGET': '13.0',
    }.items():
        require(cache.get(key) == expected, key + ' differs from the native Metal build')
    package = source_package_hashes(ROOT)
    notices = {'vispy/_licenses/' + p.name: digest(p.read_bytes())
               for p in (ROOT / 'third_party/licenses').iterdir()
               if p.is_file() and p.suffix in ('.txt', '.md', '.json')}
    notices.update({'vispy/_licenses/' + name: digest((ROOT / name).read_bytes())
                    for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md')})
    suffix = sysconfig.get_config_var('EXT_SUFFIX')
    native = ['vispy/_dawn' + suffix, 'vispy/visuals/text/_sdf_cpu' + suffix]
    hashes = wheel_package_hashes(wheel, root=ROOT)
    require(set(hashes) == set(package) | set(notices) | set(native),
            'Wheel package contents differ from tracked sources, notices and two native extensions')
    for name, expected in {**package, **notices}.items():
        require(hashes[name] == expected, 'Packaged bytes differ: ' + name)
    raw_hashes = {name: digest((build / Path(name).name).read_bytes()) for name in native}
    origin = args.output.parent / 'native-origin'
    require(not origin.exists(), 'A fresh native-origin install prefix is required')
    shutil.copyfile(build / 'install_manifest.txt', args.output.parent / 'original-install-manifest.txt')
    with (args.output.parent / 'native-origin.log').open('xb') as log:
        subprocess.run([cache['CMAKE_COMMAND'], '--install', str(build), '--prefix', str(origin), '--strip'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    libraries = {}
    with zipfile.ZipFile(wheel) as archive:
        for name in native:
            data = archive.read(name)
            require(len(data) >= 8 and struct.unpack_from('<II', data) ==
                    (0xfeedfacf, {'arm64': 0x0100000c, 'x86_64': 0x01000007}[args.arch]),
                    'Native Mach-O architecture differs: ' + name)
            path = origin / name
            require(digest(path.read_bytes()) == hashes[name], 'Controlled stripped origin differs: ' + name)
            raw = build / Path(name).name
            require(digest(raw.read_bytes()) == raw_hashes[name], 'Raw build leaf changed during installation: ' + name)
            dependencies = subprocess.check_output(['otool', '-L', str(path)], text=True)
            for line in dependencies.splitlines()[1:]:
                dependency = line.strip().split(' (', 1)[0]
                require(dependency.startswith(('/usr/lib/', '/System/Library/')),
                        'Unbundled non-system library dependency: ' + dependency)
            libraries[name] = {'wheel_sha256': hashes[name], 'raw_sha256': digest(raw.read_bytes()),
                               'controlled_stripped_sha256': digest(path.read_bytes()),
                               'otool_dependencies': dependencies}
        metadata = BytesParser().parsebytes(archive.read(next(n for n in archive.namelist()
                                                             if n.endswith('.dist-info/METADATA'))))
        require(metadata['Name'] == 'vispy' and metadata['Version'] == '0.17.0+vulkan.1',
                'Distribution identity differs')
        require(metadata['License-Expression'] == 'AGPL-3.0-only', 'Implementation license differs')
        for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md'):
            copies = [n for n in archive.namelist()
                      if n == 'vispy/_licenses/' + name or n.endswith('.dist-info/licenses/' + name)]
            require(len(copies) == 2 and all(digest(archive.read(n)) == digest((ROOT / name).read_bytes())
                                            for n in copies), 'License copies differ: ' + name)
    (args.output.parent / 'wheel-requirements.txt').write_text(
        'vispy @ ' + wheel.as_uri() + ' --hash=sha256:' + digest(wheel.read_bytes()) + '\n')
    return {'status': 'PASS_METAL_WHEEL_ARCHIVE_BUILD_ONLY', 'wheel': str(wheel),
            'wheel_sha256': digest(wheel.read_bytes()), 'architecture': args.arch,
            'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'package_members': len(package), 'notice_members': len(notices),
            'package_hashes': hashes, 'native': libraries, 'GPU_qualified': False}


def consumer_audit(args):
    require(sys.flags.isolated and sys.flags.dont_write_bytecode, 'Run the consumer with Python -I -B')
    record = json.loads(args.archive_report.read_text())
    require(record['status'] == 'PASS_METAL_WHEEL_ARCHIVE_BUILD_ONLY', 'Archive audit must pass first')
    import numpy as np
    import vispy
    from vispy import _dawn
    from vispy.visuals.text import _sdf_cpu

    prefix = Path(sys.prefix).resolve()
    package = Path(vispy.__file__).resolve().parent
    require(not prefix.is_relative_to(ROOT) and package.is_relative_to(prefix),
            'An external installed-wheel environment is required')
    for name, expected in record['package_hashes'].items():
        require(digest((package / Path(name).relative_to('vispy')).read_bytes()) == expected,
                'Installed package differs: ' + name)
    modules = {}
    for module in (_dawn, _sdf_cpu):
        path = Path(module.__file__).resolve()
        require(path.is_relative_to(package) and any(str(path).endswith(s)
                for s in importlib.machinery.EXTENSION_SUFFIXES), 'Compiled extension origin differs')
        modules[module.__name__] = {'path': str(path), 'sha256': digest(path.read_bytes())}
    reference = json.loads((ROOT / 'tests/contract/data/sdf_upstream.json').read_text())
    arrays = ROOT / 'tests/contract/data/sdf_upstream.npz'
    require(digest(arrays.read_bytes()) == reference['arrays_sha256'], 'CPU SDF reference differs')
    with np.load(arrays, allow_pickle=False) as data:
        for case in reference['cases']:
            image = data[case + '_input'].copy()
            require(_sdf_cpu._calc_distance_field(image, image.shape[1], image.shape[0], reference['spread']) is None,
                    'Compiled SDF helper must mutate in place')
            np.testing.assert_array_equal(image, data[case + '_expected'])
    return {'status': 'PASS_INSTALLED_METAL_WHEEL_CPU_IMPORTS_ONLY', 'architecture': args.arch,
            'wheel_sha256': record['wheel_sha256'], 'installed_members_verified': len(record['package_hashes']),
            'compiled_modules': modules, 'compiled_SDF_cases': reference['cases'],
            'native_revision': _dawn.revision(), 'GPU_qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('archive', 'consumer'))
    parser.add_argument('--arch', choices=('arm64', 'x86_64'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--build-dir', type=Path)
    parser.add_argument('--archive-report', type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    require(sys.platform == 'darwin' and platform.machine() == args.arch,
            'Run on the requested native macOS architecture')
    require(not args.output.exists(), 'Output must be fresh')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = archive_audit(args) if args.mode == 'archive' else consumer_audit(args)
    except BaseException:
        args.output.write_text(json.dumps({'status': 'FAILED_PRESERVED', 'mode': args.mode,
                                           'error': traceback.format_exc(), 'GPU_qualified': False}, indent=2),
                               encoding='utf-8')
        raise
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
