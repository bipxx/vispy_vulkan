# SPDX-License-Identifier: AGPL-3.0-only
"""Record the actual graphics scenario and collector bytes without loading it."""
import hashlib
from pathlib import Path


def arguments(values):
    """Consume the CLI boundary once; preserve literal '--' script arguments."""
    values = list(values)
    return values[1:] if values[:1] == ['--'] else values


def describe(args):
    script = args.script if args.scenario == 'script' else None
    if args.scenario == 'script' and script is None:
        raise ValueError('--script is required for script scenario')
    return {'id': getattr(args, 'workflow_id', None) or args.scenario,
            'scenario': args.scenario, 'binding': args.binding,
            'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest() if script else None,
            'arguments': arguments(args.arguments),
            'features': sorted(set(getattr(args, 'covered_feature', [])))}


def collector_identity(args):
    root = Path(__file__).resolve().parents[2]
    sources = [root / 'tools/audit_no_opengl.py', root / 'cmake/runtime_package.py']
    sources.extend(path for path in (root / 'tools/no_opengl').iterdir() if path.suffix in ('.py', '.c'))
    native = [getattr(args, name, None) for name in ('native_auditor', 'native_debugger')]
    return {'sources': {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(sources)},
            'native_tools': {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in native if path is not None}}
