# SPDX-License-Identifier: AGPL-3.0-only
"""Conserve required scope across explicit, reviewed v2-to-v3 ledger transfers.

Coverage is a review declaration, never inferred from a passing smoke test.
Qualification still comes solely from the ordinary inventory/evidence validator.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

try:
    from .compatibility_inventory import ROOT, check, file_ref, read_json, unique_by
except ImportError:
    from compatibility_inventory import ROOT, check, file_ref, read_json, unique_by


def digest(value):
    """Stable object identity independent of JSON indentation/key order."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('utf-8')).hexdigest()


def pair(record):
    return record['feature'], record['profile']


def origins(baseline):
    features = {f['id']: f for f in baseline['features']}
    profiles = {p['id']: p for p in baseline['profiles']}
    rows = {pair(r): r for r in baseline['rows']}
    return {pair(a): {'feature': features[a['feature']], 'profile': profiles[a['profile']],
                      'applicability': a, 'row': rows.get(pair(a))}
            for a in baseline['applicability'] if a['status'] == 'required'}


def criteria(origin):
    feature = origin['feature']
    return {'scope', 'ordinary', 'mutation'} | {
        'requirement:' + name for name in feature['requirements']
    } | {'capability:' + name for name in feature['capabilities']} | {
        'dependency:' + name for name in origin['applicability']['dependencies']}


def validate_conservation(ledger, root, validate_baseline):
    """Return transferred parent keys only after full conservation validation.

    No exclusions are admitted here. An authorized scope-change mechanism needs
    its own reviewed contract; unsupported or missing hardware stays required.
    Transfers may chain, but every terminal successor remains an ordinary
    required pair subject to all existing identity/functional/observer gates.
    """
    record = ledger['conservation']
    baseline = read_json(file_ref(root, record['baseline']))
    check(baseline.get('schema') == 2, 'conservation baseline must be a frozen v2 ledger')
    validate_baseline(baseline, root)
    check(baseline['upstream_commit'] == ledger['upstream_commit'], 'conservation upstream pin changed')
    check(set(baseline['capabilities']) <= set(ledger['capabilities']), 'baseline capabilities removed')
    original = origins(baseline)
    features = {f['id']: f for f in ledger['features']}
    profiles = {p['id']: p for p in ledger['profiles']}
    applicability = {pair(a): a for a in ledger['applicability']}
    rows = {pair(r): r for r in ledger['rows']}
    transfers = unique_by(record['transfers'], lambda t: pair(t['origin']), 'origin disposition')
    check(set(transfers) <= set(original), 'transfer origin is not an original required obligation')
    for key, origin in original.items():
        check(key in applicability and applicability[key]['status'] == 'required',
              f'original required obligation removed or downgraded: {key}')
        check(features.get(key[0]) == origin['feature'], f'original feature scope changed: {key}')
        check(profiles.get(key[1]) == origin['profile'], f'original profile changed: {key}')
        check(applicability[key]['dependencies'] == origin['applicability']['dependencies'],
              f'original dependencies changed: {key}')
        if key not in transfers:
            continue
        transfer = transfers[key]
        check(rows.get(key) == origin['row'], f'transferred historical row changed: {key}')
        check(transfer['origin_sha256'] == digest(origin), f'changed origin identity: {key}')
        check(transfer['rationale'].strip(), 'blank transfer rationale')
        coverage = unique_by(transfer['coverage'], lambda c: c['criterion'], 'coverage criterion')
        check(set(coverage) == criteria(origin), f'incomplete or unknown origin coverage: {key}')
        targets = set()
        for item in coverage.values():
            check(item['rationale'].strip(), 'blank coverage rationale')
            targets.update(pair(p) for p in item['successors'])
        for target in targets:
            check(target != key, 'self transfer')
            check(target in applicability, f'dangling successor: {target}')
            decision = applicability[target]
            check(decision['status'] == 'required', 'required obligation transferred to optional/nonapplicable work')
            check(decision['reviewed'], 'successor applicability is not reviewed')
            check(profiles[target[1]]['admitted'] and profiles[target[1]]['environment_sha256'],
                  'successor lacks a concrete pinned profile')
            check(target in rows, 'successor lacks a workflow row')
            check(set(origin['applicability']['dependencies']) <= set(decision['dependencies']),
                  'successor omitted original required dependency')
        for name in origin['feature']['requirements']:
            check(all(name in features[p['feature']]['requirements']
                      for p in coverage['requirement:' + name]['successors']),
                  'successor omitted covered requirement')
        for name in origin['feature']['capabilities']:
            check(all(name in features[p['feature']]['capabilities']
                      for p in coverage['capability:' + name]['successors']),
                  'successor omitted covered capability')
        old_sources = {digest(s) for s in origin['feature']['upstream_sources']}
        new_sources = {digest(s) for target in targets for s in features[target[0]]['upstream_sources']}
        check(old_sources <= new_sources, 'successors omitted original upstream sources')
        review = read_json(file_ref(root, transfer['review']))
        payload = {k: v for k, v in transfer.items() if k != 'review'}
        check(type(review) is dict and review.get('schema') == 1
              and review.get('status') == 'APPROVED_SCOPE'
              and type(review.get('reviewer')) is str and review['reviewer'].strip()
              and review.get('baseline_sha256') == record['baseline']['sha256']
              and review.get('transfer_sha256') == digest(payload),
              'missing/stale scope review for exact baseline and transfer')
    visiting, visited = set(), set()

    def visit(key):
        check(key not in visiting, f'cyclic obligation transfer: {key}')
        if key in visited or key not in transfers:
            return
        visiting.add(key)
        for item in transfers[key]['coverage']:
            for successor in item['successors']:
                visit(pair(successor))
        visiting.remove(key)
        visited.add(key)

    for key in transfers:
        visit(key)
    return set(transfers), len(original)


def migrate_v2(ledger, baseline_reference):
    check(type(ledger.get('schema')) is int and ledger['schema'] == 2,
          'conservation migration requires a v2 ledger')
    result = deepcopy(ledger)
    result.update(schema=3, reviewed=False,
                  conservation={'baseline': deepcopy(baseline_reference), 'transfers': []})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='Frozen v2 baseline inside root')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    source = args.input.resolve()
    check(source.is_relative_to(root), 'baseline must be retained inside the selected root')
    reference = {'path': source.relative_to(root).as_posix(),
                 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    result = migrate_v2(read_json(source), reference)
    try:
        from .compatibility_inventory import validate
    except ImportError:
        from compatibility_inventory import validate
    summary = validate(result, root)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(summary))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
