# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare an isolated, hash-checked napari source tree for the Dawn fork.

Usage: python tools/prepare_napari_no_opengl.py --archive napari-0.9.2.tar.gz
       --output <new-directory>

This prepares source only; build/install it in a separate host environment.
It never modifies an existing environment or claims GUI qualification.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'compat/host-patches/provenance.json'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(archive, output, manifest_path=MANIFEST):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    archive, output = Path(archive), Path(output)
    patch = manifest_path.parent / manifest['patch']
    if sha256(archive) != manifest['source_sha256']:
        raise ValueError('napari source archive SHA256 does not match pinned upstream')
    if sha256(patch) != manifest['patch_sha256']:
        raise ValueError('napari patch SHA256 does not match provenance')
    if output.exists():
        raise FileExistsError('output must be a new directory: ' + str(output))
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        for member in members:
            parts = Path(member.name).parts
            if (not parts or parts[0] != manifest['archive_root'] or
                    '..' in parts or Path(member.name).is_absolute() or
                    not (member.isfile() or member.isdir())):
                raise ValueError('unexpected source archive member: ' + member.name)
        output.mkdir(parents=True)
        bundle.extractall(output, members=members, filter='data')
    source = output / manifest['archive_root']
    for name, hashes in manifest['files'].items():
        if sha256(source / name) != hashes['before_sha256']:
            raise ValueError('upstream file mismatch: ' + name)
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', str(patch.resolve())],
                   cwd=source, check=True)
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', str(patch.resolve())],
                   cwd=source, check=True)
    for name, hashes in manifest['files'].items():
        if sha256(source / name) != hashes['after_sha256']:
            raise ValueError('patched file mismatch: ' + name)
    # Keep the upstream license attached to the combined derivative.
    (source / 'LICENSE-AGPL').write_bytes((ROOT / 'LICENSE').read_bytes())
    (source / 'DAWN-PATCH-LICENSING.txt').write_text(
        'Original %s code: %s; see %s.\n' % (
            manifest['project'], manifest['upstream_license'],
            manifest.get('upstream_license_file', 'LICENSE')) +
        'Dawn integration changes: AGPL-3.0-only; see LICENSE-AGPL.\n'
        'Combined distribution: AGPL-3.0-only with original notices retained.\n',
        encoding='utf-8')
    (output / 'preparation.json').write_text(json.dumps({
        'source': str(source.resolve()), 'provenance': manifest,
        'status': 'prepared; build, native-load and GUI functional gates pending',
    }, indent=2) + '\n', encoding='utf-8')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.archive, args.output))


if __name__ == '__main__':
    main()
