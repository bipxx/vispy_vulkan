# SPDX-License-Identifier: AGPL-3.0-only
"""Public declaration/upload contracts; no native compiler or device required."""
import numpy as np
import pytest

from vispy.gloo.program import Program


@pytest.mark.parametrize('gtype,components,dtype', [
    ('float', 1, np.float32), ('int', 1, np.int32),
    ('bool', 1, np.int32), ('vec3', 3, np.float32),
    ('mat2', 4, np.float32), ('mat2x3', 6, np.float32),
    ('mat3x4', 12, np.float32), ('mat4x2', 8, np.float32),
])
def test_nested_whole_subarray_and_leaf_uploads(gtype, components, dtype):
    program = Program('uniform %s grid[2][3];' % gtype, 'void main(){}')
    values = np.arange(6 * components).reshape(2, 3, components)
    program._glir.clear()
    program['grid'] = values
    np.testing.assert_array_equal(program['grid'], values.astype(dtype).ravel())
    assert program['grid'].dtype == dtype
    program['grid[1]'] = values[1]
    program['grid[1][2]'] = values[1, 2]
    np.testing.assert_array_equal(program['grid[1]'], values[1].astype(dtype).ravel())
    np.testing.assert_array_equal(program['grid[1][2]'], values[1, 2].astype(dtype).ravel())
    assert 'grid[1][2]' in program
    assert 'grid[2][0]' not in program
    assert 'grid[0][3]' not in program
    assert ('uniform_array', gtype, 'grid[1]') in program.variables
    assert ('uniform', gtype, 'grid[1][2]') in program.variables
    commands = program._glir.clear()
    assert [command[:4] for command in commands] == [
        ('UNIFORM', program.id, name, gtype)
        for name in ('grid', 'grid[1]', 'grid[1][2]')]
    for command, expected in zip(commands, (values, values[1], values[1, 2])):
        np.testing.assert_array_equal(command[4], expected.astype(dtype).ravel())
        assert command[4].flags.c_contiguous


@pytest.mark.parametrize('shape', [(3, 2, 1), (6, 1), (2, 3, 2)])
def test_same_count_or_wrong_components_do_not_replace_upload(shape):
    program = Program('uniform float grid[2][3];', 'void main(){}')
    program['grid'] = np.zeros((2, 3, 1))
    before = program['grid'].copy()
    program._glir.clear()
    with pytest.raises(ValueError, match='needs shape'):
        program['grid'] = np.ones(shape)
    np.testing.assert_array_equal(program['grid'], before)
    assert program._glir.clear() == []


def test_natural_scalar_shape_and_three_dimensional_prefixes():
    program = Program('uniform float grid[2][3][4];', 'void main(){}')
    values = np.arange(24).reshape(2, 3, 4)
    program['grid'] = values
    program['grid[1]'] = values[1]
    program['grid[1][2]'] = values[1, 2, :, None]
    program['grid[1][2][3]'] = 23
    np.testing.assert_array_equal(program['grid'], values.ravel())
    assert program._array_shapes['grid[1]'] == (3, 4)
    assert program._array_shapes['grid[1][2]'] == (4,)


def test_one_dimensional_scalar_contract_is_preserved():
    program = Program('uniform float grid[3];', 'void main(){}')
    program['grid'] = np.ones((3, 1))
    with pytest.raises(ValueError, match='needs shape'):
        program['grid'] = np.ones(3)
    assert len(program.variables) == 4


@pytest.mark.parametrize('declaration', [
    'uniform float grid[0][3];', 'uniform float grid[2][0];',
    'attribute vec2 grid[2][3];', 'varying vec2 grid[2][3];',
    'uniform sampler2DArray grid[2][3];',
])
def test_invalid_or_separately_unsupported_declarations(declaration):
    with pytest.raises(ValueError):
        Program(declaration, 'void main(){}')


@pytest.mark.parametrize('first,second', [
    ('float grid[2][3]', 'float grid[3][2]'),
    ('float grid', 'float grid[2][3]'),
    ('float grid[2][3]', 'float grid'),
    ('float grid[2][3]', 'vec2 grid[2][3]'),
])
def test_incompatible_declarations_are_rejected_in_either_stage(first, second):
    with pytest.raises(ValueError, match='conflicting shapes or types'):
        Program('uniform %s;' % first, 'uniform %s;' % second)


def test_replacing_shaders_drops_previous_shape_metadata():
    program = Program('uniform float grid[2][3];', 'void main(){}')
    program.set_shaders('uniform float next[4][2];', 'void main(){}')
    assert 'grid' not in program._array_shapes
    assert program._array_shapes['next'] == (4, 2)


def test_whitespace_and_repeated_matching_declarations():
    program = Program('uniform vec2 grid [ 2 ] [ 3 ];', 'uniform vec2 grid[2][3];')
    program['grid'] = np.zeros((2, 3, 2))
    assert len(program.variables) == 9


@pytest.mark.parametrize('writes,replay', [
    (['grid', 'grid[1][2]', 'grid'], ['grid[1][2]', 'grid']),
    (['grid', 'grid[1]', 'grid[1][2]', 'grid[1]'], ['grid', 'grid[1][2]', 'grid[1]']),
    (['grid', 'grid[1]', 'grid[1][2]', 'grid', 'grid[1][2]'], ['grid[1]', 'grid', 'grid[1][2]']),
])
def test_shader_replacement_restores_shapes_in_last_write_order(writes, replay):
    vertex, fragment = 'uniform float grid[2][3];', 'void main(){}'
    program = Program(vertex, fragment)
    for step, name in enumerate(writes):
        shape = {'grid': (2, 3, 1), 'grid[1]': (3, 1), 'grid[1][2]': (1,)}[name]
        program[name] = np.full(shape, step, dtype=np.float32)
    cached = {name: program[name].copy() for name in set(writes)}
    program._glir.clear()
    program.set_shaders(vertex, fragment)
    uploads = [c for c in program._glir.clear() if c[0] == 'UNIFORM']
    assert [c[2] for c in uploads] == replay
    for command in uploads:
        np.testing.assert_array_equal(command[4], cached[command[2]])
    for name, value in cached.items():
        np.testing.assert_array_equal(program[name], value)


@pytest.mark.parametrize('gtype', ['sampler1D', 'sampler2D', 'sampler3D', 'samplerCube',
                                 'isampler2D', 'usampler2D'])
def test_nested_sampler_leaf_names_are_public_uniforms(gtype):
    program = Program('uniform %s images[2][3];' % gtype, 'void main(){}')
    assert program._array_shapes['images'] == (2, 3)
    for row in range(2):
        for column in range(3):
            name = 'images[%d][%d]' % (row, column)
            assert ('uniform', gtype, name) in program.variables
    assert len(program.variables) == 9
