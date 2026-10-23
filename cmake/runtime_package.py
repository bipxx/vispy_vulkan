"""Exact candidate-wheel shipping contract, independent of Git availability."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import sysconfig
import zipfile

MEMBER = 'vispy/_runtime_package.json'


def validate_manifest(manifest):
    if manifest.get('schema') != 1 or manifest.get('profile') != 'dawn-no-opengl-runtime':
        raise ValueError('Unknown runtime shipping contract')
    files = manifest['files']
    excluded = manifest['excluded_files']
    if files != sorted(set(files)) or set(files) & set(excluded):
        raise ValueError('Duplicate, unordered or overlapping shipping entries')
    for name in [*files, *excluded, *manifest['notice_files']]:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix() != name or '\\' in name:
            raise ValueError('Noncanonical shipping path: ' + name)
    if not set(manifest['compatibility_aliases']) <= set(files):
        raise ValueError('Compatibility facade aliases must remain shipped')
    if manifest['generated_manifest_member'] != MEMBER:
        raise ValueError('Runtime manifest member differs')
    return manifest


def load_manifest(root):
    return validate_manifest(json.loads((Path(root) / 'compat/runtime-package.json').read_text(encoding='utf-8')))


def source_package_hashes(root):
    root = Path(root)
    manifest = load_manifest(root)
    result = {'vispy/' + name: hashlib.sha256((root / 'src/vispy' / name).read_bytes()).hexdigest()
              for name in manifest['files']}
    result[MEMBER] = hashlib.sha256((root / 'compat/runtime-package.json').read_bytes()).hexdigest()
    return result


def expected_members(manifest, *, suffix=None, platform=None):
    manifest = validate_manifest(manifest)
    suffix = sysconfig.get_config_var('EXT_SUFFIX') if suffix is None else suffix
    platform = sys.platform if platform is None else platform
    result = {'vispy/' + name for name in manifest['files']} | {MEMBER}
    result |= {'vispy/_licenses/' + name for name in manifest['notice_files']}
    result |= {'vispy/_dawn' + suffix, 'vispy/visuals/text/_sdf_cpu' + suffix}
    if platform != 'darwin':
        result |= {'vispy/VkLayer_vispy_submit' + ('.dll' if platform == 'win32' else '.so'),
                   'vispy/VkLayer_vispy_submit.json'}
    return result


def wheel_package_hashes(wheel, *, root=None, suffix=None, platform=None):
    """Check complete package membership, then return exact archived hashes.

    Source-aware archive audits additionally compare the manifest and every
    shipped pure file against current source bytes. Installed consumers use the
    already source-audited wheel's contract and compare each installed member.
    """
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate wheel archive member')
        manifest_data = archive.read(MEMBER)
        manifest = validate_manifest(json.loads(manifest_data))
        actual = {name for name in names if name.startswith('vispy/') and not name.endswith('/')}
        if actual != expected_members(manifest, suffix=suffix, platform=platform):
            raise ValueError('Wheel differs from explicit shipping contract: missing=' +
                             str(sorted(expected_members(manifest, suffix=suffix, platform=platform) - actual)) +
                             ' unexpected=' + str(sorted(actual - expected_members(manifest, suffix=suffix, platform=platform))))
        hashes = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in actual}
        if root is not None:
            source = Path(root) / 'compat/runtime-package.json'
            if source.read_bytes() != manifest_data:
                raise ValueError('Wheel shipping contract differs from source')
            for name, digest in source_package_hashes(root).items():
                if hashes[name] != digest:
                    raise ValueError('Shipped source bytes differ: ' + name)
        return hashes
