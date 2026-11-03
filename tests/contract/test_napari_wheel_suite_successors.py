# SPDX-License-Identifier: AGPL-3.0-only
"""D31: the volume and image installed-wheel successors are the retained suites' code, read with the 0.10.0 inputs."""
import ast
import builtins
import hashlib
import inspect
import json
from pathlib import Path
import symtable
import textwrap

import pytest

from tools import image_wheel_probe as old_image_probe
from tools import image_wheel_probe_successor as new_image_probe
from tools import image_wheel_reference as old_image
from tools import image_wheel_reference_successor as new_image
from tools import image_wheel_runner as old_image_runner
from tools import image_wheel_runner_successor as new_image_runner
from tools import volume_wheel_probe as old_volume_probe
from tools import volume_wheel_probe_successor as new_volume_probe
from tools import volume_wheel_reference as old_volume
from tools import volume_wheel_reference_successor as new_volume
from tools import volume_wheel_runner as old_volume_runner
from tools import volume_wheel_runner_successor as new_volume_runner
from tools.napari_host_packets import LOCK_SNAPSHOT, packet_dir, recorded_version

ROOT = Path(__file__).resolve().parents[2]
# (retained module, successor module, the steps rebound to the successor's globals, the names they read renewed)
REBOUND = {
    'volume_reference': (old_volume, new_volume, ('assert_landmarks', 'compare_case', 'render'),
                         {'categorical', 'packet_for', 'assert_landmarks'}),
    'image_reference': (old_image, new_image, ('load_case', 'compare_case'), {'load_manifest', 'case_contract'}),
    'volume_probe': (old_volume_probe, new_volume_probe, ('main',), {'capture', '__doc__'}),
    'image_probe': (old_image_probe, new_image_probe, ('main',), {'capture', '__doc__'}),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(function):
    return ast.parse(textwrap.dedent(inspect.getsource(function)))


def global_names(function):
    """The global names the function's code reads, nested scopes included, builtins too."""
    def collect(table):
        names = {symbol.get_name() for symbol in table.get_symbols() if symbol.is_global()}
        for child in table.get_children():
            names |= collect(child)
        return names
    module = symtable.symtable(textwrap.dedent(inspect.getsource(function)), function.__name__, 'exec')
    table = next(child for child in module.get_children()
                 if isinstance(child, symtable.Function) and child.get_name() == function.__name__)
    return collect(table)


@pytest.mark.parametrize('suite', REBOUND)
def test_each_rebound_step_is_the_retained_code_reading_the_successor(suite):
    old, new, steps, renewed = REBOUND[suite]
    for name in steps:
        retained, successor = getattr(old, name), getattr(new, name)
        assert successor is not retained and successor.__code__ is retained.__code__, (suite, name)
        assert successor.__globals__ is vars(new) and successor.__module__ == new.__name__, (suite, name)
        # A default naming the retained packet directory is bound to the successor's; every other default is kept.
        defaults = tuple(new.REFERENCE if value is old.REFERENCE else value for value in retained.__defaults__ or ())
        assert (successor.__defaults__ or (), successor.__kwdefaults__) == (defaults, retained.__kwdefaults__)
        for symbol in global_names(retained):
            if symbol in renewed or symbol in steps:
                assert getattr(new, symbol) is not getattr(old, symbol), (suite, name, symbol)
            elif symbol in vars(old):
                assert getattr(new, symbol) is getattr(old, symbol), (suite, name, symbol)
            else:
                assert symbol not in vars(new) and hasattr(builtins, symbol), (suite, name, symbol)


class Substitute(ast.NodeTransformer):
    """Replace the named string constants (each with source text) and the named statements, counting each use."""

    def __init__(self, constants=None, statements=None):
        self.constants, self.statements, self.used = constants or {}, statements or {}, []

    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in self.constants:
            self.used.append(node.value)
            return ast.parse(self.constants[node.value], mode='eval').body
        return node

    def generic_visit(self, node):
        if isinstance(node, ast.stmt) and ast.unparse(node) in self.statements:
            self.used.append(ast.unparse(node))
            return ast.parse(self.statements[ast.unparse(node)]).body[0]
        return super().generic_visit(node)


# (retained function, successor function, a fresh substitution for each run, its expected uses). A shared
# Substitute would count twice when pytest collects this module and the curated entry in one process.
COPIED = {
    'volume load_case': (old_volume.load_case, new_volume.load_case,
                         lambda: Substitute({'volume_fixture_sha256': "'fixture_source_sha256'"}), 2),
    'image load_manifest': (old_image.load_manifest, new_image.load_manifest,
                            lambda: Substitute(statements={
                                "assert sha(Path(producer_root) / lock['file'].replace('\\\\', '/')) == lock['sha256']":
                                    "assert sha(directory / lock['snapshot']) == lock['sha256']"}), 1),
    'volume capture': (old_volume_probe.capture, new_volume_probe.capture, lambda: Substitute({'0.9.2': 'NAPARI'}), 1),
    'image capture': (old_image_probe.capture, new_image_probe.capture, lambda: Substitute({'0.9.2': 'NAPARI'}), 1),
    'volume run_case': (old_volume_runner.run_case, new_volume_runner.run_case,
                        lambda: Substitute({'tools/volume_wheel_probe.py': "'tools/volume_wheel_probe_successor.py'"}), 1),
    'image run_case': (old_image_runner.run_case, new_image_runner.run_case,
                       lambda: Substitute({'tools/image_wheel_probe.py': "'tools/image_wheel_probe_successor.py'",
                                   'tests/reference/image-extensions-opengl/api-correct-attempt-2':
                                       "'tests/reference/image-extensions-opengl-napari-0.10.0'"}), 2),
}


@pytest.mark.parametrize('name', COPIED)
def test_each_copied_step_is_the_retained_one_with_only_its_named_substitutions(name):
    retained, successor, make, uses = COPIED[name]
    substitution = make()
    expected = substitution.visit(tree(retained))
    assert len(substitution.used) == uses, (name, substitution.used)
    assert ast.unparse(tree(successor)) == ast.unparse(expected), name
    assert successor.__module__ != retained.__module__
    for symbol in global_names(successor):
        assert symbol in vars(inspect.getmodule(successor)) or hasattr(builtins, symbol), (name, symbol)


def test_the_successors_read_the_0_10_0_packets_by_their_manifest_digests():
    volume = ROOT / 'tests/reference' / new_volume.CATEGORICAL
    assert volume == packet_dir('napari-volume-opengl', new_volume.NAPARI)
    assert recorded_version(volume) == new_volume.NAPARI == new_image.NAPARI == '0.10.0'
    assert new_volume.PACKETS == {'volume-opengl': old_volume.PACKETS['volume-opengl'],
                                  new_volume.CATEGORICAL: digest(volume / 'manifest.json')}
    image = packet_dir('image-extensions-opengl', new_image.NAPARI)
    assert new_image.REFERENCE == image and new_image.MANIFEST_SHA256 == digest(image / 'manifest.json')
    manifest = json.loads((image / 'manifest.json').read_bytes())
    authoring = json.loads((image / 'authoring.json').read_bytes())
    assert authoring['napari_version'] == new_image.NAPARI
    assert authoring['installed_upstream_lock']['snapshot'] == LOCK_SNAPSHOT
    assert manifest['authoring_sha256'] == digest(image / 'authoring.json')
    assert new_volume_probe.NAPARI == new_image_probe.NAPARI == new_volume.NAPARI


def test_the_successor_fixtures_supply_the_napari_cases():
    from tools import fixture_image_extensions_successor, fixture_napari_volume_successor
    assert new_volume.categorical is fixture_napari_volume_successor
    assert new_volume.CASES == old_volume.CASES and new_volume.scalar is old_volume.scalar
    assert new_image.case_contract is fixture_image_extensions_successor.case_contract
    assert new_image_probe.render is fixture_image_extensions_successor.render
    assert new_image.CASES is old_image.CASES and new_image.COMPARISON is old_image.COMPARISON


def test_the_probes_and_runners_read_the_successor_references():
    # A probe reading a retained reference would compare 0.10.0 frames against a 0.9.2 packet and still record the
    # successor's digests, so every name a successor probe or runner takes from its reference is pinned here.
    from tools import fixture_image_extensions_successor as image_fixture
    for name in ('CASES', 'DIRECT_CASES', 'NAPARI', 'PACKETS', 'LICENSES', 'render', 'load_case', 'compare_case', 'sha'):
        assert getattr(new_volume_probe, name) is getattr(new_volume, name), name
    for name in ('NAPARI', 'MANIFEST_SHA256', 'LICENSES', 'load_case', 'load_manifest', 'compare_case', 'sha'):
        assert getattr(new_image_probe, name) is getattr(new_image, name), name
    for name in ('CASES', 'VISPY_CASES', 'render'):
        assert getattr(new_image_probe, name) is getattr(image_fixture, name), name
    assert new_volume_runner.CASES is new_volume.CASES and new_image_runner.CASES is image_fixture.CASES


def test_the_volume_packet_map_routes_only_the_napari_cases_to_the_new_packet():
    for name in new_volume.CASES:
        expected = 'volume-opengl' if name in new_volume.DIRECT_CASES else new_volume.CATEGORICAL
        assert new_volume.packet_for(name) == expected, name
    with pytest.raises(ValueError, match='Unknown required volume case'):
        new_volume.packet_for('no_such_case')
    with pytest.raises(ValueError, match='Unknown original volume packet'):
        new_volume.load_manifest('napari-volume-opengl')


@pytest.mark.parametrize('name', old_volume.CASES)
def test_every_volume_case_loads_and_compares_on_its_successor_packet(name):
    image, params = new_volume.load_case(name)
    candidate = dict(params)
    if name not in new_volume.DIRECT_CASES:  # the candidate's canvas is a plain QWidget, not the original QOpenGLWidget
        assert 'QOpenGLWidget' in candidate['native_mro']
        candidate['native_mro'] = ['QWidget']
    new_volume.compare_case(name, image.copy(), image, dict(candidate), params)
    if name not in new_volume.DIRECT_CASES:
        changed = image.copy()
        changed[0, 0, 3] ^= 1
        with pytest.raises(AssertionError, match='Exact categorical RGBA differs'):
            new_volume.compare_case(name, changed, image, dict(candidate), params)


@pytest.mark.parametrize('name', old_image.CASES)
def test_every_image_case_loads_and_compares_on_the_0_10_0_packet(name):
    image, params = new_image.load_case(name)
    new_image.compare_case(name, image.copy(), image, dict(params), params)
    changed = image.copy()
    changed[0, 0, 3] ^= 1
    with pytest.raises(AssertionError, match='Full-frame RGBA differs'):
        new_image.compare_case(name, changed, image, dict(params), params)


@pytest.mark.parametrize('probe, retained, names', [
    (new_volume_probe, old_volume_probe, ('tools/volume_wheel_reference_successor.py', 'tools/volume_wheel_probe_successor.py',
                                          'tools/fixture_napari_volume_successor.py', 'tools/napari_host_packets.py')),
    (new_image_probe, old_image_probe, ('tools/image_wheel_reference_successor.py', 'tools/image_wheel_probe_successor.py',
                                        'tools/fixture_image_extensions_successor.py', 'tools/napari_host_packets.py'))])
def test_the_probe_sources_add_the_successor_files_to_the_retained_ones(probe, retained, names):
    assert set(retained.SOURCES) < set(probe.SOURCES) and set(names) <= set(probe.SOURCES)
    assert all((ROOT / name).is_file() for name in probe.SOURCES)


__all__ = [name for name in dir() if name.startswith('test_')]
