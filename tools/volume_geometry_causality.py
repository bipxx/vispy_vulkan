# SPDX-License-Identifier: AGPL-3.0-only
"""Source obligations for the closed, pinned volume benchmark program.

This proves source obligations, not measured geometry by itself. A runtime
validator must also prove warm bytes, object/scene identity, exact measured
GL counters and complete removal of the observer from the sampled path.
Original cube mathematics is from VisPy 0.17; its BSD notice is in LICENSE-BSD.
"""
from __future__ import annotations
import ast
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
from . import volume_benchmark_adapter as original

ROOT = original.benchmark.ROOT
require = original.require
CRITICAL = ('visuals/volume.py', 'visuals/visual.py', 'scene/visuals.py',
            'gloo/buffer.py', 'gloo/glir.py', 'gloo/program.py', 'gloo/globject.py')
WRITERS = {'_vol_shape': {'__init__', 'set_data'}, '_need_vertex_update': {'__init__', 'set_data'},
           '_vertices': {'__init__'}, '_index_buffer': {'__init__'}, '_last_data': {'__init__', 'set_data'}}
CUBE = '''def _create_vertex_data(self):
    shape = self._vol_shape
    x0, x1 = -0.5, shape[2] - 0.5
    y0, y1 = -0.5, shape[1] - 0.5
    z0, z1 = -0.5, shape[0] - 0.5
    pos = np.array([[x0,y0,z0],[x1,y0,z0],[x0,y1,z0],[x1,y1,z0],
                    [x0,y0,z1],[x1,y0,z1],[x0,y1,z1],[x1,y1,z1]], dtype=np.float32)
    indices = np.array([2,6,0,4,5,6,7,2,3,0,1,5,3,7], dtype=np.uint32)
    self._vertices.set_data(pos)
    self._index_buffer.set_data(indices)
'''
PREPARE = '''def _prepare_draw(self, view):
    if self._need_vertex_update:
        self._create_vertex_data()
    if self._need_interpolation_update:
        self._build_interpolation()
'''


def canonical(node):
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return None
    if isinstance(node, ast.AST):
        fields = []
        for name, value in ast.iter_fields(node):
            if name == 'type_params':
                require(not value, 'Generic functions are not admitted')
                continue
            fields.append((name, canonical(value)))
        return (type(node).__name__, fields)
    if isinstance(node, list): return [value for item in node if (value := canonical(item)) is not None]
    return node


def method(tree, class_name, method_name):
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    matches = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name]
    require(len(matches) == 1, 'Unique method required: ' + class_name + '.' + method_name)
    return matches[0]


def volume_obligations(text):
    tree = ast.parse(text)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'VolumeVisual')
    found = {name: set() for name in WRITERS}
    for fn in cls.body:
        if not isinstance(fn, ast.FunctionDef): continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store) and
                    isinstance(node.value, ast.Name) and node.value.id == 'self' and node.attr in WRITERS):
                found[node.attr].add(fn.name)
    require(found == WRITERS, 'Volume geometry attribute writers differ')
    flag_values=[node.value for node in ast.walk(cls) if isinstance(node,ast.Assign) and any(
        isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name) and target.value.id=='self' and
        target.attr=='_need_vertex_update' for target in node.targets)]
    require(flag_values and all(isinstance(value,ast.Constant) and value.value is True for value in flag_values),
            'Original cube update flag can be cleared')
    cube = method(tree, 'VolumeVisual', '_create_vertex_data')
    require(canonical(cube) == canonical(ast.parse(CUBE).body[0]), 'Cube is not the admitted pure shape computation')
    require(canonical(method(tree, 'VolumeVisual', '_prepare_draw')) == canonical(ast.parse(PREPARE).body[0]),
            'Volume draw no longer unconditionally prepares the needed cube')
    setter = method(tree, 'VolumeVisual', 'set_data')
    shape_assignments = [node for node in ast.walk(setter) if isinstance(node, ast.Assign) and
                         any(isinstance(target, ast.Name) and target.id == 'shape' for target in node.targets)]
    require(len(shape_assignments) == 1 and ast.unparse(shape_assignments[0].value) == 'vol.shape[:3]', 'Volume shape is not derived from input dimensions')
    return {name: sorted(values) for name, values in found.items()}


def predicted_geometry(shape):
    """Execute the fixed template only, never caller-provided source."""
    class Buffer:
        def set_data(self, data): self.data = data
    class Volume: pass
    volume = Volume(); volume._vol_shape = tuple(shape)
    volume._vertices, volume._index_buffer = Buffer(), Buffer()
    namespace = dict(np=np)
    exec(compile(CUBE, '<pinned-volume-cube-template>', 'exec'), namespace)
    namespace['_create_vertex_data'](volume)
    # The pinned VertexBuffer preparation views a contiguous Nx3 float32
    # array as one structured f0 field; byte content is unchanged.
    vertices = volume._vertices.data.view(dtype=[('f0', np.float32, 3)])
    return dict(VertexBuffer=original.geometry.array_record(vertices),
                IndexBuffer=original.geometry.array_record(volume._index_buffer.data))


def source_obligations(package, expected_package, name):
    require(name in original.suite.CASES, 'Registered volume workload required')
    workload = original.benchmark.CATALOG[name]
    require(workload.family == 'volume' and workload.update in ('resident', 'full') and
            workload.shape in ((256,256,256), (512,512,512)), 'Closed scalar volume program required')
    package = Path(package).resolve(strict=True)
    bodies, digests = {}, {}
    for relative in CRITICAL:
        path = (package / relative).resolve(strict=True)
        require(path.is_relative_to(package), 'Source outside installed package')
        body = path.read_bytes(); digest = hashlib.sha256(body).hexdigest()
        require(digest == expected_package['vispy/' + relative], 'Installed source differs: ' + relative)
        bodies[relative] = body.decode('utf-8'); digests['vispy/' + relative] = digest
    writers = volume_obligations(bodies['visuals/volume.py'])
    draw=method(ast.parse(bodies['visuals/visual.py']),'Visual','draw')
    require(ast.unparse(draw.body[0].test)=='not self.visible' and
            ast.unparse(draw.body[1].test)=='self._prepare_draw(view=self) is False',
            'Pinned visual visibility/prepare dispatch differs')
    draw_calls=[node for node in ast.walk(draw) if isinstance(node,ast.Call) and ast.unparse(node.func)=='self._program.draw']
    require(len(draw_calls)==1 and [ast.unparse(arg) for arg in draw_calls[0].args]==['self._vshare.draw_mode','self._vshare.index_buffer'],
            'Pinned visual indexed draw path differs')
    expected = original.expected_geometry(name)
    predictions = predicted_geometry(workload.shape)
    require(all(predictions[kind] == expected[kind]['payload'] for kind in predictions), 'Predicted cube differs from pinned original bytes')
    # Loading the original reference also verifies the complete frozen factory
    # source set. The same factory allocates the full update buffer empty_like
    # the original data; multiply(out=buffer) never changes its dimensions.
    factory = (ROOT / 'tools/benchmark_frames.py').read_text(encoding='utf-8')
    tree = ast.parse(factory)
    build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'build_scene')
    calls = [ast.unparse(node) for node in ast.walk(build) if isinstance(node, ast.Call)]
    require('np.empty_like(data)' in calls and 'visual.set_data(update_buffer)' in calls,
            'Shape-preserving full update route differs')
    stores=[node for node in ast.walk(build) if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Store) and node.id=='update_buffer']
    require(len(stores)==1,'Full update buffer is reassigned')
    require(not any(isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Store) and
        isinstance(node.value,ast.Name) and node.value.id=='update_buffer' for node in ast.walk(build)),
        'Full update buffer shape/dtype attributes are mutated')
    require(not any(call.startswith('update_buffer.resize(') for call in calls),'Full update buffer is resized')
    return dict(schema=1, status='source_obligations_passed', workload=name,
        workload_sha256=original.benchmark.value_sha256(asdict(workload)), installed_source_sha256=digests,
        factory_sha256=original.benchmark.sha256(ROOT/'tools/benchmark_frames.py'),
        attribute_writers=writers, predicted_payloads=predictions,
        update_shape_invariant='resident changes camera only' if workload.update=='resident' else 'empty_like(data), multiply out=update_buffer, set_data(update_buffer)',
        buffer_transfer_contract='Pinned Buffer/DataBuffer -> order-preserving GLIR SIZE/DATA -> GlirBuffer SubData. Runtime must reject errors, fallback/storage and extra uploads.',
        scope='Closed pinned benchmark program only; not arbitrary host scenes or external callbacks',
        measured_geometry_proven=False,
        required_runtime_obligations=['single visible volume scene', 'stable shape/data/buffer object identities',
            'exact cold and warm payloads', 'observer detached at both measured boundaries',
            'no observer calls during measurement', 'one raw GL draw and two uploads/152 bytes per measured frame',
            'no buffer creation/deletion/storage/errors or other forbidden measured work'])
