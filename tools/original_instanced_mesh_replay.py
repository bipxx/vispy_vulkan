# SPDX-License-Identifier: AGPL-3.0-only
"""Replay frozen original test bodies with the actual Dawn application."""
import ast
import copy
import hashlib
import sys
from pathlib import Path


def original_instanced_mesh_checks(root, scene, np):
    from vispy import use, config
    from vispy.testing import TestingCanvas
    source=Path(root)/'src/vispy/visuals/tests/test_instanced_mesh.py'
    raw=source.read_text()
    source_digest=hashlib.sha256(source.read_bytes()).hexdigest()
    names=('test_mesh_with_vertex_values','test_compute_bounds','test_compute_bounds_with_rotation')
    selected={node.name:node for node in ast.parse(raw).body
              if isinstance(node,ast.FunctionDef) and node.name in names}
    assert set(selected)==set(names)
    namespace=dict(np=np,scene=scene,use=use,TestingCanvas=TestingCanvas)
    records=[]
    old=config['gl_backend']
    try:
        for name in names:
            decorators=[ast.unparse(item) for item in selected[name].decorator_list]
            assert decorators==['requires_pyopengl()', 'requires_application()'],decorators
            assert hashlib.sha256(source.read_bytes()).hexdigest()==source_digest
            node=copy.deepcopy(selected[name])
            # Only legacy availability decorators are removed. Every original
            # statement/assertion runs against the explicitly selected Dawn app.
            node.decorator_list=[]
            body=ast.get_source_segment(raw,selected[name])
            exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(source),'exec'),namespace)
            namespace[name]()
            assert hashlib.sha256(source.read_bytes()).hexdigest()==source_digest
            assert not any(key=='OpenGL' or key.startswith('OpenGL.') for key in sys.modules)
            records.append(dict(test=name,body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                scope='Original assertions; Dawn app; legacy availability decorators omitted'))
        return records
    finally:
        use(gl=old)
