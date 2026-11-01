# SPDX-License-Identifier: AGPL-3.0-only
"""Reference packets per napari version for the version-agnostic successor fixtures (decision D30).

The retained fixtures pin napari 0.9.2 in one assert and stay bound to their 0.9.2 packets (D6). A successor fixture is
the retained module without that pin. Its packets live in tests/reference/<base>-napari-<version>/, and each packet's
provenance names the napari version it was captured with, so the version is bound by the packet, not by the code.
"""
from __future__ import annotations

import ast
import importlib.metadata as metadata
import inspect
import json
import os
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / 'tests/reference'
CAPTURE = 'tools/oracle_napari_successor_capture.py'
LOCK_SNAPSHOT = 'host-lock.txt'  # each packet keeps the oracle's lock, so every checkout can verify it


def packet_dir(base: str, version: str, root: Path = REFERENCES) -> Path:
    return root / f'{base}-napari-{version}'


def recorded_version(directory: Path) -> str:
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    return manifest['provenance']['napari_version']


def packets(base: str, root: Path = REFERENCES) -> dict[str, Path]:
    """Every packet of this base, by napari version; each packet must record the version its name gives."""
    prefix = f'{base}-napari-'
    found = {}
    for directory in sorted(path for path in root.glob(prefix + '*') if path.is_dir()):
        version = directory.name[len(prefix):]
        recorded = recorded_version(directory)
        assert recorded == version, f'{directory.name} records napari {recorded}, not {version}'
        found[version] = directory
    return found


def installed_packet(base: str, version: str | None = None, root: Path = REFERENCES) -> Path:
    """The packet for this napari version (the installed one by default); never another version's packet."""
    version = version or metadata.version('napari')
    directory = packet_dir(base, version, root)
    assert (directory / 'manifest.json').is_file(), (
        f'no {base} reference packet for napari {version}: capture one with {CAPTURE}')
    recorded = recorded_version(directory)
    assert recorded == version, f'{directory.name} records napari {recorded}, not {version}'
    return directory


def lock_mismatches(lock: Path, skip: tuple = ('vispy',)) -> list[tuple[str, str | None, str]]:
    """The lock's requirements that the running environment does not satisfy, as (name, installed, specifier).

    The renderer is skipped, because a candidate replaces it; requirements whose markers do not apply are skipped.
    """
    from packaging.requirements import Requirement
    mismatches = []
    for line in Path(lock).read_text(encoding='utf-8').splitlines():
        if not line or line.startswith((' ', '#')):
            continue
        requirement = Requirement(line.split(' --hash=', 1)[0].rstrip('\\').strip())
        if requirement.name.lower() in skip or (requirement.marker and not requirement.marker.evaluate()):
            continue
        try:
            installed = metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            installed = None
        if installed is None or installed not in requirement.specifier:
            mismatches.append((requirement.name, installed, str(requirement.specifier)))
    return mismatches


def _napari_version_expression(node: ast.expr) -> bool:
    if isinstance(node, ast.Call):  # metadata.version("napari")
        return (isinstance(node.func, ast.Attribute) and node.func.attr == 'version' and len(node.args) == 1
                and not node.keywords and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'napari')
    return (isinstance(node, ast.Attribute) and node.attr == '__version__'  # napari.__version__
            and isinstance(node.value, ast.Name) and node.value.id == 'napari')


def is_napari_pin(statement: ast.stmt) -> bool:
    """An assert that the installed napari equals one literal version, with or without a message."""
    if not isinstance(statement, ast.Assert) or not isinstance(statement.test, ast.Compare):
        return False
    test = statement.test
    return (len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and _napari_version_expression(test.left)
            and isinstance(test.comparators[0], ast.Constant) and isinstance(test.comparators[0].value, str))


def unpinned_source(function) -> str:
    """The function's definition, normalized by ast.unparse, without its top-level napari pins."""
    definition = ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]
    definition.body = [statement for statement in definition.body if not is_napari_pin(statement)]
    return ast.unparse(definition)


def evidence_dir(name: str, version: str) -> Path:
    """Where a successor suite saves candidate frames; VISPY_NAPARI_EVIDENCE keeps runs out of the main tree."""
    return Path(os.environ.get('VISPY_NAPARI_EVIDENCE', ROOT / 'build/evidence')) / name / version
