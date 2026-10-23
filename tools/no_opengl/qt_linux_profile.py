"""Package exact source-built/relocated Linux Qt artifacts with provenance."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile
import zlib

from .dependencies import elf_image
from .policy import library_reason, is_gl_entrypoint


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verified(root, relative, expected):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != relative or '\\' in relative:
        raise ValueError('Noncanonical source-built profile path')
    source = (root / relative).resolve(strict=True)
    if not source.is_relative_to(root.resolve()):
        raise ValueError('Profile source leaves bundle')
    data = source.read_bytes()
    if sha(data) != expected:
        raise ValueError('Source-built profile bytes differ: ' + relative)
    return data


def build(manifest_path, bundle, receipts, inputs, output):
    manifest_path, bundle, receipts, inputs, output = map(Path, (manifest_path, bundle, receipts, inputs, output))
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data)
    if manifest['schema'] != 1 or manifest['profile'] != 'linux-pyqt6-source-no-opengl-v1' or manifest['platform'] != 'linux_x86_64':
        raise ValueError('Unknown Linux source-built Qt profile')
    output.mkdir(parents=True, exist_ok=False)
    proof = {'status': 'BUILT_SOURCE_PROFILE_UNQUALIFIED', 'manifest_sha256': sha(manifest_data), 'wheels': [],
             'builder': {'python': sys.version, 'zlib': zlib.ZLIB_RUNTIME_VERSION},
             'scope': 'Repeatable archive packaging of exact source-built/relocated bytes; native rebuild and runtime qualification are separate receipts.'}
    receipt_files = {item['file']: verified(receipts, item['file'], item['sha256']) for item in manifest['source_receipts']}
    runtime = next(item for item in manifest['wheels'] if item['name'] == 'pyqt6-qt6')
    qt_sonames = {PurePosixPath(item['member']).name for item in runtime['files'] if '/lib/' in item['member']}
    for item in manifest['wheels']:
        files, natives = {}, []
        members = [entry['member'] for entry in item['files']]
        if len(members) != len(set(members)):
            raise ValueError('Duplicate selected package member')
        for entry in item['files']:
            data = verified(bundle, entry['source'], entry['sha256'])
            if data.startswith(b'\x7fELF'):
                if not entry.get('native') or library_reason(entry['member']):
                    raise ValueError('Unreviewed or GL-specific native profile member')
                elf = elf_image(data)
                if any(library_reason(edge['name']) or any(is_gl_entrypoint(name) for name in edge['symbols']) for edge in elf['imports']):
                    raise ValueError('GL-specific ELF dependency')
                if any(edge['name'].startswith('libQt6') and edge['name'] not in qt_sonames for edge in elf['imports']):
                    raise ValueError('Selected Qt SONAME dependency omitted')
                if any(path and not path.startswith(('$ORIGIN', '${ORIGIN}')) for text in elf['runpaths'] for path in text.split(':')):
                    raise ValueError('Nonrelocatable native runtime search path')
                natives.append({'member': entry['member'], 'sha256': entry['sha256'],
                                'before_relocation_sha256': entry['before_relocation_sha256'], 'relocated': entry['relocated']})
            files[entry['member']] = data
        normalized = item['name'].replace('-', '_')
        info = normalized + '-' + item['version'] + '.dist-info'
        license_fields = []
        for notice in manifest['notices']:
            relative = notice['relative']
            # Validate destination paths independently from input paths.
            path = PurePosixPath(relative)
            if path.is_absolute() or '..' in path.parts or path.as_posix() != relative:
                raise ValueError('Noncanonical notice path')
            files[info + '/licenses/' + relative] = verified(bundle, notice['source'], notice['sha256'])
            if any(token in path.name.casefold() for token in ('license', 'copying', 'notice', 'author', 'attribution')):
                license_fields.append('License-File: ' + relative)
        metadata = ['Metadata-Version: 2.4', 'Name: ' + item['metadata_name'], 'Version: ' + item['version'],
                    'Summary: Source-built no-OpenGL Qt profile for VisPy Vulkan/XCB', 'Requires-Python: >=3.12,<3.13',
                    'License: See bundled original upstream notices', *license_fields,
                    *['Requires-Dist: ' + value for value in item['requires']], '',
                    'Exact selected source/build/relocation hashes and feature limits are recorded in the packaged profile manifest.', '']
        files[info + '/METADATA'] = '\n'.join(metadata).encode()
        files[info + '/WHEEL'] = ('Wheel-Version: 1.0\nGenerator: vispy-source-qt-profile\nRoot-Is-Purelib: false\nTag: ' + item['tag'] + '\n').encode()
        files[info + '/source-profile.json'] = manifest_data
        for name, data in receipt_files.items():
            files[info + '/provenance/' + name] = data
        record = info + '/RECORD'
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        for name, data in sorted(files.items()):
            writer.writerow([name, 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(), len(data)])
        writer.writerow([record, '', ''])
        files[record] = stream.getvalue().encode()
        target = output / (normalized + '-' + item['version'] + '-' + item['tag'] + '.whl')
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(files.items()):
                zi = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                zi.create_system = 3
                zi.external_attr = 0o100644 << 16
                archive.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        proof['wheels'].append({'name': item['name'], 'version': item['version'], 'file': str(target.resolve()),
                                'sha256': sha(target.read_bytes()), 'members': sorted(files), 'preserved_native': natives,
                                'notice_count': len(manifest['notices'])})
    for item in manifest['support_wheels']:
        source = inputs / item['filename']
        if sha(source.read_bytes()) != item['sha256']:
            raise ValueError('Pinned SIP support wheel differs')
        with zipfile.ZipFile(source) as archive:
            if sha(archive.read(item['native_member'])) != item['native_sha256']:
                raise ValueError('SIP support native byte provenance differs')
        target = output / source.name
        shutil.copyfile(source, target)
        proof['wheels'].append({'name': item['name'], 'version': item['version'], 'file': str(target.resolve()),
                                'sha256': item['sha256'], 'unchanged_support_wheel': True})
    requirements = '# Strict Linux CPython 3.12 x86_64 source-built Qt profile; --no-index --find-links <bundle> --require-hashes.\n'
    requirements += '\n'.join(item['name'] + '==' + item['version'] + ' --hash=sha256:' + item['sha256'] for item in proof['wheels']) + '\n'
    (output / 'requirements.txt').write_text(requirements)
    (output / 'apt-install-pins.txt').write_text('\n'.join(manifest['runtime_apt_versions']['apt_install_pins']) + '\n')
    (output / 'profile-provenance.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('manifest', 'bundle', 'receipts', 'inputs', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    print(build(args.manifest, args.bundle, args.receipts, args.inputs, args.output)['status'])
