# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit, non-overwriting migration of the v1 workflow ledger to v2.

Preserve every legacy required feature/profile pair and all workflow rows.
Applicability review is reset: migration cannot approve exclusions or evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

try:
    from .compatibility_inventory import ROOT, check, read_json, unique_by, validate
except ImportError:
    from compatibility_inventory import ROOT, check, read_json, unique_by, validate


def migrate_v1(ledger):
    check(type(ledger.get('schema')) is int and ledger['schema'] == 1, 'migration requires a v1 ledger')
    result = deepcopy(ledger)
    profiles = unique_by(result['profiles'], lambda p: p['id'], 'profile')
    features = unique_by(result['features'], lambda f: f['id'], 'feature')
    rows = unique_by(result['rows'], lambda r: (r['feature'], r['profile']), 'feature/profile key')
    required_profiles = result.pop('required_profiles')
    check(required_profiles and set(required_profiles) <= set(profiles), 'missing or unknown legacy required profiles')
    check(len(required_profiles) == len(set(required_profiles)), 'duplicate legacy required profiles')
    check(set(rows) <= {(f, p) for f in features for p in profiles}, 'dangling legacy feature/profile')
    result['schema'], result['reviewed'] = 2, False
    result['applicability'] = []
    for feature in result['features']:
        required = feature.pop('required')
        check(type(required) is bool, 'legacy required flag must be boolean')
        dependencies = feature.pop('dependencies')
        check(isinstance(dependencies, list) and len(set(dependencies)) == len(dependencies)
              and set(dependencies) <= set(features), 'invalid legacy dependencies')
        for profile in profiles:
            status = 'required' if required and profile in required_profiles else 'optional'
            result['applicability'].append({
                'feature': feature['id'], 'profile': profile, 'status': status,
                'rationale': ('Preserved v1 required feature/profile pair; concrete applicability still needs review.'
                              if status == 'required' else
                              'Outside the v1 required feature/profile pairs; optional pending explicit scope review.'),
                'reviewed': False, 'dependencies': list(dependencies),
            })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result = migrate_v1(read_json(args.input))
    validate(result, args.root)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'schema': 2, 'required_pairs': sum(a['status'] == 'required' for a in result['applicability']),
                      'reviewed': False, 'rows_preserved': len(result['rows'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
