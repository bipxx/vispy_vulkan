"""Real installed Vulkan resources intentionally owned until worker shutdown."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fail-after-draw', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    from vispy import app, gloo, _dawn
    assert _dawn.device_info()['backend'] == 'Vulkan'
    canvas = app.Canvas(app='dawn_headless', size=(32, 24), show=False, config={'samples': 0})
    canvas.set_current()
    program = gloo.Program('''attribute vec2 a_position;
        varying vec2 v_uv;
        void main() { gl_Position=vec4(a_position,0.0,1.0); v_uv=(a_position+1.0)*0.5; }''',
        '''uniform sampler2D u_image; varying vec2 v_uv;
        void main() { gl_FragColor=texture2D(u_image,v_uv); }''')
    program['a_position'] = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], dtype=np.float32)
    image = np.zeros((2, 2, 4), np.uint8)
    image[:] = [0, 255, 0, 255]
    texture = gloo.Texture2D(image, interpolation='nearest')
    program['u_image'] = texture
    gloo.set_viewport(0, 0, 32, 24)
    gloo.set_state(blend=False, depth_test=False)
    gloo.clear(color=(0, 0, 0, 1))
    program.draw('triangle_strip')
    pixels = gloo.read_pixels((0, 0, 32, 24), alpha=True)
    assert pixels.shape == (24, 32, 4) and np.all(pixels == [0, 255, 0, 255])
    np.save(args.output / 'green.npy', pixels)
    # This is an ownership regression fixture, not an application: keep real
    # objects alive so gc alone cannot impersonate global native shutdown.
    state = types.ModuleType('_vispy_shutdown_fixture_state')
    state.canvas, state.program, state.texture = canvas, program, texture
    sys.modules[state.__name__] = state
    before = dict(_dawn.probe())
    assert before['canvas_texture_bytes'] > 0 and before['live_buffer_bytes'] > 0, before
    (args.output / 'live-before-worker-shutdown.json').write_text(json.dumps(before, indent=2) + '\n')
    if args.fail_after_draw:
        raise RuntimeError('Intentional installed-script failure after real Vulkan allocation')
    # Deliberately no canvas.close()/native.shutdown(): the worker must own it.


if __name__ == '__main__':
    main()
