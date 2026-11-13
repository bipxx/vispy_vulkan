# SPDX-License-Identifier: AGPL-3.0-only
"""Generated-line semantic refusals must leave the same canvas usable."""
import re
import numpy as np
import pytest
from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu
VERTEX = 'attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}'
FRAGMENT = 'void main(){gl_FragColor=vec4(0,1,0,1);}'
BUFFER = 'layout(std430,set=0,binding=9) buffer Counter {uint value;} counter;'
CASES = [
    ('vertex-storage', BUFFER + 'attribute vec2 position;void main(){counter.value=1u;gl_Position=vec4(position,0,1);}',
     FRAGMENT, 'shared storage/side effects are unsupported'),
    ('vertex-clip-distance', 'attribute vec2 position;void main(){gl_ClipDistance[0]=1.;gl_Position=vec4(position,0,1);}',
     FRAGMENT, 'unsupported builtin gl_ClipDistance'),
    ('fragment-storage', VERTEX, BUFFER + 'void main(){counter.value=1u;gl_FragColor=vec4(1);}',
     'fragment external storage writes cannot execute outside line coverage'),
    ('fragment-atomic', VERTEX, BUFFER + 'void main(){atomicAdd(counter.value,1u);gl_FragColor=vec4(1);}',
     'fragment image/atomic/synchronization side effects cannot execute outside line coverage'),
    ('fragment-image', VERTEX,
     'layout(rgba32f,set=0,binding=9) uniform writeonly image2D target;'
     'void main(){imageStore(target,ivec2(0),vec4(1));gl_FragColor=vec4(1);}',
     'fragment image/atomic/synchronization side effects cannot execute outside line coverage'),
    ('fragment-barrier', VERTEX, 'void main(){memoryBarrier();gl_FragColor=vec4(1);}',
     'fragment image/atomic/synchronization side effects cannot execute outside line coverage'),
    ('fragment-early-tests', VERTEX, 'layout(early_fragment_tests) in;void main(){gl_FragColor=vec4(1);}',
     'early_fragment_tests requires true line coverage/depth integration'),
]


@pytest.mark.parametrize('name,vertex,fragment,diagnostic', CASES, ids=[c[0] for c in CASES])
def test_generated_line_semantic_refusal_and_same_canvas_recovery(name, vertex, fragment, diagnostic):
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), config={'samples': 0})
    owned = []
    try:
        canvas.set_current();gloo.set_viewport(0, 0, 16, 16)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
        gloo.set_line_width(5)
        positions = gloo.VertexBuffer(np.array([[-.75, 0], [.75, 0]], np.float32))
        refused = gloo.Program(vertex, fragment)
        owned.extend([positions, refused]);refused['position'] = positions
        with pytest.raises(RuntimeError, match=re.escape(diagnostic)):
            refused.draw('lines')
        recovered = gloo.Program(VERTEX, FRAGMENT)
        owned.append(recovered);recovered['position'] = positions
        gloo.clear(color=(0, 0, 0, 1));recovered.draw('lines')
        image = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        np.testing.assert_array_equal(image[8, 8], [0, 255, 0, 255])
        np.testing.assert_array_equal(image[0, 0], [0, 0, 0, 255])
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()
