# SPDX-License-Identifier: AGPL-3.0-only
"""Materialize and validate additive execution rows, preserving the frozen ledger.

The default is read-only validation. This join is preparation, never artifact
admission. Existing inventory/evidence validators remain authoritative.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath

try:
    from .compatibility_candidate import DEFAULT as CANDIDATE, scope_digest, validate_candidate
    from .compatibility_conservation import digest, origins
    from .compatibility_coverage import DEFAULT as COVERAGE, validate_coverage
    from .no_opengl.functional import WORKFLOW as FUNCTIONAL_WORKFLOW, CAPTURE_WORKFLOW, criterion_binding
    from .compatibility_inventory import (ROOT, POSITIVE, InventoryError, check, file_ref,
                                          local_file, read_json, shape, unique_by, validate)
except ImportError:
    from compatibility_candidate import DEFAULT as CANDIDATE, scope_digest, validate_candidate
    from compatibility_conservation import digest, origins
    from compatibility_coverage import DEFAULT as COVERAGE, validate_coverage
    from no_opengl.functional import WORKFLOW as FUNCTIONAL_WORKFLOW, CAPTURE_WORKFLOW, criterion_binding
    from compatibility_inventory import (ROOT, POSITIVE, InventoryError, check, file_ref,
                                         local_file, read_json, shape, unique_by, validate)

DEFAULT = ROOT / 'compat/candidates/tk-state-resource-1/execution.json'
SCHEMA = 'compat/vispy-execution.schema.json'


def seal(record):
    record['manifest_sha256'] = digest({k: v for k, v in record.items() if k != 'manifest_sha256'})
    return record


def pair(item):
    return item['feature'], item['profile']


def selected_pairs(candidate):
    return {pair(item) for item in candidate['pairs']}


def execution_scope(ledger, candidate):
    """Exclude only selected-row proof state and its explicit review flags.

    Baseline/history and unselected cross-product declarations remain complete.
    Exact current evidence bytes belong to the later qualification subject.
    """
    projected = deepcopy(ledger)
    pairs = selected_pairs(candidate)
    profiles = {p['id'] for p in candidate['profiles']}
    for profile in projected['profiles']:
        if profile['id'] in profiles:
            profile.update(admitted=False, environment_sha256=None)
    for applicability in projected['applicability']:
        if pair(applicability) in pairs:
            applicability['reviewed'] = False
    for index, row in enumerate(projected['rows']):
        if pair(row) in pairs:
            projected['rows'][index] = {k: row[k] for k in ('feature', 'profile', 'workflow', 'fixtures')}
    return digest(projected)


def template(candidate, coverage, baseline):
    """Construct the only additive, non-evidentiary initial view for this scope."""
    ledger = deepcopy(baseline)
    check(ledger['schema'] == 2, 'additive execution requires a frozen v2 baseline; do not invent transfers')
    ledger['reviewed'] = False
    ledger['scope'] += '\nAdditive selected execution rows; original obligations remain required and incomplete.'
    check('public-workflow' in ledger['capabilities'], 'baseline lacks public-workflow capability')
    proposals = {p['id']: p for p in candidate['proposals']}
    profiles = {p['id'] for p in candidate['profiles']}
    check(not profiles.intersection(p['id'] for p in baseline['profiles']), 'execution profile overwrites a baseline profile')
    criteria = {c['id']: c for c in coverage['criteria']}
    bindings = {(b['criterion'], b['profile']): b for b in coverage['bindings']}
    workflows = {w['id']: w for w in candidate['workflows']}
    pairs = {pair(p): p for p in candidate['pairs']}
    for identifier in sorted(proposals):
        proposal = proposals[identifier]
        modes = {c['kind']: c for c in criteria.values() if c['feature'] == identifier}
        ledger['features'].append({
            'id': identifier, 'entry_point': '; '.join(proposal['entry_points']),
            'upstream_sources': deepcopy(proposal['upstream_sources']),
            'requirements': deepcopy(proposal['requirements']), 'capabilities': ['public-workflow'],
            'scope_reason': proposal['scope'] + '\nExcluded inputs remain required parent/residual work: '
                            + '; '.join(proposal['excluded']),
            'ordinary': modes['ordinary']['expected'],
            'mutation': '\n'.join(mode + ': ' + modes[mode]['expected']
                                  for mode in ('mutation', 'failure', 'recovery')),
            'owner': proposal['owner']})
    for identifier in sorted(profiles):
        ledger['profiles'].append({'id': identifier,
                                   'description': 'Selected execution profile ' + identifier
                                   + '; concrete observation pinned by preparation, not installed admission.',
                                   'admitted': False, 'environment_sha256': None})
    existing = {pair(a) for a in baseline['applicability']}
    for feature in ledger['features']:
        for profile in ledger['profiles']:
            key = feature['id'], profile['id']
            if key in existing:
                continue
            selected = key in pairs
            ledger['applicability'].append({
                'feature': key[0], 'profile': key[1], 'status': 'required' if selected else 'optional',
                'rationale': ('Selected additive scope; original parents remain required.' if selected else
                              'New unselected cross-product combination, unreviewed; not nonapplicability '
                              'or discharge of any original obligation.'),
                'reviewed': False, 'dependencies': deepcopy(pairs[key]['dependencies']) if selected else []})
    mappings = []
    for key in sorted(pairs):
        selected = sorted((c for c in criteria.values() if c['feature'] == key[0]), key=lambda c: c['id'])
        selected_bindings = [bindings[(c['id'], key[1])] for c in selected]
        check(all(b['status'] == 'script-ready' for b in selected_bindings), 'execution requires every selected script branch')
        ids = {b['workflow'] for b in selected_bindings}
        check(len(ids) == 1, 'one execution row requires one composite workflow; review explicit splits separately')
        workflow_id = ids.pop()
        workflow = workflows[workflow_id]
        fixtures = {}
        for criterion in selected:
            source = criterion['fixture']
            kind = 'ordinary' if criterion['kind'] == 'ordinary' else 'mutation'
            fixture_key = source['nodeid'], kind, source['cases']
            if fixture_key not in fixtures:
                fixtures[fixture_key] = {'nodeid': source['nodeid'], 'kind': kind,
                                         'cases': source['cases'], 'expected': ''}
            fixtures[fixture_key]['expected'] += criterion['kind'] + ': ' + criterion['expected'] + '\n'
            mapping = {'criterion': criterion['id'], 'profile': key[1],
                       'destination': {'feature': key[0], 'profile': key[1], 'criterion': criterion['id']},
                       'workflow': workflow_id}
            if workflow_id in (FUNCTIONAL_WORKFLOW, CAPTURE_WORKFLOW):
                mapping['functional_result'] = criterion_binding(key[0], criterion['kind'])
            mappings.append(mapping)
        ledger['rows'].append({
            'feature': key[0], 'profile': key[1], 'state': 'implemented-untested', 'outcome': 'not-run',
            'workflow': {'id': workflow_id, 'scenario': 'script', 'binding': None,
                         'script': deepcopy(workflow['script']), 'arguments': []},
            'fixtures': [dict(f, expected=f['expected'].rstrip()) for f in fixtures.values()],
            'identity': None, 'receipt': None,
            'blocker': 'New execution identity has no transferred receipt; source/scope review and installed proof remain pending.',
            'next_action': 'Obtain bound reviews, then exact same-profile product/workflow evidence under the existing auditors.'})
    return ledger, mappings


def load_inputs(record, root):
    candidate = read_json(local_file(root, record['candidate']['path']))
    validate_candidate(candidate, root)
    check(record['candidate']['scope_sha256'] == scope_digest(candidate), 'execution candidate scope changed')
    coverage = read_json(file_ref(root, record['coverage']))
    validate_coverage(coverage, root, require_script_ready=True)
    check(coverage['candidate']['path'] == record['candidate']['path'], 'execution coverage belongs to another candidate')
    check(record['baseline'] == candidate['ledger'], 'execution replaced the frozen preparation baseline')
    baseline = read_json(file_ref(root, record['baseline']))
    check(record['execution']['path'] not in (record['baseline']['path'], record['candidate']['path'],
                                             record['coverage']['path']), 'execution overwrites an immutable input')
    return candidate, coverage, baseline


def reviews_pass(record, candidate, coverage, root):
    # Existing source/scope approval kinds; no new reviewer or self-approval type.
    if not all(candidate['reviews'].values()):
        return False
    validate_candidate(candidate, root, require_reviewed=True)
    validate_coverage(coverage, root, require_reviewed=True)
    review = read_json(file_ref(root, candidate['reviews']['scope']))
    return review.get('execution_map_sha256') == record['manifest_sha256']


def validate_execution(record, root=ROOT, require_reviewed=False):
    root = Path(root)
    schema = read_json(root / SCHEMA)
    shape(record, schema, schema['$defs'])
    check(record['manifest_sha256'] == digest({k: v for k, v in record.items() if k != 'manifest_sha256'}),
          'execution map identity changed')
    candidate, coverage, baseline = load_inputs(record, root)
    ledger = read_json(local_file(root, record['execution']['path']))
    expected, mappings = template(candidate, coverage, baseline)
    keys = unique_by(record['mappings'], lambda m: (m['criterion'], m['profile']), 'execution criterion binding')
    unique_by(record['mappings'], lambda m: tuple(m['destination'][k] for k in ('feature', 'profile', 'criterion')),
              'execution destination')
    check(keys == {(m['criterion'], m['profile']): m for m in mappings}, 'execution criterion mapping lost or changed scope/workflow/profile')
    check(execution_scope(ledger, candidate) == execution_scope(expected, candidate),
          'execution scope changed: baseline/history, selected scope or applicability was altered')
    check(record['execution']['scope_sha256'] == execution_scope(ledger, candidate), 'execution ledger scope identity changed')
    validate(ledger, root)
    pairs = selected_pairs(candidate)
    approved = reviews_pass(record, candidate, coverage, root)
    applicability = {pair(a): a for a in ledger['applicability']}
    selected_reviewed = all(applicability[key]['reviewed'] for key in pairs)
    for row in ledger['rows']:
        if pair(row) not in pairs:
            continue
        if row['state'] in POSITIVE:
            check(approved and selected_reviewed, 'execution proof precedes bound source/scope review')
            check(row['identity']['source_commit'] == candidate['product_source_commit'], 'execution product source changed')
    touched_profiles = [p for p in ledger['profiles'] if p['id'] in {p['id'] for p in candidate['profiles']}]
    check(not (any(applicability[key]['reviewed'] for key in pairs)
               or any(p['admitted'] or p['environment_sha256'] is not None for p in touched_profiles)) or approved,
          'execution review/admission flags lack bound source/scope approval')
    check(not require_reviewed or (approved and selected_reviewed), 'execution source/scope review remains pending or stale')
    return {'status': 'VALID_EXECUTION_PREPARATION', 'selected_pairs': len(pairs), 'criterion_bindings': len(keys),
            'original_required_pairs_retained': len(origins(baseline)), 'originals_discharged': 0,
            'reviewed': approved and selected_reviewed, 'installable': False, 'qualified': False,
            'full_inventory_complete': False}


def prepare(candidate_path, coverage_path, ledger_path, root=ROOT):
    root = Path(root)
    candidate = read_json(local_file(root, candidate_path))
    validate_candidate(candidate, root)
    coverage_file = local_file(root, coverage_path)
    coverage = read_json(coverage_file)
    validate_coverage(coverage, root, require_script_ready=True)
    check(coverage['candidate']['path'] == candidate_path, 'execution coverage belongs to another candidate')
    baseline = read_json(file_ref(root, candidate['ledger']))
    check(ledger_path not in (candidate_path, coverage_path, candidate['ledger']['path']), 'execution overwrites an immutable input')
    ledger, mappings = template(candidate, coverage, baseline)
    record = {'schema': 1, 'phase': 'execution-preparation', 'manifest_sha256': '0' * 64,
              'candidate': {'path': candidate_path, 'scope_sha256': scope_digest(candidate)},
              'coverage': {'path': coverage_path, 'sha256': hashlib.sha256(coverage_file.read_bytes()).hexdigest()},
              'baseline': deepcopy(candidate['ledger']),
              'execution': {'path': ledger_path, 'scope_sha256': execution_scope(ledger, candidate)},
              'mappings': mappings}
    return ledger, seal(record)


def new_output(root, name):
    relative = PurePosixPath(name)
    check(not relative.is_absolute() and '..' not in relative.parts and ':' not in name and '\\' not in name,
          'invalid execution output path')
    path = (root / relative).resolve()
    check(path.is_relative_to(root.resolve()) and not path.exists(), 'execution output exists or leaves workspace')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--map', type=Path, default=DEFAULT)
    parser.add_argument('--require-reviewed', action='store_true')
    parser.add_argument('--materialize', action='store_true')
    parser.add_argument('--candidate', default=CANDIDATE.relative_to(ROOT).as_posix())
    parser.add_argument('--coverage', default=COVERAGE.relative_to(ROOT).as_posix())
    parser.add_argument('--output-ledger')
    parser.add_argument('--output-map')
    parser.add_argument('--apply-reviewed', action='store_true')
    args = parser.parse_args(argv)
    try:
        check(not (args.materialize and args.apply_reviewed), 'choose materialization or review application')
        if args.materialize:
            check(args.output_ledger and args.output_map, 'materialization requires both explicit output paths')
            output = new_output(args.root, args.output_ledger)
            mapping = new_output(args.root, args.output_map)
            check(output != mapping, 'execution outputs must be distinct')
            ledger, record = prepare(args.candidate, args.coverage, args.output_ledger, args.root)
            if args.require_reviewed:
                candidate, coverage, _ = load_inputs(record, args.root)
                check(reviews_pass(record, candidate, coverage, args.root),
                      'execution materialization lacks exact source/scope approvals')
                for applicability in ledger['applicability']:
                    if pair(applicability) in selected_pairs(candidate):
                        applicability['reviewed'] = True
            validate(ledger, args.root)
            for path, value in ((output, ledger), (mapping, record)):
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write((json.dumps(value, indent=2) + '\n').encode())
            result = validate_execution(record, args.root, args.require_reviewed)
        else:
            record = read_json(args.map)
            if args.apply_reviewed:
                validate_execution(record, args.root)
                candidate, coverage, _ = load_inputs(record, args.root)
                check(reviews_pass(record, candidate, coverage, args.root), 'execution review application lacks exact approvals')
                path = local_file(args.root, record['execution']['path'])
                ledger = read_json(path)
                for applicability in ledger['applicability']:
                    if pair(applicability) in selected_pairs(candidate):
                        applicability['reviewed'] = True
                check(execution_scope(ledger, candidate) == record['execution']['scope_sha256'], 'review application changed scope')
                validate(ledger, args.root)
                path.write_bytes((json.dumps(ledger, indent=2) + '\n').encode())
            result = validate_execution(record, args.root, args.require_reviewed)
    except (InventoryError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
