"""Verify a Linux renderer wheel against tracked sources and stripped build outputs."""

import argparse
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import re
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
from native_epoch import member, project_inventory


def digest(data):
    return hashlib.sha256(data).hexdigest()


def auditor_identity():
    paths = [Path(__file__).resolve()]
    paths += [Path(sys.modules[function.__module__].__file__).resolve()
              for function in (source_package_hashes, validate_retained, project_inventory)]
    return {str(path): digest(path.read_bytes()) for path in paths}


def git_blob_hashes(repository, commit, names):
    argv = ['git', '-c', 'safe.directory='+str(repository), '-C', str(repository), 'cat-file', '--batch']
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = child.communicate(''.join(commit+':'+name+'\n' for name in names).encode())
    assert child.returncode == 0, err.decode()
    stream, hashes = io.BytesIO(out), {}
    for name in names:
        header = stream.readline().split()
        assert len(header) == 3 and header[1] == b'blob', 'Source is not a committed blob: '+name
        count = int(header[2])
        payload = stream.read(count)
        assert len(payload) == count and stream.read(1) == b'\n'
        hashes[name] = digest(payload)
    assert stream.read() == b''
    return hashes, dict(argv=argv, child_pid=child.pid, actual_exit=child.returncode, child_waited=True)


def archive_source_revision(root, manifest):
    """Join an exact export receipt and complete source hashes; never invent Git."""
    root = Path(root).absolute()
    assert root.resolve(strict=True) == root, 'Source root must be physical'
    manifest = Path(manifest).resolve(strict=True)
    assert not manifest.is_relative_to(root), 'Retain source authority outside the export'
    data = json.loads(manifest.read_bytes())
    assert type(data.get('schema')) is int and data['schema'] == 1
    assert data.get('kind') == 'git-archive-source-inventory'
    commit = data.get('commit')
    assert isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'Exact source commit required'
    files = data.get('files')
    assert isinstance(files, dict) and files, 'Source hashes required'
    assert data.get('auditor_files') == auditor_identity(), 'External auditor dependencies changed'
    export_ref = data['export_inventory']
    export_path = Path(export_ref['path']).resolve(strict=True)
    assert not export_path.is_relative_to(root)
    assert digest(export_path.read_bytes()) == export_ref['sha256'], 'Pre-build export inventory changed'
    exported = json.loads(export_path.read_bytes())
    assert exported['commit'] == commit and isinstance(exported['files'], dict) and exported['files']
    assert set(exported['files']) <= set(files), 'Source authority drops exported inputs'
    for name, checksum in files.items():
        assert isinstance(name, str) and '\n' not in name and '\0' not in name
        if not name.startswith('third_party/licenses/'):
            assert exported['files'].get(name) == checksum, 'Source hash differs from pre-build export: '+name
    required = project_inventory(root)
    required.update({name: digest(member(root, name).read_bytes())
                     for name in ('README.md', 'compat/runtime-package.json')})
    assert set(required) <= set(files), 'Source authority omits production/package inputs'
    receipt_ref = data['export_receipt']
    receipt_path = Path(receipt_ref['path']).resolve(strict=True)
    assert not receipt_path.is_relative_to(root), 'Retain export receipt outside the source'
    assert digest(receipt_path.read_bytes()) == receipt_ref['sha256'], 'Export receipt changed'
    receipt = json.loads(receipt_path.read_bytes())
    assert type(receipt.get('actual_exit')) is int and receipt['actual_exit'] == 0
    assert type(receipt.get('child_pid')) is int and receipt['child_pid'] > 0
    assert receipt.get('child_waited') is True and not receipt.get('error'), 'Successful awaited export required'
    argv = receipt['argv']
    assert isinstance(argv, list) and argv and Path(argv[0]).name in ('git', 'git.exe')
    assert argv.count('archive') == 1
    start = argv.index('archive')
    assert argv[start+1:start+4] == ['--format=tar', commit, '--'], 'Export commit/format mismatch'
    selected = argv[start+4:]
    assert selected and all(isinstance(name, str) and name and not name.startswith(('/', '-'))
                            and all(part not in ('', '.', '..') for part in name.split('/')) for name in selected)
    for name, checksum in files.items():
        assert isinstance(checksum, str) and re.fullmatch(r'[0-9a-f]{64}', checksum)
        assert any(name == path or name.startswith(path+'/') for path in selected), 'Input was not selected for export'
        assert digest(member(root, name).read_bytes()) == checksum, 'Exported source changed: '+name
    assert argv.count('-C') == 1, 'Exact original Git archive repository required'
    repository = Path(argv[argv.index('-C')+1]).resolve(strict=True)
    committed, git_receipt = git_blob_hashes(repository, commit, sorted(files))
    assert committed == files, 'Source or license hashes differ from the original commit'
    return commit, dict(kind='verified-git-archive-inventory', manifest_sha256=digest(manifest.read_bytes()),
                        export_receipt_sha256=receipt_ref['sha256'], verified_files=len(files),
                        export_inventory_sha256=export_ref['sha256'], git_object_verification=git_receipt,
                        auditor_files=data['auditor_files'])


def verified_source_revision(root, cache, manifest=None):
    assert Path(cache['CMAKE_HOME_DIRECTORY']).resolve(strict=True) == Path(root).resolve(strict=True), \
        'Native build source root differs from audited source'
    if manifest:
        return archive_source_revision(root, manifest)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    return revision, dict(kind='git-checkout', auditor_files=auditor_identity())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--contracts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--source-manifest', type=Path)
    args = parser.parse_args()
    if bool(args.source_root) != bool(args.source_manifest):
        parser.error('--source-root and --source-manifest must be supplied together')
    root = args.source_root.absolute() if args.source_root else ROOT
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
    revision, source_proof = verified_source_revision(root, cache, args.source_manifest)
    for key, value in {'VISPY_CPU_CONTRACTS_ONLY': 'OFF', 'VISPY_INPLACE': 'OFF',
                       'VISPY_VERIFY_DEPENDENCIES': 'ON', 'DAWN_ENABLE_VULKAN': 'ON',
                       'DAWN_ENABLE_METAL': 'OFF', 'DAWN_ENABLE_NULL': 'OFF',
                       'TINT_BUILD_SPV_READER': 'ON', 'DAWN_ENABLE_SPIRV_VALIDATION': 'ON'}.items():
        assert cache.get(key) == value, key
    package = source_package_hashes(root)
    notices = {'vispy/_licenses/' + p.name: digest(p.read_bytes())
               for p in (root / 'third_party/licenses').iterdir()
               if p.is_file() and p.suffix in ('.txt', '.md', '.json')}
    notices.update({'vispy/_licenses/' + name: digest((root / name).read_bytes())
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
        hashes = wheel_package_hashes(wheel, root=root)
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
            assert len(copies) == 2 and all(digest(archive.read(n)) == digest((root / name).read_bytes()) for n in copies)
    wheel_sha = digest(wheel.read_bytes())
    (args.output.parent / 'wheel-requirements.txt').write_text('vispy @ ' + wheel.as_uri() + ' --hash=sha256:' + wheel_sha + '\n')
    args.output.write_text(json.dumps({'status': 'PASS_LINUX_RENDERER_WHEEL_ARCHIVE', 'wheel': str(wheel),
        'wheel_sha256': wheel_sha, 'source_revision': revision, 'source_revision_proof': source_proof,
        'package_members': len(package), 'notice_members': len(notices), 'native_members': len(native),
        'native_origin': {name: {'raw_sha256': raw_hashes[name], 'wheel_stripped_sha256': hashes[name]} for name in native},
        'native_contracts': {'report': str((args.contracts / 'result.json').resolve()),
                             'sha256': digest((args.contracts / 'result.json').read_bytes()),
                             'tests': contracts['tests'], 'producer_admitted': False},
        'hardware_qualified': False, 'manylinux_qualified': False}, indent=2) + '\n')
    print('PASS_LINUX_RENDERER_WHEEL_ARCHIVE', wheel_sha, flush=True)


if __name__ == '__main__':
    main()
