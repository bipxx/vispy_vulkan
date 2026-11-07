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


@pytest.mark.parametrize('sampler,operation', [
    ('sampler1D', 'textureLod'), ('sampler1D', 'texelFetch'),
    ('sampler3D', 'textureLod'), ('sampler3D', 'texelFetch'),
    ('samplerCube', 'textureLod'),
])
@pytest.mark.parametrize('stage', ['vertex', 'fragment'])
@pytest.mark.parametrize('unsigned_index', [False, True])
def test_dynamic_explicit_dimensions_stage_and_unsigned_index(sampler, operation, stage, unsigned_index):
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), config={'samples': 0})
    owned = []
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False)
        coord = ('0' if sampler == 'sampler1D' else 'ivec3(0)') if operation == 'texelFetch' else (
            '.5' if sampler == 'sampler1D' else 'vec3(1,0,0)' if sampler == 'samplerCube' else 'vec3(.5)')
        level = '0' if operation == 'texelFetch' else '0.'
        declarations = 'uniform ' + sampler + ' images[2];uniform int selector;'
        expression = operation + '(images[' + ('uint(selector)' if unsigned_index else 'selector') + '],' + coord + ',' + level + ')'
        vertex = 'attribute vec2 position;varying vec4 value;'
        vertex += declarations if stage == 'vertex' else ''
        vertex += 'void main(){gl_Position=vec4(position,0,1);value=' + (expression if stage == 'vertex' else 'vec4(0)') + ';}'
        fragment = 'varying vec4 value;' + (declarations if stage == 'fragment' else '')
        fragment += 'void main(){gl_FragColor=' + (expression if stage == 'fragment' else 'value') + ';}'
        program = gloo.Program(vertex, fragment)
        source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        owned.extend([source, program]);program['position'] = source
        colors = [(255, 0, 0, 255), (0, 255, 0, 255)]
        for index, color in enumerate(colors):
            shape = {'sampler1D': (2, 4), 'sampler3D': (2, 2, 2, 4), 'samplerCube': (6, 2, 2, 4)}[sampler]
            cls = {'sampler1D': gloo.Texture1D, 'sampler3D': gloo.Texture3D, 'samplerCube': gloo.TextureCube}[sampler]
            texture = cls(np.broadcast_to(np.asarray(color, np.uint8), shape).copy(), interpolation='nearest')
            owned.append(texture);program['images[%d]' % index] = texture
        for selector in (0, 1, -1, 2):
            program['selector'] = selector
            gloo.clear(color=(1, 0, 1, 1));program.draw('triangles')
            wanted = colors[selector] if selector in (0, 1) else (0, 0, 0, 0)
            np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 8), alpha=True),
                np.broadcast_to(np.asarray(wanted, np.uint8), (8, 8, 4)))
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()


@pytest.mark.parametrize('stage', ['vertex', 'fragment'])
def test_dynamic_explicit_active_binding_limit_refusal_and_render_recovery(stage):
    info = _dawn.device_info()
    count = min(info['max_samplers_per_shader_stage'], info['max_sampled_textures_per_shader_stage'])
    assert 1 <= count <= 64, 'This finite boundary fixture needs a revised budget for larger grants'
    def sources(length):
        declarations = 'uniform sampler2D images[%d];uniform int selector;' % length
        sample = 'textureLod(images[selector],vec2(.5),0.)'
        vertex = 'attribute vec2 position;varying vec4 value;'
        vertex += declarations if stage == 'vertex' else ''
        vertex += 'void main(){gl_Position=vec4(position,0,1);value=' + (sample if stage == 'vertex' else 'vec4(0)') + ';}'
        fragment = 'varying vec4 value;' + (declarations if stage == 'fragment' else '')
        fragment += 'void main(){gl_FragColor=' + (sample if stage == 'fragment' else 'value') + ';}'
        return vertex, fragment
    refused = _dawn.compile_variant(*sources(count + 1))
    assert not refused['ok'] and 'exceed granted limit=' in refused['error'], refused
    recovered = _dawn.compile_variant(*sources(count))
    assert recovered['ok'], recovered
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), config={'samples': 0})
    owned = []
    try:
        canvas.set_current();gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False)
        program = gloo.Program(*sources(count))
        source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        texture = gloo.Texture2D(np.broadcast_to(np.array([0, 255, 0, 255], np.uint8), (2, 2, 4)).copy(), interpolation='nearest')
        owned.extend([source, texture, program]);program['position'] = source
        for index in range(count):program['images[%d]' % index] = texture
        program['selector'] = count - 1
        gloo.clear(color=(1, 0, 1, 1));program.draw('triangles')
        np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 8), alpha=True),
            np.broadcast_to(np.array([0, 255, 0, 255], np.uint8), (8, 8, 4)))
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()


@pytest.mark.parametrize('interpolation,channel', [('nearest', 255), ('linear', 191)])
@pytest.mark.parametrize('level', [-2., 0., 2.])
def test_dynamic_explicit_single_level_filtering_and_all_arguments_evaluated_once(interpolation, channel, level):
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), config={'samples': 0})
    owned = []
    try:
        canvas.set_current();gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False)
        fragment = ('uniform sampler2D images[2];uniform int selector;uniform float level;int calls=0;'
                    'int index_arg(){calls+=1;return selector;}'
                    'vec2 coordinate_arg(){calls+=2;return vec2(.625,.5);}'
                    'float level_arg(){calls+=4;return level;}'
                    'void main(){vec4 value=textureLod(images[index_arg()],coordinate_arg(),level_arg());'
                    'gl_FragColor=vec4(value.rgb,calls==7?1.:0.);}')
        program = gloo.Program('attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}', fragment)
        source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        owned.extend([source, program]);program['position'] = source;program['level'] = level
        for index, component in enumerate((0, 2)):
            values = np.zeros((2, 2, 4), np.uint8);values[:, :, 3] = 255;values[:, 1, component] = 255
            texture = gloo.Texture2D(values, interpolation=interpolation)
            owned.append(texture);program['images[%d]' % index] = texture
        for selector, component in enumerate((0, 2)):
            program['selector'] = selector
            gloo.clear(color=(1, 0, 1, 0));program.draw('triangles')
            actual = gloo.read_pixels((0, 0, 8, 8), alpha=True)
            wanted = np.zeros((8, 8, 4), np.int16);wanted[:, :, 3] = 255;wanted[:, :, component] = channel
            assert np.all(np.abs(actual.astype(np.int16) - wanted) <= (1 if interpolation == 'linear' else 0))
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()
