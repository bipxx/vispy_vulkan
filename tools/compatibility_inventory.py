# SPDX-License-Identifier: AGPL-3.0-only
"""Validate the versioned VisPy workflow ledger without importing VisPy/GPU code.

Structural validity is separate from completion. ``--require-complete`` fails
while any required feature/profile is absent, pending, failed or unqualified.
Receipts bind selected tests and observer outputs to one source/artifact/profile.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'compat/vispy-compatibility.schema.json'
LEDGER = ROOT / 'compat/vispy-compatibility.json'
SPEC = 'docs/superpowers/specs/2026-10-24-vispy-compatibility-gap-closure.md'
STATES = ('not-inventoried', 'unsupported', 'implemented-untested', 'source-tested',
          'wheel-tested', 'qualified', 'blocked-external')
POSITIVE = ('source-tested', 'wheel-tested', 'qualified')
GATES = ('dependency-closure', 'startup-transient-loads', 'execution-api')


class InventoryError(ValueError):
    pass


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InventoryError(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique)


def check(condition, message):
    if not condition:
        raise InventoryError(message)


def shape(value, schema, definitions, location='$'):
    """Evaluate only the closed JSON Schema subset used by our versioned schema.

    Unknown keywords are errors, preventing an unsupported constraint silently
    becoming decorative. No external references or optional schema dependency.
    """
    supported = {'$schema', '$id', 'title', 'description', '$defs', '$ref', 'type',
                 'const', 'enum', 'required', 'properties', 'additionalProperties',
                 'items', 'minItems', 'uniqueItems', 'minLength', 'pattern', 'minimum'}
    check(not (set(schema) - supported), f'{location}: unsupported schema keyword')
    if '$ref' in schema:
        reference = schema['$ref']
        check(reference.startswith('#/$defs/'), f'{location}: unsupported reference')
        return shape(value, definitions[reference.removeprefix('#/$defs/')], definitions, location)
    if 'type' in schema:
        types = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        kinds = {'object': dict, 'array': list, 'string': str, 'boolean': bool,
                 'integer': int, 'null': type(None)}
        check(any(type(value) is kinds[kind] for kind in types), f'{location}: expected {types}')
    if 'const' in schema:
        check(type(value) is type(schema['const']) and value == schema['const'], f'{location}: wrong constant')
    if 'enum' in schema:
        check(value in schema['enum'], f'{location}: unknown value {value!r}')
    if isinstance(value, dict):
        check(set(schema.get('required', [])) <= set(value), f'{location}: missing required fields')
        properties = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            check(not (set(value) - set(properties)), f'{location}: unexpected fields {set(value) - set(properties)}')
        for key, item in value.items():
            if key in properties:
                shape(item, properties[key], definitions, f'{location}.{key}')
    if isinstance(value, list):
        check(len(value) >= schema.get('minItems', 0), f'{location}: too few items')
        if schema.get('uniqueItems'):
            check(len({json.dumps(item, sort_keys=True) for item in value}) == len(value), f'{location}: duplicate items')
        for index, item in enumerate(value):
            shape(item, schema.get('items', {}), definitions, f'{location}[{index}]')
    if isinstance(value, str):
        check(len(value) >= schema.get('minLength', 0), f'{location}: empty string')
        if 'pattern' in schema:
            check(re.search(schema['pattern'], value) is not None, f'{location}: invalid string {value!r}')
    if type(value) is int and 'minimum' in schema:
        check(value >= schema['minimum'], f'{location}: below minimum')


def local_file(root, name):
    path = PurePosixPath(name)
    check(not path.is_absolute() and '..' not in path.parts and '\\' not in name and ':' not in name,
          f'invalid relative file: {name}')
    resolved = (root / path).resolve()
    check(resolved.is_relative_to(root.resolve()) and resolved.is_file(), f'missing local file: {name}')
    return resolved


def file_ref(root, reference):
    check(set(reference) == {'path', 'sha256'}, 'file reference needs path and sha256')
    path = local_file(root, reference['path'])
    check(hashlib.sha256(path.read_bytes()).hexdigest() == reference['sha256'], f'changed evidence: {path}')
    return path


def unique_by(items, key, label):
    indexed = {}
    for item in items:
        name = key(item)
        check(name not in indexed, f'duplicate {label}: {name}')
        indexed[name] = item
    return indexed


def fixture_exists(root, nodeid):
    parts = nodeid.split('::')
    check(len(parts) >= 2, f'fixture must be a pytest node ID: {nodeid}')
    path = local_file(root, parts[0])
    check(path.suffix == '.py', f'not a Python fixture: {nodeid}')
    nodes = ast.parse(path.read_text(encoding='utf-8-sig')).body
    for name in parts[1:]:
        name = name.split('[', 1)[0]
        matches = [node for node in nodes if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
        check(len(matches) == 1, f'dangling fixture: {nodeid}')
        nodes = matches[0].body


def passed_pytest(root, reference, fixtures):
    report = read_json(file_ref(root, reference))
    check(type(report.get('exit_code')) is int and report['exit_code'] == 0, 'functional receipt did not exit successfully')
    collected = report.get('collected', [])
    check(collected and len(set(collected)) == len(collected), 'missing or duplicate collected tests')
    phases = {}
    for event in report.get('reports', []):
        check(event.get('outcome') == 'passed', 'functional receipt includes non-passing outcome')
        key = (event.get('nodeid'), event.get('when'))
        check(key[0] in collected and key[1] in ('setup', 'call', 'teardown'), 'unexpected test phase in receipt')
        check(key not in phases, 'duplicate test phase in receipt')
        phases[key] = event
    check(all((node, phase) in phases for node in collected for phase in ('setup', 'call', 'teardown')),
          'incomplete collected test receipt')
    for fixture in fixtures:
        selector = fixture['nodeid']
        matching = [node for node in collected if node == selector or node.startswith(selector + '[')]
        check(len(matching) == fixture['cases'], f'wrong collected count for {selector}')
        for node in matching:
            check(all((node, phase) in phases for phase in ('setup', 'call', 'teardown')),
                  f'incomplete functional receipt: {node}')


def validate(ledger, root=ROOT, require_complete=False):
    root = Path(root)
    schema = read_json(root / 'compat/vispy-compatibility.schema.json')
    check(type(ledger.get('schema')) is int and ledger['schema'] == schema['properties']['schema']['const'],
          'wrong constant: ledger schema 2 required; migrate v1 explicitly before validation')
    shape(ledger, schema, schema['$defs'])
    upstream = read_json(root / 'compat/upstream_manifest.json')
    check(ledger['upstream_commit'] == upstream['upstream_commit'], 'wrong upstream source pin')
    requirement_ids = set(re.findall(r'\b(?:EV|INV|TK|STATE|SH|BACKEND|HOST|ART|HW|PERF|RET|LIC)-\d+\b',
                                    local_file(root, SPEC).read_text(encoding='utf-8')))
    profiles = unique_by(ledger['profiles'], lambda p: p['id'], 'profile')
    for profile in profiles.values():
        check(not profile['admitted'] or profile['environment_sha256'] is not None,
              'evidence-admitted profile lacks environment pin')
    features = unique_by(ledger['features'], lambda f: f['id'], 'feature')
    rows = unique_by(ledger['rows'], lambda r: (r['feature'], r['profile']), 'feature/profile key')
    applicability = unique_by(ledger['applicability'], lambda a: (a['feature'], a['profile']), 'applicability key')
    expected_pairs = {(feature, profile) for feature in features for profile in profiles}
    check(set(applicability) <= expected_pairs, 'dangling applicability feature/profile')
    check(set(applicability) == expected_pairs, 'missing explicit feature/profile applicability')
    check(any(a['status'] == 'required' for a in applicability.values()), 'inventory has no required feature/profile pairs')
    check(not ledger['reviewed'] or all(a['reviewed'] for a in applicability.values()),
          'reviewed inventory has unreviewed applicability')
    for reference in ledger['related_inventories']:
        file_ref(root, reference)
    for feature in features.values():
        check(set(feature['requirements']) <= requirement_ids, f'unknown requirement in {feature["id"]}')
        check(set(feature['capabilities']) <= set(ledger['capabilities']), f'unknown capability in {feature["id"]}')
        for source in feature['upstream_sources']:
            check(upstream['files'].get(source['path']) == source['sha256'], f'wrong upstream member pin: {source["path"]}')
    for key, pair in applicability.items():
        check(pair['rationale'].strip(), f'blank applicability rationale: {key}')
        check(set(pair['dependencies']) <= set(features), f'dangling dependency in {key}')
        check(pair['feature'] not in pair['dependencies'], 'self dependency')
        if pair['status'] == 'not-applicable':
            check(not pair['dependencies'], 'nonapplicable pair has dependencies')
            check(key not in rows, 'nonapplicable pair cannot carry a workflow row; retain blockers as applicable work')
        for dependency in pair['dependencies']:
            required = applicability[(dependency, pair['profile'])]['status']
            check(required != 'not-applicable', 'dependency is nonapplicable in the selected profile')
            check(pair['status'] != 'required' or required == 'required',
                  'required pair depends on an optional capability')
    visiting, visited = set(), set()
    def visit(key):
        check(key not in visiting, f'cyclic dependency: {key}')
        if key in visited:
            return
        visiting.add(key)
        for dependency in applicability[key]['dependencies']:
            visit((dependency, key[1]))
        visiting.remove(key)
        visited.add(key)
    for key in applicability:
        visit(key)
    incomplete = []
    for key, row in rows.items():
        feature_id, profile_id = key
        check(feature_id in features and profile_id in profiles, f'dangling feature/profile: {key}')
        for fixture in row['fixtures']:
            fixture_exists(root, fixture['nodeid'])
        if row['state'] in POSITIVE:
            check(profiles[profile_id]['admitted'], 'unassigned profile cannot carry positive evidence')
            check({'ordinary', 'mutation'} <= {f['kind'] for f in row['fixtures']}, 'missing ordinary/mutation acceptance mapping')
            check(row['outcome'] == 'passed', 'positive state conflicts with latest outcome')
            check(row['identity'] is not None and row['receipt'] is not None, 'positive state lacks identity/receipt')
            check(row['identity']['profile_sha256'] == profiles[profile_id]['environment_sha256'],
                  'row identity does not match the pinned environment/profile')
            receipt = read_json(file_ref(root, row['receipt']))
            check(receipt.get('schema') == 1 and receipt.get('feature') == feature_id and receipt.get('profile') == profile_id,
                  'receipt belongs to another feature/profile')
            check(receipt.get('identity') == row['identity'], 'stale source/artifact/profile receipt')
            check(receipt.get('child_waited') is True and type(receipt.get('exit_code')) is int and receipt['exit_code'] == 0,
                  'receipt has missing child wait or failed exit')
            check(receipt.get('phase') == row['state'], 'receipt does not prove claimed phase')
            check(set(features[feature_id]['requirements']) <= set(receipt.get('requirements', [])), 'receipt lacks required contract mapping')
            passed_pytest(root, receipt['pytest'], row['fixtures'])
            if row['state'] in ('wheel-tested', 'qualified'):
                check(row['identity']['wheel_sha256'] is not None, 'installed claim lacks wheel identity')
                check(receipt.get('installed_origin_verified') is True, 'installed origin not verified')
                audit = read_json(file_ref(root, receipt['distribution_audit']))
                check(audit.get('status') == 'PASS' and audit.get('identity') == row['identity'], 'missing matching distribution audit')
            if row['state'] == 'qualified':
                check(set(receipt.get('gates', {})) == set(GATES), 'missing qualification gate')
                for gate in GATES:
                    output = read_json(file_ref(root, receipt['gates'][gate]))
                    check(output.get('status') == 'PASS' and output.get('identity') == row['identity']
                          and output.get('controls_passed') is True and output.get('gate') == gate,
                          f'failed/stale/uncontrolled gate: {gate}')
            for dependency in applicability[key]['dependencies']:
                previous = rows.get((dependency, profile_id))
                check(previous is not None and previous['state'] in POSITIVE, 'unproven same-profile capability dependency')
                check(POSITIVE.index(previous['state']) >= POSITIVE.index(row['state']) and previous['identity'] == row['identity'],
                      'dependency is not proven for matching source/artifact/profile')
        else:
            check(row['identity'] is None and row['receipt'] is None, 'unproven state carries a current positive receipt')
            check(row['outcome'] != 'passed', 'unproven state claims passed')
    for key, pair in applicability.items():
        if pair['status'] == 'required':
            if key not in rows:
                incomplete.append('/'.join(key) + ' (missing)')
            elif rows[key]['state'] != 'qualified':
                incomplete.append('/'.join(key))
    check(not require_complete or (ledger['reviewed'] and not incomplete),
          f'full closure unproven: reviewed={ledger["reviewed"]}, {len(incomplete)} incomplete required rows')
    return {'status': 'VALID_INCOMPLETE' if incomplete or not ledger['reviewed'] else 'VALID_COMPLETE',
            'features': len(features), 'rows': len(rows), 'incomplete_required_rows': len(incomplete),
            'required_pairs': sum(a['status'] == 'required' for a in applicability.values()),
            'optional_pairs': sum(a['status'] == 'optional' for a in applicability.values()),
            'nonapplicable_pairs': sum(a['status'] == 'not-applicable' for a in applicability.values()),
            'reviewed': ledger['reviewed']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = validate(read_json(args.ledger), args.root, args.require_complete)
    except (InventoryError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
