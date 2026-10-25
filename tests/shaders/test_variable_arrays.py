# SPDX-License-Identifier: AGPL-3.0-only
"""Array declarations survive shader composition and cache-aware GLIR uploads."""
import numpy as np
import pytest
from vispy.visuals.shaders import Variable, ModularProgram


@pytest.mark.parametrize('gtype,components', [('float', 1), ('int', 1), ('bool', 1),
    ('vec3', 3), ('bvec3', 3), ('mat2', 4), ('mat2x3', 6), ('mat4x2', 8)])
@pytest.mark.parametrize('shape', [(2,), (2, 3), (2, 2, 3)])
def test_declared_array_shape_and_values(gtype, components, shape):
    suffix = ''.join('[%d]' % d for d in shape)
    values = np.arange(np.prod(shape) * components).reshape(shape + (components,))
    variable = Variable('uniform %s grid%s' % (gtype, suffix), values)
    assert variable.name == 'grid'
    assert variable.array_shape == shape
    assert variable.definition({variable: 'grid_2'}, (120, ''), None) == (
        'uniform %s grid_2%s;' % (gtype, suffix))
    assert variable.expression({variable: 'grid_2'}) == 'grid_2'
    np.testing.assert_array_equal(variable.value, values.astype(variable.value.dtype))


def test_rejected_shape_does_not_change_value_or_state():
    variable = Variable('uniform float grid[2][3]', np.zeros((2, 3, 1)))
    before, identity = variable.value, variable.state_id
    for value in (np.ones((3, 2, 1)), np.ones((6, 1)), np.ones((2, 3, 2))):
        with pytest.raises(ValueError, match='needs shape'):
            variable.value = value
        assert variable.value is before and variable.state_id == identity
    with pytest.raises((TypeError, ValueError)):
        variable.value = [['invalid'] * 3] * 2
    assert variable.value is before and variable.state_id == identity


def test_natural_multidimensional_scalar_shape():
    variable = Variable('uniform float grid[2][3]', np.arange(6).reshape(2, 3))
    assert variable.value.shape == (2, 3, 1)
    np.testing.assert_array_equal(variable.value[..., 0], np.arange(6).reshape(2, 3))


@pytest.mark.parametrize('name', ['grid[0]', 'grid[-1]', 'grid[]', 'grid[2]tail', 'grid[n]'])
def test_invalid_dimensions_fail_explicitly(name):
    with pytest.raises(ValueError):
        Variable(name, vtype='uniform', dtype='float')


@pytest.mark.parametrize('declaration', ['grid[2]', 'uniform sampler2D grid[2]',
                                      'attribute float grid[2]'])
def test_array_values_need_an_explicit_numeric_uniform(declaration):
    with pytest.raises(TypeError, match='explicit non-sampler uniform type'):
        Variable(declaration, np.zeros((2, 1)))


def test_composed_array_update_and_cache_identity():
    variable = Variable('uniform float grid[2][3]', np.arange(6).reshape(2, 3, 1))
    program = ModularProgram(
        'attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}',
        'void main(){gl_FragColor=vec4($grid[1][2]);}')
    program.frag['grid'] = variable
    program.build_if_needed()
    name = program.compiler[variable]
    assert program._array_shapes[name] == (2, 3)
    program._glir.clear()
    program.update_variables()
    commands = [c for c in program._glir.clear() if c[0] == 'UNIFORM']
    assert len(commands) == 1 and commands[0][2:4] == (name, 'float')
    np.testing.assert_array_equal(commands[0][4], np.arange(6, dtype=np.float32))
    program.update_variables()
    assert program._glir.clear() == []
    variable.value = np.full((2, 3, 1), 7)
    assert not program._need_build
    program.update_variables()
    commands = program._glir.clear()
    assert len(commands) == 1 and commands[0][0:4] == ('UNIFORM', program.id, name, 'float')
    np.testing.assert_array_equal(commands[0][4], np.full(6, 7, dtype=np.float32))


def test_same_base_names_keep_independent_shapes_after_compiler_renaming():
    first = Variable('uniform float grid[2][3]', np.zeros((2, 3, 1)))
    second = Variable('uniform float grid[3][2]', np.ones((3, 2, 1)))
    program = ModularProgram('void main(){gl_Position=vec4(0);}',
        'void main(){gl_FragColor=vec4($a[1][2]+$b[2][1]);}')
    program.frag['a'], program.frag['b'] = first, second
    program.build_if_needed()
    a, b = program.compiler[first], program.compiler[second]
    assert a != b and '[' not in a and '[' not in b
    assert program._array_shapes[a] == (2, 3) and program._array_shapes[b] == (3, 2)
    program.update_variables()
    np.testing.assert_array_equal(program[a], np.zeros(6))
    np.testing.assert_array_equal(program[b], np.ones(6))


@pytest.mark.parametrize('version,keyword', [((120,''),'varying'), ((330,''),'in')])
def test_varying_input_preserves_source_shape_and_compiler_name(version, keyword):
    from vispy.visuals.shaders import Varying
    source = Varying('values[2][3]', dtype='vec3')
    incoming = source.invar()
    assert incoming.array_shape == (2, 3)
    assert incoming.definition({source:'renamed'}, version, 'fragment') == keyword + ' vec3 renamed[2][3];'
    assert incoming.expression({source:'renamed'}) == 'renamed'
    if version[0] > 120:
        assert source.invar(array=True).definition({source:'renamed'}, version, 'geometry') == 'in vec3 renamed[][2][3];'
