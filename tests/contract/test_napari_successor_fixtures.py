# SPDX-License-Identifier: AGPL-3.0-only
"""D30: each successor fixture is its retained module without the napari pin, and shares everything else with it."""
import ast
import builtins
import importlib
import inspect
from pathlib import Path
import subprocess
import symtable
import sys
import textwrap

import pytest

from tools.napari_host_packets import is_napari_pin, unpinned_source

ROOT = Path(__file__).resolve().parents[2]
PAIRS = {'fixture_napari': 'fixture_napari_successor',
         'fixture_napari_layer_controls': 'fixture_napari_layer_controls_successor',
         'fixture_napari_layer_families': 'fixture_napari_layer_families_successor',
         'fixture_napari_vector_layers': 'fixture_napari_vector_layers_successor',
         'fixture_napari_volume': 'fixture_napari_volume_successor'}
SHARED = ('CASES', 'CRITERIA', 'EXACT', 'SIZE', 'BACKGROUND', 'masks', 'specification', 'assert_landmarks')


def pair(retained):
    return importlib.import_module(f'tools.{retained}'), importlib.import_module(f'tools.{PAIRS[retained]}')


def definition(function):
    return ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]


def global_names(function):
    """The global names the function reads, nested scopes included, builtins excluded."""
    def collect(table):  # Symbol.is_global works in every scope; Python 3.14 adds annotation scopes
        names = {symbol.get_name() for symbol in table.get_symbols() if symbol.is_global()}
        for child in table.get_children():
            names |= collect(child)
        return names
    module = symtable.symtable(textwrap.dedent(inspect.getsource(function)), function.__name__, 'exec')
    table = next(child for child in module.get_children()
                 if isinstance(child, symtable.Function) and child.get_name() == function.__name__)
    return {name for name in collect(table) if not hasattr(builtins, name)}


@pytest.mark.parametrize('retained', PAIRS)
def test_successor_fixture_shares_the_retained_inputs_and_criteria(retained):
    old, new = pair(retained)
    shared = [name for name in SHARED if hasattr(old, name)]
    assert {'CASES', 'assert_landmarks'} <= set(shared)
    for name in shared:
        assert getattr(new, name) is getattr(old, name), (retained, name)


@pytest.mark.parametrize('retained', PAIRS)
def test_successor_render_is_the_retained_render_without_its_pin(retained):
    old, new = pair(retained)
    assert new.render is not old.render and new.render.__module__ == new.__name__
    assert sum(map(is_napari_pin, definition(old.render).body)) == 1
    assert not any(map(is_napari_pin, ast.walk(definition(new.render))))
    assert unpinned_source(new.render) == unpinned_source(old.render)
    # The same code reads the same objects: every global the successor's render uses is the retained module's own.
    for name in global_names(new.render):
        assert getattr(new, name) is getattr(old, name), (retained, name)


PLUGIN_PAIRS = {'fixture_napari_threedee_overlay': 'fixture_napari_threedee_overlay_successor',
                'fixture_napari_threedee_initialized': 'fixture_napari_threedee_initialized_successor',
                'fixture_napari_render_plane_scheduled': 'fixture_napari_render_plane_scheduled_successor'}


@pytest.mark.parametrize('retained', [*PAIRS, 'fixture_image_extensions', *PLUGIN_PAIRS])
def test_successor_fixture_imports_nothing_beyond_its_retained_module(retained):
    successor = f'{retained}_successor'
    # The plugin successors also use napari's mouse-event world position (D31).
    added = {f'tools.{successor}'} | ({'tools.napari_world_position'} if retained in PLUGIN_PAIRS else set())
    code = f"""
import sys
import tools.{retained}
before = set(sys.modules)
import tools.{successor}
assert set(sys.modules) - before == {added!r}, sorted(set(sys.modules) - before)
"""
    child = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, text=True)
    assert child.returncode == 0, (child.stdout, child.stderr)


# The image-extension successor also renews case_contract: the retained contract names its pinned host
# ("public napari0.9.2"), which the successor's packets record per version instead.
IMAGE_RENEWED = {'render', '_render_host', 'case_contract'}


def image_pair():
    return (importlib.import_module('tools.fixture_image_extensions'),
            importlib.import_module('tools.fixture_image_extensions_successor'))


def test_image_successor_shares_the_retained_inputs():
    old, new = image_pair()
    for name in ('CASES', 'VISPY_CASES', 'COMPARISON', 'HIGH_A', 'HIGH_B', 'SIZE', 'DATA_SIZE', 'BACKGROUND',
                 'array_record', 'assert_landmarks', 'final_arrays', 'input_arrays', 'paint_mask'):
        assert getattr(new, name) is getattr(old, name), name
    for name in IMAGE_RENEWED:
        assert getattr(new, name) is not getattr(old, name) and getattr(new, name).__module__ == new.__name__, name


def test_image_successor_contract_differs_only_in_the_host_workflow_name():
    old, new = image_pair()
    for name in old.CASES:
        expected = old.case_contract(name)
        if name not in old.VISPY_CASES:
            assert expected['workflow'] == 'public napari0.9.2', name
            expected['workflow'] = 'public napari'
        assert new.case_contract(name) == expected, name


@pytest.mark.parametrize('function', ['render', '_render_host'])
def test_image_successor_renders_are_the_retained_ones_without_the_pin(function):
    old, new = image_pair()
    assert sum(map(is_napari_pin, definition(getattr(old, function)).body)) == (function == '_render_host')
    assert not any(map(is_napari_pin, ast.walk(definition(getattr(new, function)))))
    assert unpinned_source(getattr(new, function)) == unpinned_source(getattr(old, function))
    for name in global_names(getattr(new, function)) - IMAGE_RENEWED:
        assert getattr(new, name) is getattr(old, name), (function, name)


class UseWorldPosition(ast.NodeTransformer):
    """canvas._map_canvas2world(p, canvas.view) -> world_position(viewer, canvas, p): napari 0.10 removed the private
    canvas method and computes mouse-event positions with ViewerModel.canvas_to_world (D31)."""

    def visit_Call(self, node):
        self.generic_visit(node)
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr == '_map_canvas2world'
                and isinstance(func.value, ast.Name) and func.value.id == 'canvas' and len(node.args) == 2
                and ast.unparse(node.args[1]) == 'canvas.view' and not node.keywords):
            return ast.Call(func=ast.Name('world_position', ast.Load()),
                            args=[ast.Name('viewer', ast.Load()), ast.Name('canvas', ast.Load()), node.args[0]],
                            keywords=[])
        return node


def is_call(statement, name):
    return (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
            and ast.unparse(statement.value.func) == f'QtTest.QTest.{name}')


class SettleMouseMoves(ast.NodeTransformer):
    """A mouseMove not already followed by QtTest.QTest.qWait(10) gets one: napari's leading-edge 5 ms throttle can
    defer the final move past a single processEvents() (the retained overlay fixtures' drag race), and the scheduled
    fixture already waits so (D19). The wait delivers napari's own timer; no callback is replaced."""

    def generic_visit(self, node):
        super().generic_visit(node)
        for field in ('body', 'orelse', 'finalbody'):
            statements = getattr(node, field, None)
            if isinstance(statements, list) and statements and isinstance(statements[0], ast.stmt):
                settled = []
                for index, statement in enumerate(statements):
                    settled.append(statement)
                    following = statements[index + 1] if index + 1 < len(statements) else None
                    if is_call(statement, 'mouseMove') and not (following is not None and is_call(following, 'qWait')):
                        settled.append(ast.parse('QtTest.QTest.qWait(10)').body[0])
                setattr(node, field, settled)
        return node


def plugin_pair(retained):
    return importlib.import_module(f'tools.{retained}'), importlib.import_module(f'tools.{PLUGIN_PAIRS[retained]}')


@pytest.mark.parametrize('retained', PLUGIN_PAIRS)
def test_plugin_successor_shares_the_retained_inputs(retained):
    old, new = plugin_pair(retained)
    for name in ('CASES', 'SIZE', 'AXES', 'specification', 'assert_landmarks', 'phantom', 'projected_axis_distance'):
        if hasattr(old, name):
            assert getattr(new, name) is getattr(old, name), (retained, name)


@pytest.mark.parametrize('retained', PLUGIN_PAIRS)
def test_plugin_successor_render_is_the_retained_render_with_its_three_changes(retained):
    from tools.napari_host_packets import napari_pin_count
    from tools.napari_world_position import world_position

    old, new = plugin_pair(retained)
    assert napari_pin_count(old.render) == 1 and napari_pin_count(new.render) == 0
    source = unpinned_source(new.render)
    assert "metadata.version('napari')" not in source and 'napari.__version__' not in source
    assert '_map_canvas2world' not in source and 'world_position(viewer, canvas, ' in source
    tree = ast.parse(unpinned_source(old.render))
    expected = ast.unparse(SettleMouseMoves().visit(UseWorldPosition().visit(tree)))
    assert source == expected, retained
    assert new.world_position is world_position
    for name in global_names(new.render) - {'world_position'}:
        assert getattr(new, name) is getattr(old, name), (retained, name)


__all__ = [name for name in dir() if name.startswith('test_')]
