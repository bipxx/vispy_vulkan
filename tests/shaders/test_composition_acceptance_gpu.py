# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise the shader composition API with analytically predicted colors."""
import numpy as np
import pytest

from vispy import app, gloo
from vispy.visuals.shaders import Compiler, Function, FunctionChain, ModularProgram, Variable, Varying
from vispy.visuals.shaders.expression import TextExpression
from vispy.visuals.shaders.function import MainFunction, StatementList


pytestmark = pytest.mark.gpu
VERTEX = 'attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }'
TRIANGLE = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)


@pytest.fixture
def shader_draw():
    from vispy import _dawn

    canvas = app.Canvas(app='dawn_headless', size=(16, 16), show=False,
                        config={'samples': 0})
    canvas.set_current()
    programs = []

    def build(vert, frag, *, modular=False):
        cls = ModularProgram if modular else gloo.Program
        program = cls(vert, frag)
        programs.append(program)
        program['a_pos'] = TRIANGLE
        return program

    def pixel(program, row=8, col=8):
        gloo.set_viewport(0, 0, 16, 16)
        gloo.set_state(blend=False, depth_test=False)
        gloo.clear(color=(0, 0, 0, 1))
        program.draw('triangles')
        return gloo.read_pixels((0, 0, 16, 16), alpha=True)[row, col]

    try:
        yield build, pixel
    finally:
        for program in programs:
            program.delete()
        try:
            gloo.flush()
        finally:
            canvas.close()
            _dawn.process_events()


@pytest.mark.parametrize('pretty', [True, False])
def test_compiler_naming_and_unresolved_template_recovery(shader_draw, pretty):
    from vispy import _dawn

    build, pixel = shader_draw
    vert = MainFunction('vert', VERTEX.replace('0.0, 1.0', '$gain * 0.0, 1.0'))
    frag = MainFunction('frag',
                        'void main() { gl_FragColor = vec4($a() + $b(), $gain, 0.0, 1.0); }')
    gain = Variable('uniform float gain', value=0.25)
    a = Function('float term() { return 0.125; }')
    b = Function('float term() { return 0.375; }')
    vert['gain'] = frag['gain'] = gain
    frag['a'], frag['b'] = a, b
    compiler = Compiler(vert=vert, frag=frag)
    code = compiler.compile(pretty=pretty)
    assert set(code) == {'vert', 'frag'}
    assert compiler[a] != compiler[b]
    assert all(f'uniform float {compiler[gain]};' in stage for stage in code.values())
    assert all(f'{compiler[term]}()' in code['frag'] for term in (a, b))
    assert code == compiler.compile(pretty=pretty)
    program = build(code['vert'], code['frag'])
    program[compiler[gain]] = 0.25
    np.testing.assert_allclose(pixel(program), [128, 64, 0, 255], atol=1)

    b.code = 'float term() { return $missing; }'
    broken = compiler.compile(pretty=pretty)
    assert '$missing' in broken['frag']
    rejected = _dawn.compile_variant(broken['vert'], broken['frag'])
    assert not rejected['ok'] and rejected['error'], rejected
    b['missing'] = '0.625'
    recovered = compiler.compile(pretty=pretty)
    assert '$missing' not in recovered['frag']
    program = build(recovered['vert'], recovered['frag'])
    program[compiler[gain]] = 0.25
    np.testing.assert_allclose(pixel(program), [191, 64, 0, 255], atol=1)


def test_functionchain_live_order_and_incompatible_recovery(shader_draw):
    build, pixel = shader_draw
    program = build(VERTEX,
                    'void main() { gl_FragColor = vec4($chain(0.125), 0.0, 0.0, 1.0); }',
                    modular=True)
    add = Function('float add_step(float x) { return x + 0.25; }')
    double = Function('float double_step(float x) { return 2.0 * x; }')
    chain = FunctionChain('pipeline', [add, double])
    program.frag['chain'] = chain
    np.testing.assert_allclose(pixel(program), [191, 0, 0, 255], atol=1)
    chain.functions = [double, add]
    np.testing.assert_allclose(pixel(program), [128, 0, 0, 255], atol=1)
    bad = Function('float bad_step(vec2 x) { return x.x; }')
    chain[1] = bad
    with pytest.raises(Exception, match='Cannot chain output'):
        pixel(program)
    chain[1] = add
    np.testing.assert_allclose(pixel(program), [128, 0, 0, 255], atol=1)


def test_mainfunction_version_static_names_and_stage_repair(shader_draw):
    from vispy import _dawn

    build, pixel = shader_draw
    vert = MainFunction('vert', '#version 120\n' + VERTEX)
    source = ('#version 120\n'
              'float local_value(float x) { return x * 0.5; }\n'
              'void main() { gl_FragColor = vec4(0.0, local_value($level), 0.0, 1.0); }')
    frag = MainFunction('frag', source)
    level = Variable('uniform float level', value=0.5)
    frag['level'] = level
    compiler = Compiler(vert=vert, frag=frag)
    code = compiler.compile()
    assert all(stage.startswith('#version 120') for stage in code.values())
    assert 'local_value' in frag.static_names()
    program = build(code['vert'], code['frag'])
    program[compiler[level]] = 0.5
    np.testing.assert_allclose(pixel(program), [0, 64, 0, 255], atol=1)
    frag.code = source.replace('x * 0.5', 'missing_identifier')
    invalid = compiler.compile()
    rejected = _dawn.compile_variant(invalid['vert'], invalid['frag'])
    assert not rejected['ok'] and 'missing_identifier' in rejected['error'], rejected
    frag.code = source.replace('x * 0.5', 'x * 1.5')
    assert frag['level'] is level
    code = compiler.compile()
    program = build(code['vert'], code['frag'])
    program[compiler[level]] = 0.5
    np.testing.assert_allclose(pixel(program), [0, 191, 0, 255], atol=1)


def test_statementlist_priority_ties_duplicate_and_missing_removal(shader_draw):
    build, pixel = shader_draw
    program = build(VERTEX, '''
        void main() { float x = 0.125; $steps
                      gl_FragColor = vec4(x, 0.0, 0.0, 1.0); }
        ''', modular=True)
    statements = StatementList()
    add = TextExpression('x += 0.25')
    double = TextExpression('x *= 2.0')
    initialize = TextExpression('x += 0.0625')
    statements.add(add, position=8)
    statements.add(double, position=8)
    statements.add(initialize, position=2)
    program.frag['steps'] = statements
    np.testing.assert_allclose(pixel(program), [223, 0, 0, 255], atol=1)
    statements.add(add, position=0)
    np.testing.assert_allclose(pixel(program), [223, 0, 0, 255], atol=1)
    statements.remove(add)
    with pytest.raises(KeyError):
        statements.remove(add)
    np.testing.assert_allclose(pixel(program), [96, 0, 0, 255], atol=1)
    statements.add(add, position=8)
    np.testing.assert_allclose(pixel(program), [159, 0, 0, 255], atol=1)


def test_varying_interpolation_rebinding_and_type_recovery(shader_draw):
    from vispy import _dawn

    build, pixel = shader_draw
    frag = 'void main() { gl_FragColor = vec4($signal, 0.0, 0.0, 1.0); }'
    program = build(VERTEX, frag, modular=True)
    signal = Varying('signal', dtype='float')
    program.vert[signal] = '(a_pos.x + 1.0) * 0.25'
    program.frag['signal'] = signal
    # Column 7 has NDC x=-1/16, so the initial varying is 15/64.
    np.testing.assert_allclose(pixel(program, col=7), [60, 0, 0, 255], atol=1)
    second = Varying('second', dtype='float')
    program.vert[signal] = None
    program.vert[second] = '(1.0 - a_pos.x) * 0.25'
    program.frag['signal'] = second
    compiler = Compiler(vert=program.vert, frag=program.frag)
    code = compiler.compile()
    name = compiler[second]
    wrong = code['frag'].replace(f'varying float {name};', f'varying vec2 {name};')
    wrong = wrong.replace(f'vec4({name},', f'vec4({name}.x,')
    assert wrong != code['frag']
    rejected = _dawn.compile_variant(code['vert'], wrong)
    assert not rejected['ok'] and name in rejected['error'], rejected
    np.testing.assert_allclose(pixel(program, col=7), [68, 0, 0, 255], atol=1)
