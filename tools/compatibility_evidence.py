# SPDX-License-Identifier: AGPL-3.0-only
"""Normalize existing graphics qualification reports with workflow coverage.

This reads evidence only. It never runs or replaces the installed-distribution
auditor, native observer, dependency resolver or independent control protocol.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

try:
    from .compatibility_inventory import ROOT, GATES, check, file_ref, read_json
    from .no_opengl.policy import LIVE_GAUGES
except ImportError:
    from compatibility_inventory import ROOT, GATES, check, file_ref, read_json
    from no_opengl.policy import LIVE_GAUGES

CORE_CONTROLS = ('safe_control_exits_zero', 'safe_control_has_no_gl_violation',
                 'native_lookup_without_call_detected', 'transient_forbidden_load_detected',
                 'transient_unload_observed', 'no_collector_errors',
                 'native_direct_call_detected', 'exec_child_native_call_detected')
COVERAGE = ('startup_and_transient_native_loads', 'native_public_gl_export_breakpoints',
            'native_entrypoint_resolution', 'process_tree')


def expected_workflow(root, row):
    workflow = row.get('workflow')
    check(workflow is not None, 'qualified row lacks reviewed workflow mapping')
    script = workflow['script']
    if workflow['scenario'] == 'script':
        check(script is not None, 'script workflow lacks script identity')
        file_ref(root, script)
    else:
        check(script is None and not workflow['arguments'], 'builtin workflow cannot claim a script or ignored arguments')
    check(workflow['scenario'] != 'qt' or workflow['binding'] is not None, 'Qt workflow lacks a selected binding')
    return {'id': workflow['id'], 'scenario': workflow['scenario'], 'binding': workflow['binding'],
            'script_sha256': script['sha256'] if script else None, 'arguments': workflow['arguments']}


def normalize(root, row, references):
    root = Path(root)
    required = {'runtime', 'worker', 'dependencies', 'inventory', 'discovery', 'discovery_worker', 'controls', 'control_reports'}
    check(set(references) == required, 'incomplete raw qualification report bundle')
    read = lambda ref: read_json(file_ref(root, ref))
    raw = {name: read(references[name]) for name in required - {'control_reports'}}
    check(all(isinstance(value, dict) for value in raw.values()), 'raw qualification reports must be JSON objects')
    expected = expected_workflow(root, row)
    wheel = row['identity']['wheel_sha256']
    check(wheel is not None, 'qualification requires an installed wheel')
    runtime, worker = raw['runtime'], raw['worker']
    discovery, previous = raw['discovery'], raw['discovery_worker']
    dependencies, inventory, controls = raw['dependencies'], raw['inventory'], raw['controls']
    workflow = runtime.get('workflow')
    check(discovery.get('status') in ('UNVERIFIED', 'PASS_ALL_NO_OPENGL_GATES'), 'discovery was failed or import-only')
    check(isinstance(workflow, dict) and set(workflow) == set(expected) | {'features'}, 'missing observed workflow identity')
    check({key: workflow[key] for key in expected} == expected, 'observed workflow does not match reviewed scenario/script/arguments')
    features = workflow['features']
    check(isinstance(features, list) and all(isinstance(name, str) for name in features)
          and len(set(features)) == len(features) and row['feature'] in features,
          'observed workflow does not cover the claimed feature')
    for report, child, child_name in ((runtime, worker, 'worker'), (discovery, previous, 'discovery_worker')):
        check(report.get('workflow') == child.get('workflow') == workflow, 'controller/worker/discovery workflows differ')
        check(report.get('scenario') == child.get('scenario') == expected['scenario'], 'scenario label differs from actual workflow')
        check(report.get('source_mode') is False and child.get('source_mode') is False, 'source probes cannot qualify installed workflows')
        check(type(report.get('process_exit')) is int and report['process_exit'] == 0 and report.get('child_waited') is True,
              'runtime process failed or was not waited')
        check(report.get('worker_report_sha256') == references[child_name]['sha256'], 'runtime binds a different worker report')
        check(child.get('status') == 'PASS_SCENARIO' and not child.get('error') and not child.get('cleanup_error'), 'worker scenario/cleanup failed')
        check(child.get('wheel_sha256') == wheel and type(child.get('wheel_members_verified')) is int
              and child['wheel_members_verified'] > 0, 'worker lacks exact installed member audit')
        check(not child.get('forbidden_modules_present') and child.get('native_cleanup_performed') is True
              and all(type(child.get('after_shutdown', {}).get(key)) is int and child['after_shutdown'][key] == 0 for key in LIVE_GAUGES),
              'worker lacks clean native shutdown')
        native = report.get('native_observer', {})
        check(type(native.get('process_exit')) is int and native['process_exit'] == 0 and not native.get('errors')
              and all(native.get('coverage', {}).get(key) is True for key in COVERAGE), 'incomplete native observer coverage')
        check(not report.get('gates', {}).get('violations') and all(report.get('gates', {}).get(key) == 'PASS'
              for key in ('no_gl_execution', 'no_gl_loads')), 'runtime absence gate failed or unverified')
    check(runtime.get('status') == 'PASS_ALL_NO_OPENGL_GATES'
          and runtime['gates'].get('no_gl_install_link_requirement') == 'PASS'
          and not runtime['gates'].get('loaded_files_outside_installed_receipt'), 'installed replay is not fully qualified')
    check(runtime.get('dependencies_report_sha256') == references['dependencies']['sha256'], 'replay used another dependency receipt')
    check(dependencies.get('status') == dependencies.get('gate') == 'PASS'
          and dependencies.get('admitted_runtime_evidence') is True
          and dependencies.get('wheel_sha256') == wheel and not dependencies.get('blocking_unresolved')
          and not dependencies.get('raw_declared_closure', {}).get('violations')
          and all(dependencies.get('coverage', {}).get(key) is True for key in
                  ('environment_without_gl_packages', 'exact_installed_wheel_bytes', 'selected_candidate_requirements')),
          'installed dependency audit failed or unverified')
    check(dependencies.get('runtime_report_sha256') == references['discovery']['sha256']
          and dependencies.get('worker_report_sha256') == references['discovery_worker']['sha256']
          and dependencies.get('inventory_sha256') == references['inventory']['sha256']
          and dependencies.get('discovery_workflow') == workflow, 'dependency inventory is not bound to the discovery workflow')
    environment = dependencies.get('environment_id')
    check(isinstance(environment, str) and re.fullmatch('[0-9a-f]{64}', environment)
          and worker.get('environment_id') == inventory.get('environment_id') == environment,
          'replay environment differs from installed inventory')
    check(inventory.get('status') == 'PASS_INVENTORY' and inventory.get('wheel_sha256') == wheel
          and type(inventory.get('wheel_members_verified')) is int and inventory['wheel_members_verified'] > 0
          and not any(inventory.get(key) for key in ('errors', 'gl_runtime_files', 'gl_requirements')),
          'installed distribution inventory failed')
    system = inventory.get('system_inventory') or {}
    check(not system.get('gl_runtime_files') and not system.get('gl_packages'), 'system inventory contains excluded GL runtimes')
    check(worker.get('executable_resolved') == previous.get('executable_resolved') == dependencies.get('consumer_executable')
          == inventory.get('executable') and bool(inventory.get('executable')), 'consumer interpreter identities differ')
    collector = runtime.get('collector_identity')
    check(isinstance(collector, dict) and set(collector) == {'sources', 'native_tools'}
          and collector == discovery.get('collector_identity') == controls.get('collector_identity')
          == dependencies.get('collector_identity'), 'observer/control identities differ')
    check({'tools/audit_no_opengl.py', 'tools/no_opengl/probe.py', 'tools/no_opengl/workflow.py', 'tools/no_opengl/policy.py'}
          <= set(collector['sources']), 'missing observer implementation identity')
    for path, digest in collector['sources'].items():
        file_ref(root, {'path': path, 'sha256': digest})
    check(isinstance(collector['native_tools'], dict) and all(isinstance(path, str) and path
          and isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest)
          for path, digest in collector['native_tools'].items()), 'invalid native observer tool identity')
    checks = controls.get('checks', {})
    check(controls.get('status') == 'PASS_CONTROLS' and set(CORE_CONTROLS) <= set(checks)
          and all(value is True for value in checks.values()), 'independent collector controls failed or incomplete')
    check({'safe', 'resolve', 'call', 'transient', 'child_call'} <= set(references['control_reports'])
          and set(references['control_reports']) == set(controls.get('reports', {}))
          == set(controls.get('reports_sha256', {})) and references['control_reports'], 'missing raw collector control reports')
    for name, ref in references['control_reports'].items():
        check(ref['sha256'] == controls['reports_sha256'][name], 'control report hash differs')
        read(ref)
    return {gate: {'schema': 1, 'gate': gate, 'status': 'PASS', 'identity': deepcopy(row['identity']),
                   'workflow': deepcopy(workflow), 'controls_passed': True, 'observer_identity': deepcopy(collector),
                   'raw_reports': deepcopy(references)} for gate in GATES}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--feature', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--raw-reports', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    ledger = read_json(args.ledger)
    matches = [row for row in ledger['rows'] if (row['feature'], row['profile']) == (args.feature, args.profile)]
    check(len(matches) == 1, 'select exactly one feature/profile row')
    gates = normalize(args.root, matches[0], read_json(args.raw_reports))
    destinations = {gate: args.output.with_name(args.output.stem + '.' + gate + '.json') for gate in GATES}
    check(not any(path.exists() for path in [args.output, *destinations.values()]), 'fresh normalization outputs required')
    references = {}
    for gate, path in destinations.items():
        relative = path.resolve().relative_to(args.root.resolve()).as_posix()
        with path.open('x', encoding='utf-8') as stream:
            json.dump(gates[gate], stream, indent=2)
            stream.write('\n')
        references[gate] = {'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump({'schema': 1, 'feature': args.feature, 'profile': args.profile, 'gates': references}, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'PASS_NORMALIZED', 'gates': list(gates)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
