# SPDX-License-Identifier: AGPL-3.0-only
"""Package a reviewed, byte-identical oneTBB core runtime and original license."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from .dependencies import pe_image
from .policy import library_reason


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(manifest_path, source, output):
    manifest_path, source, output = map(Path, (manifest_path, source, output))
    manifest = json.loads(manifest_path.read_text())
    if manifest['schema'] != 1 or manifest['profile'] != 'windows-numba-tbb-core-v1':
        raise ValueError('Unknown TBB core profile')
    if digest(source.read_bytes()) != manifest['input']['sha256']:
        raise ValueError('Pinned original TBB wheel differs')
    bootstrap = Path(__file__).with_name('tbb_runtime_bootstrap.py').read_bytes()
    if digest(bootstrap) != manifest['bootstrap_sha256']:
        raise ValueError('Runtime directory registration source differs')
    output.mkdir(parents=True, exist_ok=False)
    info = 'vispy_tbb_runtime-' + manifest['version'] + '.dist-info'
    files = {'_vispy_tbb_runtime.py': bootstrap, 'vispy_tbb_runtime.pth': b'import _vispy_tbb_runtime\n'}
    with zipfile.ZipFile(source) as archive:
        core = archive.read(manifest['core']['source'])
        if digest(core) != manifest['core']['sha256']:
            raise ValueError('TBB core native bytes differ')
        image = pe_image(core)
        exported = {item['name'] for item in image['exports']}
        if not set(manifest['numba']['required_symbols']) <= exported:
            raise ValueError('Numba ABI symbols absent from TBB core')
        if any(library_reason(item['name']) for item in image['imports']):
            raise ValueError('GL runtime dependency in CPU runtime')
        files['_vispy_tbb/bin/tbb12.dll'] = core
        for item in manifest['original_notices']:
            data = archive.read(item['source'])
            if digest(data) != item['sha256']:
                raise ValueError('Original TBB notice bytes differ')
            files[info + '/licenses/' + Path(item['source']).name] = data
        original_metadata = next(name for name in archive.namelist() if name.endswith('.dist-info/METADATA'))
        files[info + '/provenance/original-tbb-METADATA'] = archive.read(original_metadata)
    files[info + '/licenses/LICENSE-AGPL'] = (Path(__file__).resolve().parents[2] / 'LICENSE').read_bytes()
    files[info + '/source-profile.json'] = manifest_path.read_bytes()
    files[info + '/METADATA'] = ('Metadata-Version: 2.4\nName: vispy-tbb-runtime\nVersion: ' + manifest['version']
                               + '\nSummary: Selected CPU runtime for the pinned Numba ABI\nRequires-Python: >=3.12,<3.13\n'
                                 'License: Original Intel Simplified Software License for the unchanged runtime; AGPL-3.0-only for the directory-registration code\n'
                                 'License-File: LICENSE.txt\nLicense-File: LICENSE-AGPL\n\n'
                                 'Core DLL is unchanged. Optional HWLOC binding and allocator plugins are not selected.\n').encode()
    files[info + '/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: vispy-core-tbb-profile\nRoot-Is-Purelib: false\nTag: py3-none-win_amd64\n'
    record = info + '/RECORD'
    text = io.StringIO(newline='')
    writer = csv.writer(text, lineterminator='\n')
    for name, data in sorted(files.items()):
        writer.writerow([name, 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(), len(data)])
    writer.writerow([record, '', ''])
    files[record] = text.getvalue().encode()
    target = output / ('vispy_tbb_runtime-' + manifest['version'] + '-py3-none-win_amd64.whl')
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    proof = {'status': 'BUILT_TBB_PROFILE_UNQUALIFIED', 'file': str(target.resolve()), 'sha256': digest(target.read_bytes()),
             'native_sha256': manifest['core']['sha256'], 'native_unchanged': True,
             'original_runtime_license': manifest['runtime_license'], 'directory_registration_license': 'AGPL-3.0-only'}
    (output / 'requirements.txt').write_text('vispy-tbb-runtime==' + manifest['version'] + ' --hash=sha256:' + proof['sha256'] + '\n', newline='\n')
    (output / 'profile-provenance.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('manifest', 'source', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    print(build(args.manifest, args.source, args.output)['status'])
