"""Reproducible selected Qt/PyQt wheels from pinned original wheel inputs.

Native bytes and original notices are unchanged. This is a package profile,
not a Qt source rebuild and not proof of runtime absence (notably NVIDIA WSI).
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import zlib
import zipfile

from .dependencies import pe_image
from .policy import is_gl_entrypoint, library_reason


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(manifest_path, inputs, output):
    manifest_path, inputs, output = Path(manifest_path), Path(inputs), Path(output)
    manifest = json.loads(manifest_path.read_text())
    if manifest['schema'] != 1 or manifest['platform'] != 'win_amd64':
        raise ValueError('Unknown Qt package profile')
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'BUILT_PROFILE_UNQUALIFIED', 'profile': manifest['profile'],
              'manifest_sha256': sha(manifest_path.read_bytes()), 'wheels': [],
              'builder': {'python': sys.version, 'zlib': zlib.ZLIB_RUNTIME_VERSION},
              'scope': 'Exact selected native bytes/notices; functional/native/runtime dependency qualification still required.'}
    runtime = next(item for item in manifest['wheels'] if item['name'] == 'pyqt6-qt6')
    selected_qt_dlls = {PurePosixPath(name).name.casefold() for name in runtime['selected_members'] if '/bin/Qt6' in name}
    for item in manifest['wheels']:
        source = inputs / item['input_filename']
        if sha(source.read_bytes()) != item['input_sha256']:
            raise ValueError('Pinned input wheel differs: ' + str(source))
        selected = item['selected_members']
        if selected != sorted(set(selected)):
            raise ValueError('Profile membership is not canonical')
        files, natives, notices = {}, [], []
        with zipfile.ZipFile(source) as archive:
            original = archive.namelist()
            if len(original) != len(set(original)) or not set(selected) <= set(original):
                raise ValueError('Unknown/duplicate source wheel member')
            all_notices = {name for name in original if any(word in name.casefold() for word in ('license', 'copying', 'notice')) and not name.endswith('/')}
            if set(item['original_notice_members']) != all_notices or not all_notices <= set(selected):
                raise ValueError('Original notices are missing or changed in the profile')
            for name in selected:
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or path.as_posix() != name or '\\' in name:
                    raise ValueError('Noncanonical profile member')
                data = archive.read(name)
                destination = name
                if '.dist-info/' in name:
                    head, tail = name.split('/', 1)
                    destination = head.replace('-' + item['input_version'] + '.dist-info', '-' + item['output_version'] + '.dist-info') + '/' + tail
                if name.endswith('/METADATA'):
                    text = data.decode().replace('\r\n', '\n')
                    text, count = re.subn(r'^Version: [^\n]*', 'Version: ' + item['output_version'], text, count=1, flags=re.MULTILINE)
                    if count != 1:
                        raise ValueError('Missing original Version metadata')
                    if item['name'] == 'pyqt6':
                        text, count = re.subn(r'^Requires-Dist: PyQt6-Qt6[^\n]*',
                                             'Requires-Dist: PyQt6-Qt6==' + runtime['output_version'], text, count=1,
                                             flags=re.MULTILINE | re.IGNORECASE)
                        if count != 1:
                            raise ValueError('Missing original Qt runtime dependency')
                    data = text.encode()
                if name.endswith(('.dll', '.pyd')):
                    if library_reason(name):
                        raise ValueError('GL-specific native member in selected profile: ' + name)
                    image = pe_image(data)
                    for dependency in image['imports']:
                        if library_reason(dependency['name']) or any(is_gl_entrypoint(symbol) for symbol in dependency['symbols']):
                            raise ValueError('Selected member has GL-specific import: ' + name)
                        if dependency['name'].casefold().startswith('qt6') and dependency['name'].casefold() not in selected_qt_dlls:
                            raise ValueError('Selected Qt native dependency omitted: ' + name + ' -> ' + dependency['name'])
                    natives.append({'source': name, 'member': destination, 'sha256': sha(data), 'unchanged': data == archive.read(name)})
                if name in all_notices:
                    notices.append({'source': name, 'member': destination, 'sha256': sha(data)})
                files[destination] = data
            profile_member = 'PyQt6/_vispy_binding_profile.json' if item['name'] == 'pyqt6' else 'PyQt6/Qt6/_vispy_runtime_profile.json'
            files[profile_member] = json.dumps(manifest, sort_keys=True, indent=2).encode() + b'\n'
            metadata = next(name for name in files if name.endswith('.dist-info/METADATA'))
            record = metadata.rsplit('/', 1)[0] + '/RECORD'
            stream = io.StringIO(newline='')
            writer = csv.writer(stream, lineterminator='\n')
            for name, data in sorted(files.items()):
                writer.writerow([name, 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(), len(data)])
            writer.writerow([record, '', ''])
            files[record] = stream.getvalue().encode()
            filename = item['input_filename'].replace('-' + item['input_version'] + '-', '-' + item['output_version'] + '-', 1)
            target = output / filename
            with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as wheel:
                for name, data in sorted(files.items()):
                    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    wheel.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            report['wheels'].append({'file': str(target.resolve()), 'sha256': sha(target.read_bytes()),
                                     'name': item['name'], 'version': item['output_version'],
                                     'input_sha256': item['input_sha256'], 'members': sorted(files),
                                     'omitted_source_members': sorted(set(original) - set(selected)),
                                     'preserved_native': natives, 'preserved_notices': notices})
    for item in manifest.get('support_wheels', []):
        source = inputs / item['filename']
        if sha(source.read_bytes()) != item['sha256']:
            raise ValueError('Pinned support wheel differs: ' + str(source))
        target = output / item['filename']
        shutil.copyfile(source, target)
        report['wheels'].append({'name': item['name'], 'version': item['version'],
                                 'file': str(target.resolve()), 'sha256': item['sha256'],
                                 'unchanged_support_wheel': True})
    requirements = '# Strict Windows CPython 3.12 x64 Qt profile; use --no-index --find-links <bundle> --require-hashes.\n'
    requirements += '\n'.join(item['name'] + '==' + item['version'] + ' --hash=sha256:' + item['sha256']
                              for item in report['wheels']) + '\n'
    (output / 'requirements.txt').write_text(requirements, newline='\n')
    (output / 'profile-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(build(args.manifest, args.inputs, args.output)['status'])
