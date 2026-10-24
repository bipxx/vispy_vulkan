# SPDX-License-Identifier: AGPL-3.0-only
"""Validate a concrete development candidate before review or another build.

This preparation format deliberately cannot represent wheel qualification.
Canonical obligations, auditors, independent controls and promotion gates remain
authoritative; a validated proposal neither transfers nor discharges an origin.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

try:
    from .compatibility_inventory import (ROOT, SPEC, InventoryError, check, file_ref,
                                          fixture_exists, read_json, shape, unique_by, validate)
    from .compatibility_conservation import digest
except ImportError:
    from compatibility_inventory import (ROOT, SPEC, InventoryError, check, file_ref,
                                         fixture_exists, read_json, shape, unique_by, validate)
    from compatibility_conservation import digest

DEFAULT = ROOT / 'compat/candidates/tk-state-resource-1/candidate.json'
PREPARATION_TOOLS = (
    'tools/compatibility_candidate.py', 'tools/compatibility_inventory.py',
    'tools/compatibility_conservation.py', 'tools/compatibility_evidence.py',
    'tools/compatibility_coverage.py', 'compat/vispy-coverage.schema.json',
    'tools/no_opengl/policy.py', SPEC,
    'compat/vispy-candidate.schema.json', 'compat/vispy-compatibility.schema.json',
    'compat/vispy-compatibility-v3.schema.json', 'cmake/runtime_package.py',
    '.github/workflows/cpu-contract.yml',
)


def scope_digest(candidate):
    return digest({k: v for k, v in candidate.items() if k not in ('manifest_sha256', 'reviews')})


def seal(candidate):
    candidate['manifest_sha256'] = digest({k: v for k, v in candidate.items() if k != 'manifest_sha256'})
    return candidate


def observer_recipe(workflow):
    command = ['{controller_python}', 'tools/audit_no_opengl.py', 'run',
               '--python', '{consumer_python}', '--wheel', '{wheel}',
               '--scenario', 'script', '--script', workflow['script']['path'],
               '--workflow-id', workflow['id']]
    for feature in workflow['features']:
        command.extend(['--covered-feature', feature])
    command.extend(['--dependencies-report', '{dependency_report}', '--policy', 'deny',
                    '--output', '{evidence_dir}/' + workflow['id'] + '.json'])
    return command


def validate_candidate(candidate, root=ROOT, require_reviewed=False):
    root = Path(root)
    schema = read_json(ROOT / 'compat/vispy-candidate.schema.json')
    shape(candidate, schema, schema['$defs'])
    check(candidate['manifest_sha256'] == digest({k: v for k, v in candidate.items() if k != 'manifest_sha256'}),
          'candidate manifest identity changed')
    preparation_tools = unique_by(candidate['preparation_tools'], lambda r: r['path'], 'preparation tool')
    check(set(preparation_tools) == set(PREPARATION_TOOLS), 'incomplete preparation verifier/tool identities')
    for reference in preparation_tools.values():
        file_ref(root, reference)
    ledger = read_json(file_ref(root, candidate['ledger']))
    inventory = validate(ledger, root)
    check(candidate['upstream_commit'] == ledger['upstream_commit'], 'candidate upstream pin changed')
    matrix_path = file_ref(root, candidate['matrix'])
    check(candidate['matrix'] in ledger['related_inventories'], 'candidate host matrix is not the canonical obligation')
    matrix = read_json(matrix_path)
    mandatory = {row['id'] for row in matrix['rows'] if row.get('mandatory')}
    check(len(candidate['required_host_rows']) == len(set(candidate['required_host_rows']))
          and set(candidate['required_host_rows']) == mandatory, 'mandatory host obligation removed or duplicated')
    inputs = read_json(file_ref(root, candidate['runtime_inputs']))
    check(isinstance(inputs, dict) and set(inputs) == {'schema', 'source_commit', 'python', 'native', 'locks', 'licenses', 'build'}
          and type(inputs['schema']) is int and inputs['schema'] == 1, 'unknown runtime input record')
    check(inputs['source_commit'] == candidate['product_source_commit'], 'runtime source commit mismatch')
    sys.path.insert(0, str(ROOT / 'cmake'))
    from runtime_package import source_package_hashes
    expected_python = source_package_hashes(root)
    python = unique_by(inputs['python'], lambda r: r['member'], 'runtime member')
    check(set(python) == set(expected_python), 'incomplete or extra runtime source members')
    for name, expected in expected_python.items():
        record = python[name]
        check(set(record) == {'member', 'file'}, 'unknown runtime member fields')
        expected_path = ('compat/runtime-package.json' if name == 'vispy/_runtime_package.json'
                         else 'src/' + name)
        check(record['file']['path'] == expected_path and record['file']['sha256'] == expected,
              'runtime source member identity mismatch')
        file_ref(root, record['file'])
    native = unique_by(inputs['native'], lambda r: r['path'], 'native input')
    expected_native = {p.relative_to(root).as_posix() for p in (root / 'cpp').rglob('*')
                       if p.is_file() and p.suffix in ('.cpp', '.hpp', '.h')}
    check(set(native) == expected_native and expected_native, 'incomplete native source/header inputs')
    for reference in [*native.values(), *inputs['locks']]:
        file_ref(root, reference)
    check({r['path'] for r in inputs['locks']} == {'uv.lock', 'cmake/dependencies.lock.json'},
          'candidate lock set changed')
    contract = read_json(root / 'compat/runtime-package.json')
    check({'LICENSE', 'LICENSE-BSD', 'LICENSING.md'} <= set(contract['notice_files']),
          'implementation/original licensing notices removed')
    expected_licenses = {name if name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md')
                         else 'third_party/licenses/' + name for name in contract['notice_files']}
    licenses = unique_by(inputs['licenses'], lambda r: r['path'], 'license input')
    check(set(licenses) == expected_licenses, 'incomplete original/shipping license inputs')
    for reference in licenses.values():
        file_ref(root, reference)
    expected_build = {'CMakeLists.txt', 'pyproject.toml'}
    expected_build.update(p.relative_to(root).as_posix() for p in (root / 'cmake').rglob('*')
                          if p.is_file() and p.suffix in ('.cmake', '.py', '.in'))
    expected_build.update(p.relative_to(root).as_posix() for p in (root / 'src/vispy').rglob('*')
                          if p.is_file() and p.suffix in ('.pyx', '.pxd'))
    build = unique_by(inputs['build'], lambda r: r['path'], 'build input')
    check(set(build) == expected_build, 'incomplete build recipe/native extension source inputs')
    for reference in build.values():
        file_ref(root, reference)
    profiles = unique_by(candidate['profiles'], lambda p: p['id'], 'candidate profile')
    for profile in profiles.values():
        observation = read_json(file_ref(root, profile['observation']))
        check(isinstance(observation, dict), 'profile observation must be an object')
        check(profile['install'] == ['uv', 'pip', 'install', '--python', '{consumer_python}',
                                     '--no-deps', '{wheel}'], 'candidate install recipe differs')
        check(observation.get('id') == profile['id'] and observation.get('phase') == 'source-functional',
              'wrong profile observation or claimed installed admission')
        check(observation.get('product_runtime_source_commit') == candidate['product_source_commit'],
              'profile source runtime mismatch')
        check(observation.get('native_inputs_sha256') == digest(inputs['native']), 'profile native inputs changed')
        check(isinstance(observation.get('python_version'), str)
              and observation['python_version'].startswith('3.12.')
              and isinstance(observation.get('interpreter_sha256'), str)
              and re.fullmatch('[0-9a-f]{64}', observation['interpreter_sha256'])
              and isinstance(observation.get('native_sha256'), str)
              and re.fullmatch('[0-9a-f]{64}', observation['native_sha256'])
              and isinstance(observation.get('os_identity'), str) and observation['os_identity'].strip(),
              'profile lacks concrete interpreter/native/OS identities')
        check(observation.get('python_abi') == 'cp312' and observation.get('architecture') == 'x86_64',
              'profile ABI/architecture not the observed candidate')
        try:
            from .no_opengl.policy import LIVE_GAUGES
        except ImportError:
            from no_opengl.policy import LIVE_GAUGES
        observation_result = observation.get('source_observation', {})
        check(isinstance(observation_result, dict), 'source observation must be an object')
        gauges = observation_result.get('shutdown_gauges', {})
        check(type(observation_result.get('cases')) is int and observation_result['cases'] > 0
              and isinstance(gauges, dict) and set(gauges) == set(LIVE_GAUGES)
              and all(type(value) is int and value == 0 for value in gauges.values()),
              'source profile lacks recorded zero-gauge functional observation')
        kind, device = observation.get('kind'), observation.get('device', {})
        check(isinstance(device, dict) and device.get('backend') == 'Vulkan', 'candidate profile is not observed Vulkan')
        check((kind == 'windows-gpu' and device.get('software') is False)
              or (kind == 'wsl-software' and device.get('software') is True),
              'software/hardware profile scope mismatch')
        check(observation.get('display_mode') == 'tk-raster', 'profile display mode mismatch')
        prefix = 'windows-' if kind == 'windows-gpu' else 'wsl-'
        prior = {r.get('artifact_sha256') for r in matrix['rows']
                 if r['id'].startswith(prefix) and r.get('status') == 'QUALIFIED'}
        check(profile['previous_qualified_wheel_sha256'] in prior, 'previous wheel is not qualified for this platform')
    proposals = unique_by(candidate['proposals'], lambda p: p['id'], 'proposed feature')
    check(not (set(proposals) & {f['id'] for f in ledger['features']}),
          'scoped proposal overwrites an existing broad feature')
    seed_pairs = {(p['feature'], p['profile']) for p in ledger['applicability'] if p['status'] == 'required'}
    upstream = read_json(root / 'compat/upstream_manifest.json')
    requirements = set(re.findall(r'\b(?:EV|INV|TK|STATE|SH|BACKEND|HOST|ART|HW|PERF|RET|LIC)-\d+\b',
                                  (root / SPEC).read_text(encoding='utf-8')))
    for proposal in proposals.values():
        check(proposal['scope'].strip() and all(s.strip() for s in proposal['excluded']), 'blank proposal scope')
        check(set(proposal['requirements']) <= requirements, 'unknown candidate requirement')
        check(all((o['feature'], o['profile']) in seed_pairs for o in proposal['origins']),
              'proposal references a missing/nonrequired origin')
        for source in proposal['upstream_sources']:
            check(upstream['files'].get(source['path']) == source['sha256'], 'proposal upstream source changed')
    pairs = unique_by(candidate['pairs'], lambda p: (p['feature'], p['profile']), 'proposal/profile pair')
    check(set(pairs) == {(f, p) for f in proposals for p in profiles}, 'missing concrete required proposal/profile pair')
    visiting, visited = set(), set()

    def visit(key):
        check(key not in visiting, 'cyclic candidate dependency')
        if key in visited:
            return
        visiting.add(key)
        for dependency in pairs[key]['dependencies']:
            check((dependency, key[1]) in pairs and dependency != key[0], 'dangling/self candidate dependency')
            visit((dependency, key[1]))
        visiting.remove(key)
        visited.add(key)

    for key in pairs:
        visit(key)
    workflows = unique_by(candidate['workflows'], lambda w: w['id'], 'candidate workflow')
    covered = set()
    for workflow in workflows.values():
        file_ref(root, workflow['script'])
        check(set(workflow['profiles']) <= set(profiles) and set(workflow['features']) <= set(proposals),
              'workflow has unknown profile/feature')
        check({'ordinary', 'mutation', 'failure', 'recovery'} <= {a['kind'] for a in workflow['acceptance']},
              'candidate workflow lacks ordinary/mutation/failure/recovery acceptance')
        check(workflow['launch'] == ['{consumer_python}', workflow['script']['path']],
              'launch command differs from pinned script')
        check(workflow['observer'] == observer_recipe(workflow),
              'observer recipe differs from exact installed workflow/feature binding')
        for feature in workflow['features']:
            for profile in workflow['profiles']:
                check(set(pairs[(feature, profile)]['dependencies']) <= set(workflow['features']),
                      'observed workflow omits required same-profile dependency')
        for acceptance in workflow['acceptance']:
            check(acceptance['source']['path'] == acceptance['nodeid'].split('::', 1)[0],
                  'acceptance source differs from fixture node')
            file_ref(root, acceptance['source'])
            fixture_exists(root, acceptance['nodeid'])
        covered.update((feature, profile) for feature in workflow['features'] for profile in workflow['profiles'])
    check(covered == set(pairs), 'proposed required pair has no actual workflow')
    reviews = []
    for kind, reference in candidate['reviews'].items():
        if reference is None:
            continue
        review = read_json(file_ref(root, reference))
        check(isinstance(review, dict) and type(review.get('schema')) is int
              and review['schema'] == 1 and review.get('status') == 'APPROVED'
              and review.get('kind') == kind and review.get('independent') is True
              and isinstance(review.get('reviewer'), str) and review['reviewer'].strip()
              and review.get('candidate_scope_sha256') == scope_digest(candidate), 'stale/wrong candidate review')
        reviews.append(kind)
    reviewed = set(reviews) == {'source', 'scope'}
    check(not require_reviewed or reviewed, 'candidate source and scope review remain pending')
    return {'status': 'VALID_PREPARATION', 'candidate': candidate['id'], 'proposed_pairs': len(pairs),
            'canonical_required_pairs_preserved': inventory['required_pairs'], 'workflows': len(workflows),
            'reviewed': reviewed, 'installable': False, 'qualified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=DEFAULT)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--require-reviewed', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = validate_candidate(read_json(args.candidate), args.root, args.require_reviewed)
    except (InventoryError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
