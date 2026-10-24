"""Bind installed inventory, dependency graph and an admitted native trace."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from .dependencies import dependency_closure


def build(args):
    wheel = args.wheel.resolve(strict=True)
    python = args.python.absolute()
    python.resolve(strict=True)  # Validation only: launching its realpath loses Linux venv semantics.
    runtime_path = args.runtime_report.resolve(strict=True)
    runtime = json.loads(runtime_path.read_text())
    worker_path = Path(runtime['worker_report']).resolve(strict=True)
    worker = json.loads(worker_path.read_text())
    wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
    admitted = (runtime.get('scenario') in ('headless', 'qt', 'script') and not runtime.get('source_mode')
                and worker.get('status') == 'PASS_SCENARIO' and not worker.get('error') and not worker.get('cleanup_error')
                and worker.get('wheel_sha256') == wheel_hash and worker.get('wheel_members_verified', 0) > 0
                and Path(worker['executable']).resolve() == python.resolve()
                and runtime.get('workflow') is not None and runtime['workflow'] == worker.get('workflow')
                and runtime.get('child_waited') is True
                and runtime.get('worker_report_sha256') == hashlib.sha256(worker_path.read_bytes()).hexdigest()
                and all(runtime.get('gates', {}).get(key) == 'PASS' for key in ('no_gl_execution', 'no_gl_loads')))
    inventory_path = args.output.resolve().with_suffix('.inventory.json')
    if inventory_path.exists():
        raise ValueError('Fresh consumer inventory required')
    result = subprocess.run([str(python), '-I', '-B', str(Path(__file__).with_name('inventory.py').resolve()),
                             '--wheel', str(wheel), '--output', str(inventory_path)], capture_output=True, text=True)
    inventory = json.loads(inventory_path.read_text())
    if result.returncode or inventory.get('status') != 'PASS_INVENTORY':
        return {'schema': 1, 'status': 'FAIL', 'gate': 'FAIL', 'wheel_sha256': wheel_hash,
                'inventory': str(inventory_path), 'inventory_result': inventory,
                'errors': ['Installed consumer inventory failed'], 'coverage': {}}
    paths = [row['path'] for row in runtime.get('native_observer', {}).get('events', []) if row['kind'] == 'native_load' and row.get('path')]
    roots = {Path(row['path']).resolve(strict=True) for row in inventory['native_files']}
    roots |= {Path(path).resolve(strict=True) for path in paths if Path(path).is_file()}
    roots.add(python)
    directories = set(path.parent for path in roots)
    directories.update(path.resolve(strict=True) for path in args.search_dir)
    base = Path(inventory['base_prefix'])
    directories.update(path for path in (base, base / 'DLLs', base / 'lib') if path.is_dir())
    api_namespace = None
    if sys.platform == 'win32':
        from .windows_contracts import namespace
        api_namespace = namespace()
        directories.add((Path(os.environ['SystemRoot']) / 'System32').resolve(strict=True))
    else:
        directories.update(path for value in ('/lib/x86_64-linux-gnu', '/usr/lib/x86_64-linux-gnu', '/lib64') if (path := Path(value)).is_dir())
    closure = dependency_closure(sorted(roots), sorted(directories))
    optional, blocking = [], []
    for edge in closure['unresolved']:
        evidence = None
        if admitted and 'parent' in edge and sys.platform == 'win32':
            from .windows_contracts import absent_os_delay
            evidence = absent_os_delay(edge, binaries=closure['binaries'], runtime_paths=paths, api_namespace=api_namespace)
        (optional if evidence else blocking).append(evidence or edge)
    gate = 'FAIL' if closure['violations'] else ('PASS' if admitted and not blocking else 'UNVERIFIED')
    return {'schema': 1, 'status': gate, 'gate': gate, 'wheel_sha256': wheel_hash,
            'discovery_workflow': runtime.get('workflow'), 'collector_identity': runtime.get('collector_identity'),
            'environment_id': inventory['environment_id'], 'consumer_executable': inventory['executable'],
            'inventory': str(inventory_path), 'inventory_sha256': hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
            'runtime_report': str(runtime_path), 'runtime_report_sha256': hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
            'worker_report_sha256': hashlib.sha256(worker_path.read_bytes()).hexdigest(), 'admitted_runtime_evidence': admitted,
            'raw_declared_closure': closure, 'blocking_unresolved': blocking, 'absent_optional_os_dependencies': optional,
            'windows_api_set_namespace': api_namespace,
            'coverage': {'environment_without_gl_packages': True, 'exact_installed_wheel_bytes': True,
                         'selected_candidate_requirements': gate == 'PASS', 'complete_arbitrary_os_extension_closure': not closure['unresolved']},
            'scope': 'Exact installed candidate/native dependency inventory plus traced admitted flow. Windows OS GL component presence is allowed; '
                     'absent Windows OS delay branches remain raw-closure unresolved, with OS-file/version/namespace/resolver/unused-flow evidence. '
                     'No candidate unresolved import or GL-named import is waived. Linux system packages/files are separately inventoried.'}
