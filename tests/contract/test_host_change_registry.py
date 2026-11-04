# SPDX-License-Identifier: AGPL-3.0-only
"""D28: every host patch is registered with its upstream route, and hot-swap locks name stock hosts only."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'compat/host-changes.json'
STATUSES = {'draft', 'approved', 'posted', 'merged', 'released', 'declined', 'not_planned'}
PR = re.compile(r'^https://github\.com/(napari/napari|spyder-ide/qtpy)/pull/\d+$')
HOT_SWAP = 'only VisPy is replaced'
# Drafts stay local (user, 2026-10-28; publication_drift KNOWN), so published main lacks the files: an entry names
# its draft by path, and the user, not this repository, submits it upstream (D28 plan, upstream AI policies).
DRAFTS = 'docs/upstream-drafts/'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def header(path):
    """The leading comment lines of a lock."""
    lines = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('#'):
            break
        lines.append(line)
    return lines


def requirements(path):
    """(normalized name, text before ' \\') for each requirement line of a uv-compiled lock."""
    result = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line[0] in '# \t-':
            continue
        spec = line.split(' \\')[0].strip()
        name = re.split(r'[=<>!~@ ;\[]', spec, maxsplit=1)[0]
        result.append((re.sub(r'[-_.]+', '-', name).lower(), spec))
    return result


def test_every_host_patch_is_registered_once():
    names = [entry['patch'] for entry in registry()['patches']]
    on_disk = [path.relative_to(ROOT).as_posix() for path in (ROOT / 'compat/host-patches').glob('*.patch')]
    assert sorted(names) == sorted(on_disk) and len(names) == len(set(names))


def test_registered_hashes_match_the_patch_files():
    for entry in registry()['patches']:
        assert hashlib.sha256((ROOT / entry['patch']).read_bytes()).hexdigest() == entry['sha256'], entry['patch']


def test_host_patches_serve_strict_rows_only():
    assert all(entry['profiles'] == ['strict'] for entry in registry()['patches'])


def test_each_patch_says_why_vispy_cannot_fix_it():
    assert all(entry['why_not_vispy'].strip() for entry in registry()['patches'])


def test_upstream_entries_are_consistent():
    for entry in registry()['patches']:
        assert entry['upstream'], entry['patch']
        for change in entry['upstream']:
            status = change['status']
            assert status in STATUSES, (entry['patch'], status)
            if status == 'not_planned':
                assert change['reason'].strip(), entry['patch']
            if status in {'draft', 'approved'}:
                assert change['change'].startswith(DRAFTS) and change['change'].endswith('.patch'), change
            if status in {'posted', 'merged', 'released', 'declined'}:
                assert PR.match(change['pr'] or ''), change
            assert (change.get('released_in') is not None) == (status == 'released'), change


def test_stock_swap_locks_name_stock_hosts_only():
    # Stock-swap locks name local wheel paths and stay local (.gitignore: /compat/host-environments/*), so this
    # checks every one present in the tree; published main carries none.
    for lock in (ROOT / 'compat/host-environments').glob('*.txt'):
        if any(HOT_SWAP in line for line in header(lock)):
            for name, spec in requirements(lock):
                if name != 'vispy':
                    assert '@' not in spec and '+' not in spec, (lock.name, name, spec)


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
