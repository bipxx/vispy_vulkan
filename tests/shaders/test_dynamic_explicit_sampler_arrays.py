# SPDX-License-Identifier: AGPL-3.0-only
"""Analytic output for dynamic explicit sampling; not implicit-derivative proof."""
import numpy as np
import pytest
from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('family', ['float', 'signed', 'unsigned'])
@pytest.mark.parametrize('operation', ['textureLod', 'texelFetch'])
@pytest.mark.parametrize('divergent', [False, True])
def test_dynamic_explicit_selection_bounds_single_evaluation_rebinding_and_loss(family, operation, divergent):
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), config={'samples': 0})
    owned = []
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False)
        sampler = dict(float='sampler2D', signed='isampler2D', unsigned='usampler2D')[family]
        words = dict(float=[1., .5, .25], signed=[-2147483601, 2147483600, -123456789],
                     unsigned=[0xf0000003, 0x80000011, 0xfffffffb])[family]
        literal = lambda value: (str(value) + 'u' if family == 'unsigned' else str(value))
        coordinate, level = ('ivec2(0)', '0') if operation == 'texelFetch' else ('vec2(.5)', '0.')
        shader = ('uniform ' + sampler + ' images[2];uniform int selector;int calls=0;'
                  'int next_index(){calls+=1;return selector' +
                  ('+int(gl_FragCoord.x>=4.)' if divergent else '') + ';}'
                  'void main(){' + ('float' if family == 'float' else 'uint' if family == 'unsigned' else 'int') +
                  ' word=' + operation + '(images[next_index()],' + coordinate + ',' + level + ').r;'
                  'vec3 color=word==' + literal(words[0]) + '?vec3(1,0,0):word==' + literal(words[1]) +
                  '?vec3(0,1,0):word==' + literal(words[2]) + '?vec3(0,0,1):vec3(0);'
                  'gl_FragColor=vec4(color,calls==1?1.:0.);}')
        program = gloo.Program('attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}', shader)
        source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        owned.extend([source, program]);program['position'] = source
        def texture(word):
            dtype = dict(float=np.float32, signed=np.int32, unsigned=np.uint32)[family]
            options = dict(internalformat={'float': 'r32f', 'signed': 'r32i', 'unsigned': 'r32ui'}[family])
            result = gloo.Texture2D(np.full((2, 2), word, dtype), interpolation='nearest', **options)
            owned.append(result)
            return result
        program['images[0]'] = texture(words[0]);program['images[1]'] = texture(words[1])
        colors = [(255, 0, 0, 255), (0, 255, 0, 255)]
        def check(selector):
            program['selector'] = selector
            gloo.clear(color=(1, 0, 1, 0));program.draw('triangles')
            actual = gloo.read_pixels((0, 0, 8, 8), alpha=True)
            expected = np.zeros((8, 8, 4), np.uint8);expected[:, :, 3] = 255
            for column in range(8):
                index = selector + int(divergent and column >= 4)
                if 0 <= index < 2:expected[:, column] = colors[index]
            np.testing.assert_array_equal(actual, expected)
        for selector in (0, 1, -1, 2):check(selector)
        program['images[0]'] = texture(words[2]);colors[0] = (0, 0, 255, 255)
        check(0)
        generation = _dawn.probe()['device_generation']
        _dawn.lose_device();canvas.set_current();gloo.set_viewport(0, 0, 8, 8)
        check(0)
        assert _dawn.probe()['device_generation'] > generation
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()


@pytest.mark.parametrize('case', ['declaration', 'macro', 'nested'])
def test_generated_helper_collisions_and_nested_explicit_calls_render(case):
    from test_sampler_arrays import scene, draw
    prefix = ('float vispy_dynamic_sample_0(float value){return value;}\n' if case == 'declaration'
              else '#define vispy_dynamic_sample_0 user_macro_name\n' if case == 'macro' else '')
    coordinate = ('vec2(textureLod(images[selector],vec2(.5),0.).r)'
                  if case == 'nested' else 'vec2(.5)')
    fragment = (prefix + 'uniform sampler2D images[2];uniform int selector;'
                'void main(){gl_FragColor=textureLod(images[selector],' + coordinate + ',0.);}')
    with scene(fragment) as (_, program, _a, _b, _owned):
        program['selector'] = 1
        np.testing.assert_array_equal(draw(program),
            np.broadcast_to(np.array([0, 255, 0, 255], np.uint8), (8, 16, 4)))
