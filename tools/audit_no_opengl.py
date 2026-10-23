"""Audit candidate binary dependencies and fresh-process OpenGL activity.

An incomplete collector returns UNVERIFIED, never a no-OpenGL pass. Candidate
runtime execution and the GL-free installed environment are distinct evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from no_opengl.dependencies import dependency_closure
from no_opengl.policy import assess, import_reason, library_reason


def run_candidate(args):
    report_path = args.output.resolve()
    worker = report_path.with_suffix('.worker.json')
    assert not worker.exists(), 'Fresh worker report required'
    command = [str(args.python), '-I', '-B', str(Path(__file__).parent / 'no_opengl/probe.py'),
               '--output', str(worker), '--scenario', args.scenario, '--policy', args.policy]
    for name in ('binding', 'source_root', 'wheel', 'script'):
        value = getattr(args, name)
        if value is not None:
            command.extend(['--' + name.replace('_', '-'), str(value)])
    for path in args.dependency_path:
        command.extend(['--dependency-path', str(path)])
    if args.arguments:
        command.extend(['--', *args.arguments])
    environment = os.environ.copy()
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE'):
        environment.pop(key, None)
    log = report_path.with_suffix('.process.log')
    native = {'events': [], 'coverage': {}, 'errors': []}
    if sys.platform == 'win32':
        from no_opengl.windows import trace
        native = trace(command, environment=environment, cwd=report_path.parent, log=log, timeout=args.timeout)
        code = native['process_exit']
    elif sys.platform.startswith('linux') and args.native_auditor:
        from no_opengl.linux import trace
        native = trace(command, auditor=args.native_auditor, environment=environment,
                       cwd=report_path.parent, log=log,
                       trace_path=report_path.with_suffix('.loader.tsv'), timeout=args.timeout)
        code = native['process_exit']
    else:
        with log.open('wb') as stream:
            process = subprocess.run(command, env=environment, cwd=report_path.parent,
                                     stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
        code = process.returncode
        native['coverage'] = {'startup_and_transient_native_loads': False, 'native_public_gl_export_breakpoints': False}
        native['errors'] = [{'error': 'No native observer available; Python hooks and snapshots alone cannot prove absence'}]
    child_report = json.loads(worker.read_text()) if worker.exists() else {'status': 'MISSING_WORKER_REPORT', 'events': []}
    events = [*native['events'], *child_report['events']]
    for snapshot in child_report.get('snapshots', []):
        for path in snapshot['paths']:
            if library_reason(path):
                events.append({'kind': 'native_load', 'path': path, 'observation': 'module snapshot', 'phase': snapshot['phase']})
    succeeded = code == 0 and child_report['status'] == 'PASS_SCENARIO'
    gates = assess(events, native_loads_complete=native['coverage'].get('startup_and_transient_native_loads', False),
                   native_api_complete=all(native['coverage'].get(name, False) for name in
                       ('native_public_gl_export_breakpoints', 'native_entrypoint_resolution', 'process_tree')),
                   execution_succeeded=succeeded)
    gates['no_gl_install_link_requirement'] = 'UNVERIFIED'
    if args.dependencies_report:
        dependencies = json.loads(args.dependencies_report.read_text())
        gates['no_gl_install_link_requirement'] = dependencies.get('gate', 'UNVERIFIED')
        # A declared binary closure alone cannot establish the installed package
        # environment, and must bind to this exact wheel before integration.
        if not dependencies.get('coverage', {}).get('environment_without_gl_packages') or not args.wheel or dependencies.get('wheel_sha256') != hashlib.sha256(args.wheel.read_bytes()).hexdigest():
            if gates['no_gl_install_link_requirement'] != 'FAIL':
                gates['no_gl_install_link_requirement'] = 'UNVERIFIED'
    imports_pass = succeeded and not child_report.get('forbidden_modules_present') and not any(
        row['kind'] == 'python_import' for row in gates['violations'])
    if gates['violations'] or not succeeded:
        status = 'FAIL'
    elif args.gates == 'imports':
        status = 'PASS_IMPORT_GATE_ONLY' if imports_pass else 'FAIL'
    elif not args.source_root and args.wheel and child_report.get('wheel_sha256') == hashlib.sha256(args.wheel.read_bytes()).hexdigest() and all(gates[name] == 'PASS' for name in ('no_gl_execution', 'no_gl_loads', 'no_gl_install_link_requirement')):
        status = 'PASS_ALL_NO_OPENGL_GATES'
    else:
        status = 'UNVERIFIED'
    return {'status': status, 'scenario': args.scenario, 'source_mode': bool(args.source_root), 'process_exit': code,
            'gates': gates, 'imports_gate_passed': imports_pass, 'native_observer': native,
            'worker_report': str(worker), 'worker_status': child_report['status'],
            'scope': 'All three gates require same-artifact installed runtime and environment evidence; source probes never establish artifact qualification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    dependencies = sub.add_parser('dependencies')
    dependencies.add_argument('--root', type=Path, action='append', default=[])
    dependencies.add_argument('--search-dir', type=Path, action='append', default=[])
    dependencies.add_argument('--qt-root', type=Path)
    dependencies.add_argument('--wheel', type=Path)
    dependencies.add_argument('--output', type=Path, required=True)
    run = sub.add_parser('run')
    run.add_argument('--python', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--scenario', choices=('import', 'headless', 'qt', 'script'), default='import')
    run.add_argument('--binding', choices=('pyqt5', 'pyqt6', 'pyside6'))
    run.add_argument('--source-root', type=Path)
    run.add_argument('--dependency-path', type=Path, action='append', default=[])
    run.add_argument('--wheel', type=Path)
    run.add_argument('--script', type=Path)
    run.add_argument('--native-auditor', type=Path)
    run.add_argument('--dependencies-report', type=Path)
    run.add_argument('--policy', choices=('observe', 'deny'), default='deny')
    run.add_argument('--gates', choices=('all', 'imports'), default='all')
    run.add_argument('--timeout', type=float, default=120)
    run.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        parser.error('A new output report path is required')
    if args.mode == 'dependencies':
        roots, directories = list(args.root), list(args.search_dir)
        if args.qt_root:
            qt = args.qt_root.resolve(strict=True)
            found = [*qt.glob('bin/Qt?Gui.dll'), *qt.glob('Qt?Gui.dll'), *qt.glob('plugins/platforms/qwindows.dll'),
                     *qt.glob('lib/libQt?Gui.so.*'), *qt.glob('plugins/platforms/libqxcb.so')]
            roots.extend(found)
            directories.extend(p for p in (qt / 'bin', qt / 'lib', qt) if p.is_dir())
            if not found:
                parser.error('No selected QtGui/platform roots found under --qt-root')
        wheel_sha = None
        if args.wheel:
            wheel_sha = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
            extracted = args.output.parent / (args.output.stem + '-wheel-native')
            extracted.mkdir(exist_ok=False)
            with zipfile.ZipFile(args.wheel) as archive:
                for name in archive.namelist():
                    if name.startswith('vispy/') and name.endswith(('.dll', '.pyd', '.so')):
                        relative = Path(name)
                        if '..' in relative.parts or relative.is_absolute():
                            raise ValueError('Invalid wheel member')
                        path = extracted / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(archive.read(name))
                        roots.append(path)
            directories.extend({p.parent for p in roots})
        if not roots:
            parser.error('Provide --root, --qt-root or --wheel')
        report = dependency_closure(roots, directories)
        report.update(status=report['gate'], wheel_sha256=wheel_sha)
    else:
        report = run_candidate(args)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], args.output, flush=True)
    return 0 if report['status'] in ('PASS', 'PASS_IMPORT_GATE_ONLY', 'PASS_ALL_NO_OPENGL_GATES') else (1 if report['status'] == 'FAIL' else 2)


if __name__ == '__main__':
    raise SystemExit(main())
