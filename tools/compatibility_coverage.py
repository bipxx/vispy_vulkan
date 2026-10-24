# SPDX-License-Identifier: AGPL-3.0-only
"""Join selected public criteria to executable scenarios without discharging parents.

A script-ready binding is preparation, never observed/installed qualification.
The canonical inventory and original gate validators remain authoritative.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .compatibility_candidate import scope_digest, validate_candidate
    from .compatibility_conservation import criteria as origin_criteria, digest, origins, pair
    from .compatibility_inventory import (ROOT, InventoryError, check, file_ref, fixture_exists,
                                          local_file, read_json, shape, unique_by)
except ImportError:
    from compatibility_candidate import scope_digest, validate_candidate
    from compatibility_conservation import criteria as origin_criteria, digest, origins, pair
    from compatibility_inventory import (ROOT, InventoryError, check, file_ref, fixture_exists,
                                         local_file, read_json, shape, unique_by)

DEFAULT = ROOT / 'compat/candidates/tk-state-resource-1/coverage.json'
MODES = ('ordinary', 'mutation', 'failure', 'recovery')


def seal(record):
    record['manifest_sha256'] = digest({k: v for k, v in record.items() if k != 'manifest_sha256'})
    return record


def validate_coverage(record, root=ROOT, require_reviewed=False, require_script_ready=False):
    root = Path(root)
    schema = read_json(ROOT / 'compat/vispy-coverage.schema.json')
    shape(record, schema, schema['$defs'])
    check(record['manifest_sha256'] == digest({k: v for k, v in record.items() if k != 'manifest_sha256'}),
          'coverage map identity changed')
    candidate = read_json(local_file(root, record['candidate']['path']))
    preparation = validate_candidate(candidate, root)
    check(record['candidate']['scope_sha256'] == scope_digest(candidate), 'coverage candidate scope changed')
    baseline = read_json(file_ref(root, candidate['ledger']))
    original = origins(baseline)
    proposals = unique_by(candidate['proposals'], lambda p: p['id'], 'proposal')
    profiles = {p['id'] for p in candidate['profiles']}
    workflows = {w['id']: w for w in candidate['workflows']}
    parents = unique_by(record['origin_dispositions'], pair, 'retained parent')
    check(set(parents) == set(original), 'required original obligation missing or invented')
    for key, origin in original.items():
        parent = parents[key]
        check(parent['origin_sha256'] == digest(origin), 'retained origin identity changed')
        check(set(parent['criteria']) == origin_criteria(origin), 'original criteria removed or changed')
        expected = {p['id'] for p in proposals.values() if key in {pair(o) for o in p['origins']}}
        check(len(parent['proposed_subsets']) == len(set(parent['proposed_subsets']))
              and set(parent['proposed_subsets']) == expected, 'retained parent subset reconciliation changed')
    criteria = unique_by(record['criteria'], lambda c: c['id'], 'selected criterion')
    by_mode = unique_by(record['criteria'], lambda c: (c['feature'], c['kind']), 'feature acceptance mode')
    check(set(by_mode) == {(f, mode) for f in proposals for mode in MODES},
          'missing selected feature acceptance criterion')
    for criterion in criteria.values():
        feature, mode = criterion['feature'], criterion['kind']
        proposal = proposals[feature]
        check(criterion['id'] == feature + '.' + mode, 'unstable selected criterion identity')
        check(set(criterion['operations']) <= set(proposal['entry_points']), 'criterion has unselected public operation')
        check(set(criterion['requirements']) <= set(proposal['requirements']), 'criterion has unselected requirement')
        check(criterion['new_requirement'] is (not proposal['origins']), 'unseeded method invented or lost its new requirement')
        links = unique_by(criterion['origin_links'], lambda p: (p['feature'], p['profile'], p['criterion']),
                          'origin criterion link')
        token = 'ordinary' if mode == 'ordinary' else 'mutation'
        check(set(links) == {(p['feature'], p['profile'], token) for p in proposal['origins']},
              'criterion origin link is missing, invented or overstated')
        fixture = criterion['fixture']
        check(fixture['source']['path'] == fixture['nodeid'].split('::', 1)[0], 'criterion fixture source differs')
        file_ref(root, fixture['source'])
        fixture_exists(root, fixture['nodeid'])
    for feature, proposal in proposals.items():
        selected = [c for c in criteria.values() if c['feature'] == feature]
        check(set(proposal['entry_points']) == {op for c in selected for op in c['operations']},
              'selected public operation omitted')
        check(set(proposal['requirements']) == {req for c in selected for req in c['requirements']},
              'selected requirement omitted')
    bindings = unique_by(record['bindings'], lambda b: (b['criterion'], b['profile']), 'criterion/profile binding')
    check(set(bindings) == {(c, p) for c in criteria for p in profiles}, 'missing criterion/profile binding')
    ready, unresolved = 0, []
    for key, binding in bindings.items():
        criterion = criteria[key[0]]
        if binding['status'] == 'source-only':
            check(binding['workflow'] is None and binding['scenario'] is None,
                  'source-only criterion claims an observed scenario')
            unresolved.append({'criterion': key[0], 'profile': key[1], 'reason': binding['rationale']})
            continue
        check(binding['workflow'] in workflows, 'criterion references missing workflow')
        workflow = workflows[binding['workflow']]
        check(key[1] in workflow['profiles'] and criterion['feature'] in workflow['features'],
              'criterion workflow has wrong feature/profile')
        scenario = binding['scenario']
        check(scenario is not None and scenario['script'] == workflow['script']
              and scenario['arguments'] == [], 'criterion scenario identity or literal arguments changed')
        file_ref(root, scenario['script'])
        check(any(a['kind'] == criterion['kind'] and a['nodeid'] == criterion['fixture']['nodeid']
                  and a['cases'] == criterion['fixture']['cases'] and a['source'] == criterion['fixture']['source']
                  for a in workflow['acceptance']),
              'ordinary or unrelated fixture cannot cover the required branch')
        ready += 1
    # One existing scope review can approve both declarations without a hash
    # cycle: the candidate scope digest excludes only reviews and self identity.
    scope_ref = candidate['reviews']['scope']
    scope_review = read_json(file_ref(root, scope_ref)) if scope_ref is not None else {}
    reviewed = preparation['reviewed'] and scope_review.get('coverage_map_sha256') == record['manifest_sha256']
    check(not require_reviewed or reviewed, 'coverage/source scope review remains pending or stale')
    check(not require_script_ready or not unresolved, 'required branch lacks executable observer mapping')
    return {'status': 'VALID_COVERAGE_PROPOSAL', 'candidate': candidate['id'],
            'criteria': len(criteria), 'profile_bindings': len(bindings),
            'script_ready_bindings': ready, 'unmapped_observation_bindings': unresolved,
            'original_required_pairs_retained': len(original), 'originals_discharged': 0,
            'reviewed': reviewed, 'installable': False, 'qualified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, default=DEFAULT)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--require-reviewed', action='store_true')
    parser.add_argument('--require-script-ready', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = validate_coverage(read_json(args.map), args.root, args.require_reviewed, args.require_script_ready)
    except (InventoryError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
