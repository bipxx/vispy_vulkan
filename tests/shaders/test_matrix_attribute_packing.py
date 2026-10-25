# SPDX-License-Identifier: AGPL-3.0-only
"""Matrix vertex records retain column words, counts and updates without a GPU."""
import numpy as np
import pytest

from vispy.gloo import Program, VertexBuffer


MATRICES = [(f'mat{c}' if c == r else f'mat{c}x{r}', c, r)
            for c in (2, 3, 4) for r in (2, 3, 4)]


def program(gtype):
    return Program('attribute %s transform; void main(){}' % gtype,
                   'void main(){}')


def uploaded(buffer, commands):
    return [command[3] for command in commands
            if command[0] == 'DATA' and command[1] == buffer.id][-1]


@pytest.mark.parametrize('gtype,columns,rows', MATRICES)
@pytest.mark.parametrize('form', ['flat', 'columns', 'strided'])
def test_matrix_records_keep_vertex_count_and_exact_column_words(gtype, columns, rows, form):
    shader = program(gtype)
    words = np.arange(5 * columns * rows, dtype=np.float32).reshape(5, columns, rows)
    if form == 'flat':
        values = words.reshape(5, -1)
    elif form == 'strided':
        values = np.zeros((5, columns, rows * 2), dtype=np.float32)[:, :, ::2]
        values[:] = words
        assert not values.flags.c_contiguous
    else:
        values = words
    shader['transform'] = values
    buffer = shader['transform']
    assert buffer.size == 5
    assert buffer.stride == columns * rows * 4
    assert buffer.dtype['f0'].shape == (columns, rows)
    commands = shader.glir.clear()
    np.testing.assert_array_equal(uploaded(buffer, commands)['f0'], words)
    attributes = [command for command in commands if command[0] == 'ATTRIBUTE']
    assert attributes[-1][2:5] == ('transform', gtype, (buffer.id, buffer.stride, 0))


@pytest.mark.parametrize('gtype,columns,rows', MATRICES)
def test_later_matrix_assignment_updates_the_existing_vertex_records(gtype, columns, rows):
    shader = program(gtype)
    shader['transform'] = np.zeros((5, columns * rows), dtype=np.float32)
    buffer = shader['transform']
    shader.glir.clear()
    words = np.arange(3 * columns * rows, dtype=np.float32).reshape(3, columns, rows)
    shader['transform'] = words
    assert shader['transform'] is buffer
    assert buffer.size == 3
    commands = shader.glir.clear()
    np.testing.assert_array_equal(uploaded(buffer, commands)['f0'], words)


@pytest.mark.parametrize('shape', [(5,), (5, 8), (5, 3, 2), (5, 2, 3, 1)])
def test_wrong_shape_does_not_replace_existing_matrix_binding(shape):
    shader = program('mat2x3')
    shader['transform'] = np.zeros((5, 2, 3), dtype=np.float32)
    previous = shader['transform']
    shader.glir.clear()
    with pytest.raises(ValueError, match='needs shape'):
        shader['transform'] = np.zeros(shape, dtype=np.float32)
    assert shader['transform'] is previous and previous.size == 5
    assert shader.glir.clear() == []


@pytest.mark.parametrize('dtype', [np.float64, np.int32, np.uint32, '>f4'])
def test_wrong_scalar_representation_is_rejected_before_upload(dtype):
    shader = program('mat3')
    shader.glir.clear()
    with pytest.raises(TypeError, match='native float32'):
        shader['transform'] = np.zeros((5, 3, 3), dtype=dtype)
    assert shader.glir.clear() == []


def test_interleaved_matrix_view_preserves_its_record_stride_and_offset():
    records = np.zeros(5, dtype=[('position', np.float32, 2),
                                 ('transform', np.float32, (3, 2)),
                                 ('padding', np.float32, 4)])
    buffer = VertexBuffer(records)
    view = buffer['transform']
    shader = program('mat3x2')
    shader['transform'] = view
    assert shader['transform'] is view
    commands = shader.glir.clear()
    binding = [command for command in commands if command[0] == 'ATTRIBUTE'][-1]
    assert binding[2:5] == ('transform', 'mat3x2', (buffer.id, records.dtype.itemsize, 8))


@pytest.mark.parametrize('gtype,columns,rows', MATRICES)
def test_flat_constant_matrix_stays_a_constant(gtype, columns, rows):
    shader = program(gtype)
    values = tuple(float(n) for n in range(columns * rows))
    shader['transform'] = values
    commands = shader.glir.clear()
    binding = [command for command in commands if command[0] == 'ATTRIBUTE'][-1]
    assert binding[2:5] == ('transform', gtype, (0, *values))
