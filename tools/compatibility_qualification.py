# SPDX-License-Identifier: AGPL-3.0-only
"""Freeze whole-row admission selections; this is not artifact admission.

Validation is read-only. Materialization requires an explicit new output path.
The later subject/provenance/CI/promotion join remains a separate requirement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .compatibility_candidate import scope_digest
    from .compatibility_conservation import digest
    from .compatibility_execution import (DEFAULT as EXECUTION, load_inputs, new_output,
                                          validate_execution)
    from .compatibility_inventory import (ROOT, InventoryError, check, file_ref,
                                          local_file, read_json, shape, unique_by)
except ImportError:
    from compatibility_candidate import scope_digest
    from compatibility_conservation import digest
    from compatibility_execution import (DEFAULT as EXECUTION, load_inputs, new_output,
                                         validate_execution)
    from compatibility_inventory import (ROOT, InventoryError, check, file_ref,
                                         local_file, read_json, shape, unique_by)

SCHEMA = 'compat/vispy-admission-selection.schema.json'
DEFAULT = ROOT / 'compat/candidates/tk-state-resource-1/admission-selection.json'
MODES = ('ordinary', 'mutation', 'failure', 'recovery')


def key(record):
    return tuple(record[field] for field in ('feature', 'profile', 'criterion'))


def ordered(records):
    return sorted(records, key=key)


def seal(record):
    record['manifest_sha256'] = digest({k: v for k, v in record.items() if k != 'manifest_sha256'})
    return record


def expand_selection(requested, mappings, ledger):
    """Every request selects a whole row and its recursive same-profile rows."""
    check(requested, 'empty admission request')
    unique_by(requested, key, 'requested criterion')
    check(requested == ordered(requested), 'requested criteria must be sorted')
    destinations = unique_by((m['destination'] for m in mappings), key, 'mapped criterion')
    rows = unique_by(ledger['rows'], lambda r: (r['feature'], r['profile']), 'execution row')
    apps = unique_by(ledger['applicability'], lambda r: (r['feature'], r['profile']), 'applicability')
    for request in requested:
        check(key(request) in destinations, 'requested criterion has no execution mapping')
    visited, visiting, closure = set(), set(), []

    def visit(pair):
        check(pair not in visiting, 'cyclic admission dependency: ' + '/'.join(pair))
        if pair in visited:
            return
        check(pair in rows and pair in apps, 'missing dependency execution row/applicability')
        check(apps[pair]['status'] == 'required', 'admission dependency is not required')
        expected = {(pair[0], pair[1], pair[0] + '.' + mode) for mode in MODES}
        actual = {k for k in destinations if k[:2] == pair}
        check(actual == expected, 'whole-row admission requires all four mapped criteria')
        visiting.add(pair)
        for dependency in apps[pair]['dependencies']:
            visit((dependency, pair[1]))
        visiting.remove(pair)
        visited.add(pair)
        closure.extend(destinations[k] for k in sorted(expected))

    for request in requested:
        visit(key(request)[:2])
    return ordered(closure)


def prepare(execution_path, requested, root=ROOT):
    root = Path(root)
    execution = read_json(local_file(root, execution_path))
    validate_execution(execution, root)
    candidate, _, _ = load_inputs(execution, root)
    ledger = read_json(local_file(root, execution['execution']['path']))
    return seal({'schema': 1, 'phase': 'admission-selection',
                 'manifest_sha256': '0' * 64,
                 'candidate': {'path': execution['candidate']['path'],
                               'scope_sha256': scope_digest(candidate)},
                 'execution_map': {'path': execution_path,
                                   'scope_sha256': execution['manifest_sha256']},
                 'requested': requested,
                 'closure': expand_selection(requested, execution['mappings'], ledger)})


def validate_selection(record, root=ROOT, require_reviewed=False):
    root = Path(root)
    schema = read_json(root / SCHEMA)
    shape(record, schema, schema['$defs'])
    check(record['manifest_sha256'] == seal(dict(record))['manifest_sha256'],
          'admission selection digest changed')
    expected = prepare(record['execution_map']['path'], record['requested'], root)
    check(record == expected, 'admission selection scope/whole-row dependency closure changed')
    execution = read_json(local_file(root, record['execution_map']['path']))
    state = validate_execution(execution, root)
    candidate, _, _ = load_inputs(execution, root)
    review_ref = candidate['reviews']['scope']
    reviewed = state['reviewed'] and review_ref is not None
    if reviewed:
        review = read_json(file_ref(root, review_ref))
        reviewed = review.get('admission_scope_sha256') == record['manifest_sha256']
    check(not require_reviewed or reviewed, 'admission selection source/scope review remains pending or stale')
    return {'status': 'VALID_ADMISSION_SELECTION', 'requested': record['requested'],
            'closure': record['closure'], 'reviewed': bool(reviewed),
            'admitted': False, 'qualified': False, 'full_inventory_complete': False,
            'missing': ['exact-artifact-subject', 'producer-and-installed-evidence',
                        'required-head-ci', 'promotion-basis-review', 'terminal-retention']
                       + ([] if reviewed else ['bound-source-and-selection-scope-review'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--selection', type=Path, default=DEFAULT)
    parser.add_argument('--require-reviewed', action='store_true')
    parser.add_argument('--materialize', action='store_true')
    parser.add_argument('--execution-map', default=EXECUTION.relative_to(ROOT).as_posix())
    parser.add_argument('--requests', help='Root-relative JSON array of exact requested keys')
    parser.add_argument('--output', help='New root-relative selection file')
    args = parser.parse_args(argv)
    try:
        if args.materialize:
            check(args.requests and args.output, 'materialization requires requests and new output')
            output = new_output(args.root, args.output)
            record = prepare(args.execution_map, read_json(local_file(args.root, args.requests)), args.root)
            result = validate_selection(record, args.root, args.require_reviewed)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('xb') as stream:
                stream.write((json.dumps(record, indent=2) + '\n').encode())
        else:
            check(not (args.requests or args.output), 'output/requests require explicit materialization')
            result = validate_selection(read_json(args.selection), args.root, args.require_reviewed)
    except (InventoryError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
