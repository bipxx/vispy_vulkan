# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only archive and vendor SDK prerequisites; never artifact admission."""
from __future__ import annotations

import argparse
import ast
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import struct
import zipfile

try:
    from .compatibility_candidate import scope_digest, validate_candidate
    from .compatibility_inventory import ROOT, InventoryError, check, file_ref, local_file, read_json, shape, unique_by
    from .no_opengl.dependencies import pe_image, elf_image
except ImportError:
    from compatibility_candidate import scope_digest, validate_candidate
    from compatibility_inventory import ROOT, InventoryError, check, file_ref, local_file, read_json, shape, unique_by
    from no_opengl.dependencies import pe_image, elf_image

def local_module(name):
    spec = importlib.util.spec_from_file_location('qualification_' + name, ROOT / 'cmake' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native_sdk = local_module('native_sdk')
runtime_package = local_module('runtime_package')

POLICY = 'compat/qualification-producers.json'
SCHEMA = 'compat/qualification-artifact.schema.json'
SDK_SHA = '7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2'
COMPILER_SHA = '824f0234b667847befd7e3ff258822bfe557b540959ff042caaec6844b709a11'
DIST = 'vispy-0.17.0+vulkan.1.dist-info'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_shape(record, kind, root=ROOT):
    definitions = read_json(Path(root) / SCHEMA)['$defs']
    shape(record, definitions[kind], definitions)


def validate_policy(root=ROOT):
    policy = read_json(Path(root) / POLICY)
    validate_shape(policy, 'policy', root)
    check(policy['windows_sdk_sha256'] == SDK_SHA and policy['windows_compiler_sha256'] == COMPILER_SHA,
          'vendor SDK trust input changed; producer review required')
    return policy


def retained_file(root, reference):
    path = file_ref(root, reference)
    check(not path.is_relative_to((Path(root) / 'build/work').resolve()),
          'archive/producer evidence cannot depend on managed scratch')
    return path


def source_notices(root):
    root = Path(root)
    manifest = runtime_package.load_manifest(root)
    result = {}
    for name in manifest['notice_files']:
        path = root / name if name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md') else root / 'third_party/licenses' / name
        result['vispy/_licenses/' + name] = path.read_bytes()
    return result


def source_distribution_licenses(root):
    root = Path(root)
    text = (root / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(r'^license-files = (\[.*\])$', text, re.M)
    check(match is not None, 'source license-file contract missing')
    result = {}
    for pattern in ast.literal_eval(match[1]):
        path = PurePosixPath(pattern)
        check(not path.is_absolute() and '..' not in path.parts and '\\' not in pattern, 'invalid license-file pattern')
        files = sorted(p for p in root.glob(pattern) if p.is_file())
        check(files, 'source license pattern matches no files')
        for file in files:
            result[DIST + '/licenses/' + file.relative_to(root).as_posix()] = file.read_bytes()
    check(all(DIST + '/licenses/' + name in result for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md')),
          'original license copies missing from distribution')
    return result


def check_record(archive, names):
    rows = list(csv.reader(io.StringIO(archive.read(DIST + '/RECORD').decode('utf-8'))))
    check(all(len(row) == 3 for row in rows), 'malformed wheel RECORD row')
    indexed = unique_by(rows, lambda row: row[0], 'wheel RECORD member')
    check(set(indexed) == names, 'wheel RECORD inventory differs from archive')
    for name, row in indexed.items():
        if name == DIST + '/RECORD':
            check(row[1:] == ['', ''], 'wheel RECORD must not hash itself')
            continue
        data = archive.read(name)
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode('ascii')
        check(row[1] == 'sha256=' + digest and row[2] == str(len(data)), 'wheel RECORD hash/size differs: ' + name)


def audit_archive(data, *, manifest_data, pure_hashes, notices, distribution_licenses,
                  native_hashes, suffix, platform, tag):
    """Pure archive join. Expected inputs come from frozen sources/output files.

    In-memory synthetic tests use this function without fabricating producer or
    installed receipts. Native hash equality alone does not prove a build.
    """
    manifest = runtime_package.validate_manifest(json.loads(manifest_data))
    check(platform in ('win32', 'linux'), 'archive architecture policy is not implemented for this platform')
    expected_pure = {'vispy/' + name for name in manifest['files']} | {runtime_package.MEMBER}
    check(set(pure_hashes) == expected_pure and pure_hashes[runtime_package.MEMBER] == sha(manifest_data),
          'incomplete frozen source member hashes')
    expected_notices = {'vispy/_licenses/' + name for name in manifest['notice_files']}
    check(set(notices) == expected_notices, 'incomplete original notice inputs')
    for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md'):
        check(DIST + '/licenses/' + name in distribution_licenses
              and distribution_licenses[DIST + '/licenses/' + name] == notices.get('vispy/_licenses/' + name),
              'missing/different original distribution license copies')
    expected_native = runtime_package.expected_members(manifest, suffix=suffix, platform=platform) - expected_pure - expected_notices
    check(set(native_hashes) == expected_native, 'incomplete native output inventory')
    hashes = runtime_package.wheel_package_hashes(io.BytesIO(data), suffix=suffix, platform=platform)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set()
        for info in archive.infolist():
            name = info.filename.rstrip('/')
            path = PurePosixPath(name)
            check(not path.is_absolute() and '..' not in path.parts and '\\' not in name
                  and path.as_posix() == name, 'noncanonical wheel member')
            if not info.is_dir():
                names.add(info.filename)
        expected = set(hashes) | set(distribution_licenses) | {DIST + '/' + name for name in ('METADATA', 'WHEEL', 'RECORD')}
        check(names == expected, 'distribution archive has missing/unexpected members')
        check(archive.read(runtime_package.MEMBER) == manifest_data, 'wheel shipping contract differs from source')
        for name, expected_hash in {**pure_hashes, **native_hashes}.items():
            check(hashes[name] == expected_hash, 'wheel source/native output bytes differ: ' + name)
        for name in native_hashes:
            if name.endswith('.json'):
                continue
            try:
                image = pe_image(archive.read(name)) if platform == 'win32' else elf_image(archive.read(name))
            except (ValueError, struct.error, IndexError) as error:
                raise InventoryError('invalid native archive image: ' + name) from error
            check(image['pointer_bytes'] == 8 and image['machine'] == (0x8664 if platform == 'win32' else 62),
                  'native archive architecture differs from profile: ' + name)
        for name, expected_bytes in {**notices, **distribution_licenses}.items():
            check(archive.read(name) == expected_bytes, 'original license/notice bytes differ: ' + name)
        metadata = BytesParser().parsebytes(archive.read(DIST + '/METADATA'))
        for field, value in {'Name': 'vispy', 'Version': '0.17.0+vulkan.1', 'License-Expression': 'AGPL-3.0-only',
                             'Description-Content-Type': 'text/markdown'}.items():
            check(metadata.get_all(field) == [value], 'wrong/duplicate wheel metadata: ' + field)
        wheel = BytesParser().parsebytes(archive.read(DIST + '/WHEEL'))
        for field, value in {'Wheel-Version': '1.0', 'Root-Is-Purelib': 'false', 'Tag': tag}.items():
            check(wheel.get_all(field) == [value], 'wrong/duplicate wheel ABI metadata: ' + field)
        check_record(archive, names)
    return {'status': 'PASS_EXACT_ARCHIVE_PREREQUISITE', 'wheel_sha256': sha(data),
            'package_hashes': hashes, 'distribution_members': len(names),
            'producer_admitted': False, 'artifact_admitted': False, 'installed_origin_verified': False}


def validate_archive(record, root=ROOT):
    root = Path(root)
    validate_shape(record, 'archive', root)
    validate_policy(root)
    candidate = read_json(local_file(root, record['candidate']['path']))
    validate_candidate(candidate, root)
    check(scope_digest(candidate) == record['candidate']['scope_sha256'], 'archive candidate scope changed')
    profiles = {p['id']: p for p in candidate['profiles']}
    check(record['profile'] in profiles, 'archive profile is not selected')
    observation = read_json(file_ref(root, profiles[record['profile']]['observation']))
    check(observation['architecture'] == 'x86_64', 'archive profile architecture not yet supported')
    abi = observation['python_abi']
    check(re.fullmatch(r'cp[0-9]{2,3}', abi) is not None, 'unsupported archive Python ABI')
    windows = observation['kind'] == 'windows-gpu'
    check(windows or observation['kind'] == 'wsl-software', 'archive profile platform not yet supported')
    platform = 'win32' if windows else 'linux'
    platform_tag = 'win_amd64' if windows else 'linux_x86_64'
    suffix = '.' + abi + '-win_amd64.pyd' if windows else '.cpython-' + abi[2:] + '-x86_64-linux-gnu.so'
    wheel = retained_file(root, record['wheel'])
    check(wheel.name == 'vispy-0.17.0+vulkan.1-' + abi + '-' + abi + '-' + platform_tag + '.whl', 'wrong wheel filename/profile ABI')
    outputs = unique_by(record['native_outputs'], lambda r: r['member'], 'native output member')
    native_hashes = {name: sha(retained_file(root, ref['file']).read_bytes()) for name, ref in outputs.items()}
    result = audit_archive(wheel.read_bytes(), manifest_data=(root / 'compat/runtime-package.json').read_bytes(),
                           pure_hashes=runtime_package.source_package_hashes(root), notices=source_notices(root),
                           distribution_licenses=source_distribution_licenses(root), native_hashes=native_hashes,
                           suffix=suffix, platform=platform, tag=abi + '-' + abi + '-' + platform_tag)
    return {**result, 'profile': record['profile'], 'source_commit': candidate['product_source_commit'],
            'missing': ['native-leaf-producer-admission', 'installed-functional-and-absence-gates',
                        'terminal-retention', 'promotion-basis-review']}


def validate_sdk(record, root=ROOT):
    root = Path(root)
    validate_shape(record, 'sdk', root)
    policy = validate_policy(root)
    check(record['manifest']['sha256'] == policy['windows_sdk_sha256'], 'SDK is not an allowed vendor origin')
    manifest = retained_file(root, record['manifest'])
    check(manifest.name == 'manifest.json', 'wrong SDK manifest member')
    lock = retained_file(root, record['dependency_lock'])
    consumer = read_json(retained_file(root, record['consumer']))
    check(set(consumer) == set(native_sdk.SETTINGS) | {'compiler'}, 'incomplete/unknown SDK consumer settings')
    result = native_sdk.verify(manifest.parent, SDK_SHA, lock, consumer)
    check(result['compiler_sha256'] == COMPILER_SHA, 'unapproved vendor compiler')
    check(result['compiler_policy_verifier_sha256'] == sha((root / 'cmake/native_sdk.py').read_bytes()),
          'SDK compiler policy verifier changed')
    return {'status': 'PASS_VENDOR_SDK_REUSE_ONLY', 'sdk_sha256': SDK_SHA,
            'native_leaf_admitted': False, 'artifact_admitted': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--archive', type=Path)
    choice.add_argument('--sdk', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.archive:
            result = validate_archive(read_json(args.archive), args.root)
        elif args.sdk:
            result = validate_sdk(read_json(args.sdk), args.root)
        else:
            result = {'status': 'VALID_PRODUCER_PREREQUISITE_POLICY', 'policy': validate_policy(args.root),
                      'native_leaf_admitted': False, 'artifact_admitted': False}
    except (InventoryError, native_sdk.SDKError, OSError, ValueError, KeyError, TypeError, IndexError,
            zipfile.BadZipFile, UnicodeError, csv.Error) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
