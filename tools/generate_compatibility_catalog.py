# SPDX-License-Identifier: AGPL-3.0-only
"""Create a draft public-workflow ledger from verified pinned package sources.

Explicit invocation only; refuses to replace an existing ledger. This bootstrap
does not infer support from Python availability and does not qualify any row.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

try:
    from .compatibility_inventory import ROOT, read_json, check
except ImportError:
    from compatibility_inventory import ROOT, read_json, check

NAMESPACES = {
    'app/__init__.py': ('python-hosts', ['TK-1', 'TK-2', 'TK-6']),
    'gloo/__init__.py': ('native', ['INV-3', 'STATE-2']),
    'visuals/__init__.py': ('native', ['INV-3']),
    'visuals/filters/__init__.py': ('native', ['INV-3', 'SH-4']),
    'visuals/shaders/__init__.py': ('native', ['INV-3', 'SH-1', 'SH-2', 'SH-3', 'SH-5']),
    'visuals/transforms/__init__.py': ('python-hosts', ['INV-3']),
    'scene/cameras/__init__.py': ('python-hosts', ['INV-3', 'TK-6']),
    'scene/widgets/__init__.py': ('python-hosts', ['INV-3', 'TK-7']),
    'scene/__init__.py': ('python-hosts', ['INV-3']),
}


def exports(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module != '__future__':
            names.update(alias.asname or alias.name for alias in node.names
                         if alias.name != '*' and not (alias.asname or alias.name).startswith('_'))
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
            names.add(node.name)
    return sorted(names)


def generate(source, root=ROOT):
    manifest = read_json(root / 'compat/upstream_manifest.json')
    features = []
    def verified(relative):
        data = (source / relative).read_bytes()
        check(hashlib.sha256(data).hexdigest() == manifest['files'][relative], f'upstream source mismatch: {relative}')
        return ast.parse(data)
    def add(entry, relative, owner, requirements, capability):
        identifier = entry.lower().replace('vispy.', '', 1).replace('_', '-')
        existing = next((feature for feature in features if feature['id'] == identifier), None)
        if existing is not None:
            check(existing['entry_point'] == entry, f'colliding public names: {entry}')
            source_pin = {'path': relative, 'sha256': manifest['files'][relative]}
            if source_pin not in existing['upstream_sources']:
                existing['upstream_sources'].append(source_pin)
            existing['requirements'] = sorted(set(existing['requirements']) | set(requirements))
            existing['capabilities'] = sorted(set(existing['capabilities']) | {capability})
            return
        features.append({
            'id': identifier, 'entry_point': entry,
            'upstream_sources': [{'path': relative, 'sha256': manifest['files'][relative]}],
            'requirements': requirements, 'capabilities': [capability], 'dependencies': [],
            'required': True, 'scope_reason': 'Pinned public export/workflow; acceptance and required profiles need review.',
            'ordinary': f'Exercise {entry} end to end with independently expected public behavior.',
            'mutation': 'Verify an important update/input or failure/recovery lifecycle without losing output/ownership.',
            'owner': owner,
        })
    for relative, (owner, requirements) in NAMESPACES.items():
        namespace = 'vispy.' + relative.removesuffix('/__init__.py').replace('/', '.')
        for name in exports(verified(relative)):
            add(namespace + '.' + name, relative, owner, requirements, 'public-workflow')
    # gloo's wildcard exports must be expanded rather than silently skipped.
    relative = 'gloo/wrappers.py'
    wrapper_tree = verified(relative)
    for name in exports(wrapper_tree):
        if any(isinstance(node, ast.FunctionDef) and node.name == name for node in wrapper_tree.body):
            add('vispy.gloo.' + name, relative, 'native', ['STATE-1', 'STATE-2', 'STATE-4'], 'state-submission')
    relative = 'app/backends/__init__.py'
    for node in verified(relative).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('CORE_BACKENDS', 'PSEUDO_BACKENDS') for t in node.targets):
            for name, module, _ in ast.literal_eval(node.value):
                if name != '_test':
                    add('vispy.app.backend.' + name.lower(), relative, 'python-hosts', ['BACKEND-1', 'BACKEND-2'], 'backend-presentation')
    inventories = ('compat/upstream_manifest.json', 'tests/reference/inventory.json', 'compat/no-opengl-matrix.json')
    return {
        'schema': 1, 'upstream_commit': manifest['upstream_commit'], 'reviewed': False,
        'scope': 'Generated public namespace/registered-backend seed, not a complete reviewed upstream inventory. Wildcard scene aliases, method-level contracts, representative examples, events, host workflows and raw interoperation still require reconciliation. No support percentage or promotion follows from this seed.',
        'related_inventories': [{'path': name, 'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()} for name in inventories],
        'capabilities': ['public-workflow', 'state-submission', 'backend-presentation'],
        'profiles': [{'id': 'unassigned', 'description': 'No concrete environment/artifact admitted; review and split into actual profile rows.', 'admitted': False, 'environment_sha256': None}],
        'required_profiles': ['unassigned'],
        'features': sorted(features, key=lambda feature: feature['id']),
        'rows': [{'feature': feature['id'], 'profile': 'unassigned', 'state': 'not-inventoried',
                  'outcome': 'not-run', 'fixtures': [], 'identity': None, 'receipt': None,
                  'blocker': 'Generated seed; real acceptance fixture/profile mapping has not been reviewed.',
                  'next_action': 'Reconcile existing fixtures and host evidence; select ordinary/mutation cases and concrete required profiles.'}
                 for feature in sorted(features, key=lambda feature: feature['id'])],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Existing immutable upstream vispy package directory')
    parser.add_argument('--output', type=Path, default=ROOT / 'compat/vispy-compatibility.json')
    args = parser.parse_args()
    ledger = generate(args.source)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(ledger, stream, indent=2)
        stream.write('\n')
    print(f'Created {len(ledger["features"])} draft feature rows; reviewed=false, no positive claims')


if __name__ == '__main__':
    main()
