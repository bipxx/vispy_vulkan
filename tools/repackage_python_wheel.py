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
