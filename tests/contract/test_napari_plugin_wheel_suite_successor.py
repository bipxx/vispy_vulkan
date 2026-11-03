# SPDX-License-Identifier: AGPL-3.0-only
"""D31: the plugin-wheel successor suite runs the retained suite's own code with the napari 0.10.0 inputs."""
import ast
import builtins
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import symtable
import sys
import textwrap
from types import ModuleType

import pytest

from tools import napari_plugin_wheel_suite as old
from tools import napari_plugin_wheel_suite_successor as new
from tools.napari_host_packets import LOCK_SNAPSHOT, packet_dir, recorded_version

ROOT = Path(__file__).resolve().parents[2]
REBOUND = ('sources', 'legacy_reference', 'registration_control', 'load_reference', 'worker', 'run', 'main')
SHARED = ('compare', 'read_extras', 'interpreter_policy')
# What the rebound code reads from the successor instead of the retained module.
RENEWED = {'render', 'LEGACY', 'LEGACY_SHA256', 'SOURCES', 'plugin_info', 'runtime_requirements', *REBOUND,
           '__file__', '__doc__'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


@pytest.mark.parametrize('name', REBOUND)
def test_each_suite_step_is_the_retained_code(name):
    retained, successor = getattr(old, name), getattr(new, name)
    assert successor is not retained and successor.__code__ is retained.__code__
    assert successor.__globals__ is vars(new) and successor.__module__ == new.__name__
    assert (successor.__defaults__, successor.__kwdefaults__, successor.__closure__) == (
        retained.__defaults__, retained.__kwdefaults__, retained.__closure__)


@pytest.mark.parametrize('name', SHARED)
def test_steps_that_read_no_renewed_input_are_the_retained_functions(name):
    assert getattr(new, name) is getattr(old, name)
    assert not global_names(getattr(old, name)) & RENEWED


@pytest.mark.parametrize('name', REBOUND)
def test_the_retained_code_reads_retained_objects_except_the_named_inputs(name):
    for symbol in global_names(getattr(old, name)):
        if symbol in RENEWED:
            assert getattr(new, symbol) is not getattr(old, symbol), (name, symbol)
        elif symbol in vars(old):
            assert getattr(new, symbol) is getattr(old, symbol), (name, symbol)
        else:
            assert symbol not in vars(new) and hasattr(builtins, symbol), (name, symbol)


class SuccessorInputs(ast.NodeTransformer):
    """The retained verify_saved reads its napari 0.9.2 host versions as a literal and the plugin wheel digest from
    its capture tool; the successor reads HOST_VERSIONS and PLUGIN_WHEEL_SHA256."""
    RETAINED = "{'napari': '0.9.2', 'napari-threedee': '0.0.29', 'numpy': '2.4.6', 'PyQt6': '6.11.0'}"

    def __init__(self):
        self.replaced = []

    def visit_Dict(self, node):
        if ast.unparse(node) == self.RETAINED:
            self.replaced.append('versions')
            return ast.Name('HOST_VERSIONS', ast.Load())
        return self.generic_visit(node)

    def visit_Attribute(self, node):
        if ast.unparse(node) == 'capture.WHEEL_SHA':
            self.replaced.append('wheel')
            return ast.Name('PLUGIN_WHEEL_SHA256', ast.Load())
        return self.generic_visit(node)


def test_verify_saved_is_the_retained_check_reading_the_successor_versions_and_wheel():
    transformer = SuccessorInputs()
    expected = transformer.visit(ast.parse(textwrap.dedent(inspect.getsource(old.verify_saved))))
    assert sorted(transformer.replaced) == ['versions', 'versions', 'wheel', 'wheel']
    actual = ast.parse(textwrap.dedent(inspect.getsource(new.verify_saved)))
    assert ast.unparse(actual) == ast.unparse(expected)
    assert new.verify_saved.__kwdefaults__ == old.verify_saved.__kwdefaults__


@pytest.mark.parametrize('name', ('verify_saved', 'plugin_info', 'runtime_requirements'))
def test_every_global_the_successor_functions_read_is_defined(name):
    function = getattr(new, name)
    assert function.__module__ == new.__name__ and function is not getattr(old, name)
    for symbol in global_names(function):
        assert symbol in vars(new) or hasattr(builtins, symbol), (name, symbol)


def test_host_versions_are_the_runtime_lock_pins_and_the_plugin_wheel():
    pins = dict(re.findall(r'(?m)^([a-z0-9._-]+)==(\S+) \\$', (ROOT / new.RUNTIME).read_text(encoding='utf-8')))
    assert new.HOST_VERSIONS == {'napari': pins['napari'], 'napari-threedee': '0.0.29', 'numpy': pins['numpy'],
                                 'PyQt6': pins['pyqt6']}
    assert new.HOST_VERSIONS['napari'] == '0.10.0'
    assert new.PLUGIN_WHEEL.name.startswith('napari_threedee-0.0.29-')


def test_legacy_packet_is_the_overlay_packet_for_the_locked_napari_and_keeps_the_runtime():
    directory = ROOT / new.LEGACY
    assert directory == packet_dir('napari-threedee-overlay-opengl', new.HOST_VERSIONS['napari'])
    assert recorded_version(directory) == new.HOST_VERSIONS['napari']
    assert digest(directory / 'manifest.json') == new.LEGACY_SHA256
    assert new.RUNTIME == f'{new.LEGACY}/{LOCK_SNAPSHOT}'
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['provenance']['plugin']['host_lock']['sha256'] == digest(ROOT / new.RUNTIME)


def test_runtime_is_the_packet_lock_with_vispy_replaced_by_the_plugin_wheel():
    lock = (ROOT / new.RUNTIME).read_text(encoding='utf-8')
    blocks = re.findall(old.base.VISPY_BLOCK, lock)
    assert len(blocks) == 1
    wheel = f'napari-threedee @ {new.PLUGIN_WHEEL.as_uri()} --hash=sha256:{new.PLUGIN_WHEEL_SHA256}'
    runtime = new.runtime_requirements()
    assert runtime == lock.replace(blocks[0], '', 1) + f'\n{wheel}\n'
    assert 'vispy==' not in runtime
    # asciitree 1.0.0 stays as locked: its wheel is listed, so --only-binary installs it (0.3.3 had only an sdist).
    asciitree = re.search(r'(?m)^asciitree==.*\n(?:    --hash=.*\n)+', runtime).group()
    assert asciitree.startswith('asciitree==1.0.0 ')
    assert '4ec3e9dbf093e4b52577325071c11c669ad6fb180a78f168962d35b535d3f430' in asciitree


def test_plugin_wheel_digest_is_the_input_bundle_and_successor_capture_digest(monkeypatch):
    inputs = json.loads((old.INPUTS / 'manifest.json').read_bytes())
    assert new.PLUGIN_WHEEL is old.PLUGIN_WHEEL
    assert digest(new.PLUGIN_WHEEL) == inputs['files'][new.PLUGIN_WHEEL.name] == new.PLUGIN_WHEEL_SHA256
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))  # the capture runs as a script
    spec = importlib.util.spec_from_file_location('plugin_wheel_successor_capture',
                                                  ROOT / 'tools/oracle_napari_plugin_successor_capture.py')
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    assert capture.WHEEL_SHA == new.PLUGIN_WHEEL_SHA256 and capture.WHEEL == new.PLUGIN_WHEEL


def test_sources_name_the_successor_inputs_and_not_the_retained_runtime():
    for name in ('tools/napari_plugin_wheel_suite_successor.py', 'tools/napari_plugin_wheel_suite.py',
                 'tools/fixture_napari_threedee_overlay_successor.py', 'tools/fixture_napari_threedee_overlay.py',
                 'tools/napari_world_position.py', 'tools/oracle_napari_plugin_successor_capture.py',
                 'tools/napari_host_packets.py', 'tools/smooth_line_parity.py', new.RUNTIME,
                 new.PLUGIN_WHEEL.relative_to(ROOT).as_posix(), *old.base.SOURCES):
        assert name in new.SOURCES, name
    assert old.RUNTIME not in new.SOURCES
    assert not any('asciitree' in name or name.startswith('build/') for name in new.SOURCES)
    assert set(new.sources()) == set(new.SOURCES)


def fake_capture(record):
    module = ModuleType('oracle_napari_plugin_successor_capture')
    module.plugin_provenance = lambda suite, host_lock: dict(record, requested=(suite, host_lock))
    return module


@pytest.mark.parametrize('broken', (None, 'version', 'lock', 'wheel', 'origin'))
def test_plugin_info_checks_the_successor_capture_the_versions_and_the_lock(broken, monkeypatch):
    prefix = Path(sys.prefix).resolve()
    record = dict(plugin_origin=str(prefix / 'Lib/site-packages/napari_threedee'),
                  napari_origin=str((ROOT if broken == 'origin' else prefix) / 'napari/__init__.py'),
                  plugin_wheel_sha256='0' * 64 if broken == 'wheel' else new.PLUGIN_WHEEL_SHA256)
    monkeypatch.setitem(sys.modules, 'oracle_napari_plugin_successor_capture', fake_capture(record))
    versions = dict(new.HOST_VERSIONS, **({'numpy': '2.5.3'} if broken == 'version' else {}))
    monkeypatch.setattr(new.metadata, 'version', versions.__getitem__)
    locks = []
    monkeypatch.setattr(new, 'lock_mismatches', lambda lock: locks.append(lock) or (
        [('pandas', '3.0.6', '==3.1.0')] if broken == 'lock' else []))
    if broken:
        with pytest.raises(AssertionError):
            new.plugin_info()
        return
    plugin, observed = new.plugin_info()
    assert plugin['requested'] == ('overlay', None) and observed == new.HOST_VERSIONS
    assert locks == [ROOT / new.RUNTIME]


def candidate_parameters(expected):
    params = dict(expected)
    assert 'QOpenGLWidget' in params['native_mro']
    params['native_mro'] = ['QWidget']
    return params


@pytest.mark.parametrize('name', new.CASES)
def test_packet_cases_and_auxiliary_frames_are_accepted_with_the_candidate_widget(name):
    image, params, extras = new.legacy_reference(name)
    new.compare(name, image.copy(), image, candidate_parameters(params), params,
                {key: value.copy() for key, value in extras.items()}, extras)


@pytest.mark.parametrize('name', new.CASES)
def test_successor_packet_rejects_one_changed_rgba_byte(name):
    image, params, extras = new.legacy_reference(name)
    candidate = image.copy()
    candidate[0, 0, 3] ^= 1
    with pytest.raises(AssertionError, match='Plugin frame differs beyond smooth-line edges'):
        new.compare(name, candidate, image, candidate_parameters(params), params, extras, extras)


@pytest.mark.parametrize('name', ('selection', 'translation', 'miss'))
def test_successor_packet_before_frames_are_mandatory(name):
    image, params, extras = new.legacy_reference(name)
    changed = {key: value.copy() for key, value in extras.items()}
    changed['before'][0, 0, 3] ^= 1
    with pytest.raises(AssertionError, match='Auxiliary frame'):
        new.compare(name, image, image, candidate_parameters(params), params, changed, extras)


def test_successor_packet_event_state_stays_exact():
    image, params, extras = new.legacy_reference('selection')
    changed = candidate_parameters(params)
    changed['screenshot_api'] = 'different export'
    with pytest.raises(AssertionError, match='Qt events or callback state'):
        new.compare('selection', image, image, changed, params, extras, extras)


__all__ = [name for name in dir() if name.startswith('test_')]
