# SPDX-License-Identifier: AGPL-3.0-only
"""Assemble changed pure members around audited native bytes, without a build.

The caller supplies frozen original archive inputs from the retained producer
record. Passing these byte audits does not approve that producer, a source
change, or the resulting installed artifact.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
from pathlib import Path
import zipfile

try:
    from . import qualification_artifact as archive_audit
except ImportError:
    import qualification_artifact as archive_audit


def repackage(data, replacements, **original_inputs):
    """Return wheel bytes and an audit; preserve every non-replaced payload.

    Shipping membership and metadata changes need a separate packaging decision.
    Here only existing pure members may change; the shipping manifest itself,
    native outputs, notices, metadata and tags remain byte-identical.
    """
    original = archive_audit.audit_archive(data, **original_inputs)
    pure = original_inputs['pure_hashes']
    allowed = set(pure) - {archive_audit.runtime_package.MEMBER}
    if not set(replacements) <= allowed:
        raise ValueError('Only existing pure source members may be replaced')
    if any(type(value) is not bytes for value in replacements.values()):
        raise ValueError('Replacement source members must be bytes')

    changed = {name: value for name, value in replacements.items()
               if archive_audit.sha(value) != pure[name]}
    if not changed:
        return data, dict(status='UNCHANGED_ORIGINAL_WHEEL_REUSED', changed_members=[],
                          original_sha256=archive_audit.sha(data),
                          wheel_sha256=archive_audit.sha(data), artifact_admitted=False,
                          audit=original)

    record_name = archive_audit.DIST + '/RECORD'
    result = io.BytesIO()
    rows = []
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(result, 'w') as target:
        for info in source.infolist():
            if info.filename == record_name:
                record_info = info
                continue
            payload = changed.get(info.filename, source.read(info.filename))
            target.writestr(info, payload)
            if not info.is_dir():
                digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b'=')
                rows.append([info.filename, 'sha256=' + digest.decode('ascii'), str(len(payload))])
        rows.append([record_name, '', ''])
        record = io.StringIO(newline='')
        csv.writer(record).writerows(rows)
        target.writestr(record_info, record.getvalue().encode('utf-8'))

    output = result.getvalue()
    inputs = dict(original_inputs, pure_hashes={
        **pure, **{name: archive_audit.sha(value) for name, value in changed.items()}})
    audited = archive_audit.audit_archive(output, **inputs)
    return output, dict(status='ASSEMBLED_PURE_SOURCE_CHANGE_NOT_ADMITTED',
                        changed_members=sorted(changed), original_sha256=archive_audit.sha(data),
                        wheel_sha256=archive_audit.sha(output), artifact_admitted=False,
                        native_rebuilt=False, audit=audited)


def repackage_from_source(data, source, original_sources, native_hashes, *, platform, suffix, tag):
    """Keep original metadata/manifest/notices while updating declared sources.

    Native production validation belongs to the caller. These checks do not
    replace it: they join an original source map to an exact original archive
    and the current pure sources before assembling a successor.
    """
    source = Path(source)
    manifest = archive_audit.runtime_package.load_manifest(source)
    current = archive_audit.runtime_package.source_package_hashes(source)
    origins = {member: ('compat/runtime-package.json' if member == archive_audit.runtime_package.MEMBER
                        else 'src/' + member) for member in current}
    metadata = {'README.md', 'pyproject.toml', 'compat/runtime-package.json'}
    metadata.update(name if name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md')
                    else 'third_party/licenses/' + name for name in manifest['notice_files'])
    for name in sorted(metadata):
        if original_sources.get(name) != archive_audit.sha((source / name).read_bytes()):
            raise ValueError('Changed or missing original package metadata/notice input: ' + name)
    if any(name not in original_sources for name in origins.values()):
        raise ValueError('Original source map lacks a declared package member')
    original = {member: original_sources[name] for member, name in origins.items()}
    replacements = {member: (source / origins[member]).read_bytes() for member in current
                    if current[member] != original[member]}
    result, report = repackage(data, replacements,
        manifest_data=(source / 'compat/runtime-package.json').read_bytes(), pure_hashes=original,
        notices=archive_audit.source_notices(source),
        distribution_licenses=archive_audit.source_distribution_licenses(source),
        native_hashes=native_hashes, platform=platform, suffix=suffix, tag=tag)
    if archive_audit.runtime_package.source_package_hashes(source) != current:
        raise ValueError('Source package changed during archive assembly')
    report.update(current_source_hashes=current, original_source_hashes=original,
                  unchanged_metadata_inputs={name: original_sources[name] for name in sorted(metadata)})
    return result, report
