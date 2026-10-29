# SPDX-License-Identifier: AGPL-3.0-only
"""List where this working tree differs from the published main branch; run it before each publication.

The working tree is not a git repository. PRs are published file by file from a separate clone, so an edit that never
reaches a PR stays local and drifts. This compares every file of the clone's main (git ls-tree at --ref) with this
working tree, byte for byte, as git blobs; main checks files out byte-preserving (.gitattributes: * -text). It lists:
- changed: both have the file and the bytes differ, marked when only CR/LF differ;
- missing: main has the file and this tree does not;
- local only: a file under one of main's top-level directories that main lacks and the clone's .gitignore does not
  ignore.
third_party/ is left to cmake/verify_dependencies.py. A difference is explained when the publication expects it
(--expect, its own files or directories) or KNOWN records why it stays local; anything else exits 1.
Usage (repository root): publication_drift.py <clone> [--ref origin/main] [--expect PATH ...] [--json OUT]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = ('third_party/',)
KNOWN = {  # a path, or a directory ending in /
    'docs/superpowers/plans/2026-10-10-vispy-vulkan-next-batch-plan.md':
        'the local 1.17 MB agent-history file; its published copy keeps its earlier body byte-exact and is never '
        'overwritten by it (consolidated plan, plan index)',
    'docs/upstream-drafts/': 'W12 upstream drafts stay local until the user approves posting (user, 2026-10-28)',
    'tools/wheel_index.py': 'W11 index tooling, prepared locally; it is published with W11, on approval (D2)',
    'tests/contract/test_wheel_index.py': 'the CPU test of tools/wheel_index.py, published with it (W11)',
}


def matches(path, items):
    return next((item for item in items if path == item or item.endswith('/') and path.startswith(item)), None)


def git(clone, *arguments, stdin=None):
    result = subprocess.run(['git', '-C', str(clone), *arguments], input=stdin, capture_output=True, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError('git %s failed: %s' % (' '.join(arguments), result.stderr.decode(errors='replace')))
    return result.stdout


def blob_id(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def published(clone, ref):
    """Map each regular file of ``ref`` to its blob id."""
    files = {}
    for entry in git(clone, 'ls-tree', '-r', '-z', '--full-tree', ref).split(b'\0'):
        if entry:
            meta, path = entry.split(b'\t', 1)
            mode, kind, oid = meta.split()
            if kind == b'blob' and mode != b'120000':
                files[path.decode('utf-8', 'surrogateescape')] = oid.decode()
    return files


def local_files(root, directories):
    for directory in directories:
        for base, names, files in os.walk(root / directory):
            names[:] = [name for name in names if name != '__pycache__']
            for name in files:
                yield (Path(base) / name).relative_to(root).as_posix()


def drift(root, clone, ref='origin/main', expect=(), known=None):
    known = KNOWN if known is None else known
    main = {path: oid for path, oid in published(clone, ref).items() if not path.startswith(EXCLUDED)}
    changed, missing = [], []
    for path, oid in sorted(main.items()):
        local = root / path
        if not local.is_file():
            missing.append(path)
            continue
        data = local.read_bytes()
        if blob_id(data) != oid:
            original = git(clone, 'cat-file', 'blob', oid)
            changed.append({'path': path, 'line_endings_only':
                            data.replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n')})
    directories = sorted({path.split('/')[0] for path in main if '/' in path})
    candidates = sorted(set(local_files(root, directories)) - set(main))
    ignored = set(git(clone, 'check-ignore', '--no-index', '--stdin', '-z',
                      stdin=b'\0'.join(path.encode('utf-8', 'surrogateescape') for path in candidates)
                      ).decode('utf-8', 'surrogateescape').split('\0')) - {''}
    local_only = [path for path in candidates if path not in ignored]
    differing = [item['path'] for item in changed] + missing + local_only
    return {'ref': ref, 'commit': git(clone, 'rev-parse', ref).decode().strip(), 'changed': changed,
            'missing': missing, 'local_only': local_only,
            'known': {path: known[matches(path, known)] for path in differing if matches(path, known)},
            'unexplained': [path for path in differing if not matches(path, known) and not matches(path, expect)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('clone', type=Path)
    parser.add_argument('--ref', default='origin/main')
    parser.add_argument('--expect', nargs='*', default=(), help='files or directories/ the publication changes')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    options = parser.parse_args(argv)
    record = drift(options.root, options.clone, options.ref, [path.replace('\\', '/') for path in options.expect])
    if options.json:
        options.json.write_bytes((json.dumps(record, indent=2) + '\n').encode())
    print('%s at %s' % (record['ref'], record['commit']))
    for item in record['changed']:
        print('changed     %s%s' % (item['path'], '  (line endings only)' if item['line_endings_only'] else ''))
    for path in record['missing']:
        print('missing     ' + path)
    for path in record['local_only']:
        print('local only  ' + path)
    for path, reason in record['known'].items():
        print('known       %s: %s' % (path, reason))
    print('%d unexplained' % len(record['unexplained']))
    return 1 if record['unexplained'] else 0


if __name__ == '__main__':
    sys.exit(main())
