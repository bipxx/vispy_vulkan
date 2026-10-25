"""Verify a Linux renderer wheel against tracked sources and stripped build outputs."""

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cmake'))
from runtime_package import source_package_hashes, wheel_package_hashes
sys.path.insert(0, str(ROOT / 'tools'))
from run_linux_native_contracts import validate_retained


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--contracts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    build = args.build_dir.resolve(strict=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    assert wheel.name == 'vispy-0.17.0+vulkan.1-cp312-cp312-linux_x86_64.whl'
    assert wheel.stat().st_size <= 100 * 1024 ** 2
    contracts = validate_retained(args.contracts, build, (build / 'CMakeCache.txt').read_bytes())
    cache = {}
    for line in (build / 'CMakeCache.txt').read_text().splitlines():
        if line and not line.startswith(('#', '//')) and ':' in line and '=' in line:
            key, value = line.split('=', 1)
            cache[key.split(':', 1)[0]] = value
    for key, value in {'VISPY_CPU_CONTRACTS_ONLY': 'OFF', 'VISPY_INPLACE': 'OFF',
                       'VISPY_VERIFY_DEPENDENCIES': 'ON', 'DAWN_ENABLE_VULKAN': 'ON',
                       'DAWN_ENABLE_METAL': 'OFF', 'DAWN_ENABLE_NULL': 'OFF',
                       'TINT_BUILD_SPV_READER': 'ON', 'DAWN_ENABLE_SPIRV_VALIDATION': 'ON'}.items():
        assert cache.get(key) == value, key
    package = source_package_hashes(ROOT)
    notices = {'vispy/_licenses/' + p.name: digest(p.read_bytes())
               for p in (ROOT / 'third_party/licenses').iterdir()
               if p.is_file() and p.suffix in ('.txt', '.md', '.json')}
    notices.update({'vispy/_licenses/' + name: digest((ROOT / name).read_bytes())
                    for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md')})
    suffix = sysconfig.get_config_var('EXT_SUFFIX')
    native = ['vispy/_dawn' + suffix, 'vispy/visuals/text/_sdf_cpu' + suffix,
              'vispy/VkLayer_vispy_submit.so', 'vispy/VkLayer_vispy_submit.json']
    raw = {name: build / ('generated' if name.endswith('.json') else '') / Path(name).name
           for name in native}
    raw_hashes = {name: digest(path.read_bytes()) for name, path in raw.items()}
    origin = args.output.parent / 'native-origin'
    assert not origin.exists(), 'A new controlled install prefix is required'
    shutil.copyfile(build / 'install_manifest.txt', args.output.parent / 'original-install-manifest.txt')
    cmake = cache['CMAKE_COMMAND']
    if not Path(cmake).is_file():
        cmake = shutil.which('cmake')
    assert cmake
    with (args.output.parent / 'native-origin.log').open('wb') as log:
        subprocess.run([cmake, '--install', str(build), '--prefix', str(origin), '--strip'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        hashes = wheel_package_hashes(wheel, root=ROOT)
        assert set(hashes) == set(package) | set(notices) | set(native)
        for name, expected in {**package, **notices}.items():
            assert hashes[name] == expected, name
        for name in native:
            assert digest((origin / name).read_bytes()) == hashes[name], name
            assert digest(raw[name].read_bytes()) == raw_hashes[name], name
            if name.endswith('.so'):
                data = archive.read(name)
                assert data[:6] == b'\x7fELF\x02\x01' and data[18:20] == b'\x3e\x00', name
        metadata = BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith('.dist-info/METADATA'))))
        assert metadata['Name'] == 'vispy' and metadata['Version'] == '0.17.0+vulkan.1'
        assert metadata['License-Expression'] == 'AGPL-3.0-only'
        assert metadata['Description-Content-Type'] == 'text/markdown'
        for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md'):
            copies = [n for n in names if n == 'vispy/_licenses/' + name or n.endswith('.dist-info/licenses/' + name)]
            assert len(copies) == 2 and all(digest(archive.read(n)) == digest((ROOT / name).read_bytes()) for n in copies)
    wheel_sha = digest(wheel.read_bytes())
    (args.output.parent / 'wheel-requirements.txt').write_text('vispy @ ' + wheel.as_uri() + ' --hash=sha256:' + wheel_sha + '\n')
    args.output.write_text(json.dumps({'status': 'PASS_LINUX_RENDERER_WHEEL_ARCHIVE', 'wheel': str(wheel),
        'wheel_sha256': wheel_sha, 'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'package_members': len(package), 'notice_members': len(notices), 'native_members': len(native),
        'native_origin': {name: {'raw_sha256': raw_hashes[name], 'wheel_stripped_sha256': hashes[name]} for name in native},
        'native_contracts': {'report': str((args.contracts / 'result.json').resolve()),
                             'sha256': digest((args.contracts / 'result.json').read_bytes()),
                             'tests': contracts['tests'], 'producer_admitted': False},
        'hardware_qualified': False, 'manylinux_qualified': False}, indent=2) + '\n')
    print('PASS_LINUX_RENDERER_WHEEL_ARCHIVE', wheel_sha, flush=True)


if __name__ == '__main__':
    main()
