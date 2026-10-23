# SPDX-License-Identifier: AGPL-3.0-only
"""Actual benchmark inputs and fixed quality controls, without a renderer."""
import ast
from dataclasses import asdict
import hashlib
import inspect
import json
import math
from types import SimpleNamespace
import sys

import numpy as np
import pytest
from tools import fixture_large_volume as fixture


def portable_ast(node):
    """Ignore only empty generic metadata added in newer Python AST schemas."""
    if isinstance(node,ast.AST):
        assert not getattr(node,'type_params',[])
        return [type(node).__name__,{key:portable_ast(getattr(node,key,None))
                for key in node._fields if key!='type_params'}]
    if isinstance(node,list):return [portable_ast(item) for item in node]
    if node is Ellipsis:return {'python_constant':'Ellipsis'}
    return node


def test_all_24_volume_benchmark_workloads_are_used_without_parameter_changes():
    expected = {f'volume-{side}-{viewport}-{method}-{update}'
                for side in (256, 512) for viewport in (1024, 2048)
                for method in ('mip', 'translucent', 'iso') for update in ('resident', 'full')}
    assert set(fixture.CASES) == expected and len(fixture.CASES) == 24
    for name in fixture.CASES:
        spec = fixture.case_contract(name)
        assert spec['workload'] == asdict(fixture.benchmark.CATALOG[name])
        assert spec['workload_sha256'] == fixture.benchmark.value_sha256(spec['workload'])
        assert spec['workload']['relative_step_size'] == .8
        assert spec['workload']['interpolation'] == 'linear'
        assert spec['workload']['threshold'] == .5 and spec['workload']['gamma'] == 1
        assert spec['workload']['colormap'] == ('density-alpha' if spec['workload']['method'] == 'translucent' else 'grays')
        assert spec['probe_frames'] == [None, None, 7, 73]
        assert spec['comparison']['max_abs_channel_error'] == 2
        assert spec['comparison']['excluded_pixels'] == 0 and spec['comparison']['edge_mask'] is None
        assert not spec['performance_qualified']


def test_factory_data_camera_and_updates_preserve_the_prior_ast_with_declared_setup_fixes():
    current = ast.parse(inspect.getsource(fixture.benchmark.build_scene)).body[0]
    assert [a.arg for a in current.args.kwonlyargs] == ['on_canvas']
    current.args.kwonlyargs = []; current.args.kw_defaults = []
    hooks = [node for node in current.body if isinstance(node, ast.If) and
             isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == 'on_canvas']
    assert len(hooks) == 1
    current.body.remove(hooks[0])
    preparation = [node for node in current.body if isinstance(node,ast.Expr) and
                   isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and
                   node.value.func.id == 'prepare_benchmark_canvas']
    assert len(preparation) == 1;current.body.remove(preparation[0])
    for call in ast.walk(current):
        if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute):continue
        if call.func.attr == 'Volume':
            cmap = [k for k in call.keywords if k.arg == 'cmap']
            assert len(cmap) == 1;call.keywords.remove(cmap[0])
        elif call.func.attr == 'Image':
            cmap = next(k for k in call.keywords if k.arg == 'cmap')
            assert isinstance(cmap.value,ast.Attribute) and cmap.value.attr == 'colormap'
            cmap.value = ast.Constant(value='grays')
    # Only explicit surface preparation, declared colormap handling and the
    # capture hook differ. Dataset, camera and update closure stay pinned.
    assert hashlib.sha256(json.dumps(portable_ast(current),sort_keys=True,separators=(',',':')).encode()).hexdigest() == (
        '46292b578c6083d6d3b0b8b4f9b0c8039fc1f66641e9a1e8574afef1f2071d88')


@pytest.mark.parametrize('side', (256, 512))
def test_actual_factory_generates_full_float_data_and_reuses_full_update_buffer(monkeypatch, side):
    events = []; recorded = {}
    class Volume:
        def __init__(self, data, **kwargs):
            events.append('volume'); recorded.update(data=data, controls=kwargs)
        def set_data(self, data):
            recorded['update'] = data
    view = SimpleNamespace(scene=object())
    canvas = SimpleNamespace(app=SimpleNamespace(native=SimpleNamespace(
        setQuitOnLastWindowClosed=lambda value: events.append('quit-policy'))),
        central_widget=SimpleNamespace(add_view=lambda: view))
    fake = SimpleNamespace(SceneCanvas=lambda **kw: canvas,
                           visuals=SimpleNamespace(Volume=Volume),
                           TurntableCamera=lambda **kw: recorded.setdefault('camera', kw))
    # An explicit CPU double supplies only the public objects used by the real
    # factory. No VisPy/provider/device module is imported or executed here.
    monkeypatch.setitem(sys.modules, 'vispy', SimpleNamespace(scene=fake))
    monkeypatch.setattr(fixture.benchmark, 'prepare_benchmark_canvas', lambda *args: None)
    workload = fixture.benchmark.CATALOG[f'volume-{side}-1024-mip-full']
    actual_canvas, update, digest = fixture.benchmark.build_scene(
        workload, 'upstream', False, on_canvas=lambda c: events.append('capture-hook'))
    assert actual_canvas is canvas and events == ['quit-policy', 'capture-hook', 'volume']
    data = recorded['data']
    assert data.shape == (side,)*3 and data.dtype == np.float32
    assert data.nbytes == side**3*4
    assert hashlib.sha256(memoryview(data).cast('B')).hexdigest() == digest
    assert data[0, 0, 0] == 0 and data[side//2, side//2, side//2] == 1
    for z, y, x in ((side//3, side//2, side//2), (side//2, side//3, side//2), (side//2, side//2, side//3)):
        az, ay, ax = (v/(side-1)-.5 for v in (z,y,x))
        expected = max(0, 1-(ay/.36)**2-(ax/.28)**2-(az/.42)**2)
        assert abs(float(data[z,y,x])-expected) < 4e-7
    assert recorded['camera'] == dict(azimuth=30, elevation=20, distance=side*2.5,
                                       fov=45, center=(side/2,)*3)
    assert update(7) == data.nbytes
    first_buffer = recorded['update']
    assert first_buffer is not data
    factor = np.float32(1-.01*math.sin(7*2*math.pi/180))
    np.testing.assert_array_equal(first_buffer[side//2], data[side//2]*factor)
    assert update(73) == data.nbytes and recorded['update'] is first_buffer
    factor = np.float32(1-.01*math.sin(73*2*math.pi/180))
    np.testing.assert_array_equal(first_buffer[side//2], data[side//2]*factor)


def test_quality_uses_existing_full_frame_two_byte_rule_including_alpha():
    reference = np.zeros((8, 8, 4), np.uint8)
    reference[..., 3] = 255
    changed = reference.copy(); changed[5, 6, 0] = 2; changed[1, 2, 3] -= 2
    assert fixture.compare_frames(reference, changed)['status'] == 'passed'
    changed[1, 2, 3] -= 1
    assert fixture.compare_frames(reference, changed)['status'] == 'failed'
    assert fixture.compare_frames(reference, changed[:4])['status'] == 'failed'
    assert fixture.compare_frames(reference, changed.astype(np.float32))['status'] == 'failed'


def test_invalid_or_smaller_unregistered_workload_cannot_enter_protocol():
    with pytest.raises(ValueError):fixture.case_contract('volume-32-96-mip-resident')


def test_small_update_requires_pixel_change_with_predeclared_overlap():
    initial = np.zeros((8,8,4), np.uint8); original = initial.copy(); original[:4,:,0] = 1
    # Every stale pixel is within the inherited two-byte tolerance, but stale
    # output must not admit a full-data update or a resident camera rotation.
    assert fixture.compare_frames(original, initial)['status'] == 'passed'
    assert not fixture.change_discrimination(initial, original, initial, initial)['passed']
    candidate = initial.copy(); candidate[:2,:,0] = 1
    assert fixture.change_discrimination(initial, original, initial, candidate)['passed']
    candidate[1,7,0] = 0
    assert not fixture.change_discrimination(initial, original, initial, candidate)['passed']
    check = fixture.change_discrimination(initial, initial, initial, initial)
    assert not check['passed'] and check['status'] == 'upload-witnessed, not pixel-discriminating'


def test_streamed_glir_hashes_equal_existing_records_without_large_bytes_copy():
    from tools.fixture_large_image import record_commands as prior
    for data in (np.arange(128,dtype=np.float32).reshape(8,16),
                 np.arange(256,dtype=np.float32).reshape(16,16)[::2,::2]):
        actual, expected, shaders, prior_shaders = [], [], {}, {}
        rows = [('DATA',1,0,data),('DATA',2,0,'void main() {}')]
        fixture.record_commands(rows,actual,shaders);prior(rows,expected,prior_shaders)
        assert actual == expected and shaders == prior_shaders


def test_density_alpha_uses_public_linear_colormap_with_zero_density_transparent(monkeypatch):
    calls=[]
    color=SimpleNamespace(Colormap=lambda colors,**kwargs: calls.append((colors,kwargs)))
    monkeypatch.setitem(sys.modules,'vispy',SimpleNamespace(color=color))
    monkeypatch.setitem(sys.modules,'vispy.color',color)
    workload=fixture.benchmark.CATALOG['volume-256-1024-translucent-resident']
    fixture.benchmark.volume_colormap(workload)
    assert calls==[([(0,0,0,0),(1,1,1,1)],dict(controls=(0,1),interpolation='linear'))]
    assert fixture.benchmark.volume_colormap(fixture.benchmark.CATALOG['volume-256-1024-mip-resident'])=='grays'


@pytest.mark.parametrize('clamp_again',(False,True))
def test_public_resize_restores_required_physical_extent_or_fails_before_data(clamp_again):
    class Canvas:
        def __init__(self):
            self.logical=(2048,1901);self.physical_size=(2048,1901);self.warms=0
            self._backend=SimpleNamespace(_vispy_warmup=self.warmup)
        def warmup(self):self.warms+=1
        @property
        def size(self):return self.logical
        @size.setter
        def size(self,value):
            self.logical=value
            if not clamp_again:self.physical_size=value
    canvas=Canvas()
    if clamp_again:
        with pytest.raises(fixture.benchmark.InstrumentationUnavailable):
            fixture.benchmark.prepare_benchmark_canvas(canvas,(2048,2048))
    else:
        result=fixture.benchmark.prepare_benchmark_canvas(canvas,(2048,2048))
        assert result['initial_physical']==[2048,1901] and result['final_physical']==[2048,2048]
    assert canvas.warms==2
