"""CPU-only public construction, exact GLIR transport and rejection contracts."""
import sys

import numpy as np
import pytest

from vispy import gloo
from vispy.gloo import glir
from vispy.gloo.dawn_parser import pack_commands
from vispy.gloo.globject import GLObject


CASES = [
    ('r32i', np.int32, 'isampler2D', 0x8235, [-2147483648, -16777217, -1, 0, 1, 16777217, 2147483646, 2147483647]),
    ('r32ui', np.uint32, 'usampler2D', 0x8236, [0, 1, 16777215, 16777217, 2147483647, 2147483648, 4294967294, 4294967295]),
]
VERTEX = 'attribute vec2 a_position; void main(){gl_Position=vec4(a_position,0.,1.);}'


def program(sampler):
    return gloo.Program(VERTEX, 'uniform %s u_words; void main(){}' % sampler)


def frozen(value):
    if isinstance(value, np.ndarray):
        return ('array', value.dtype.str, value.shape, value.tobytes())
    if isinstance(value, (tuple, list)):
        return tuple(frozen(item) for item in value)
    if isinstance(value, dict):
        return {key: frozen(item) for key, item in value.items()}
    if isinstance(value, GLObject):
        return ('object', value.id)
    return value


def queue(obj):
    return frozen(obj.glir._shared._commands)


def state(obj):
    names = ('_shape', '_format', '_internalformat', '_interpolation', '_wrapping',
             '_user_variables', '_pending_variables')
    return {name: frozen(getattr(obj, name)) for name in names if hasattr(obj, name)}


@pytest.fixture(autouse=True)
def no_native_import():
    assert 'vispy._dawn' not in sys.modules
    yield
    assert 'vispy._dawn' not in sys.modules


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
@pytest.mark.parametrize('explicit_red', [False, True])
def test_constructor_keeps_every_word_and_numeric_size(internal, dtype, sampler, storage, words, explicit_red):
    values = np.array(words, dtype=dtype).reshape(2, 4)
    tex = gloo.Texture2D(values, internalformat=internal, **({'format': 'red'} if explicit_red else {}))
    assert tex.shape == (2, 4, 1)
    assert tex.format == 'red' and tex.internalformat == internal
    assert tex.glsl_type == ('uniform', sampler) and tex.glsl_sampler_type == sampler
    assert tex.glsl_sample == 'texture' and tex.interpolation == 'nearest'
    commands = tex.glir.clear()
    sizes = [cmd for cmd in commands if cmd[0] == 'SIZE']
    assert sizes and all(cmd[2:] == ((2, 4, 1), 0x8D94, storage) for cmd in sizes)
    payloads = [cmd[3] for cmd in commands if cmd[0] == 'DATA']
    assert len(payloads) == 1 and payloads[0].dtype == np.dtype(dtype)
    assert payloads[0].tobytes() == values.tobytes()
    packed, arrays = pack_commands(commands)
    assert arrays == []
    data = next(cmd[3] for cmd in packed if cmd[0] == 'DATA')
    assert data == {'__bytes__': values.tobytes(), 'shape': [2, 4, 1], 'dtype': np.dtype(dtype).str}


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
def test_shape_allocation_partial_and_copied_updates(internal, dtype, sampler, storage, words):
    tex = gloo.Texture2D(shape=(3, 4), internalformat=internal)
    assert not any(cmd[0] == 'DATA' for cmd in tex.glir.clear())
    part = np.array(words[:4], dtype=dtype).reshape(2, 2)
    tex.set_data(part, offset=(1, 1), copy=True)
    commands = tex.glir.clear()
    assert len(commands) == 1 and commands[0][:3] == ('DATA', tex.id, (1, 1))
    assert commands[0][3].shape == (2, 2, 1)
    original = part.tobytes()
    part[...] = 0
    assert commands[0][3].tobytes() == original
    update = np.array(words[4:6], dtype=dtype).reshape(1, 2, 1)
    tex[0:1, 1:3] = update
    command = tex.glir.clear()[-1]
    assert command[:3] == ('DATA', tex.id, (0, 1)) and command[3].tobytes() == update.tobytes()
    tex.resize((4, 5))
    assert tex.shape == (4, 5, 1) and tex.format == 'red' and tex.internalformat == internal
    assert tex.glir.clear()[-1] == ('SIZE', tex.id, (4, 5, 1), 0x8D94, storage)


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
def test_both_parser_transports_keep_integer_formats_and_upload_type(monkeypatch, internal, dtype, sampler, storage, words):
    tex = gloo.Texture2D(np.array(words, dtype=dtype).reshape(2, 4), internalformat=internal)
    commands = tex.glir.clear()
    size = next(cmd for cmd in commands if cmd[0] == 'SIZE')
    upload = next(cmd for cmd in commands if cmd[0] == 'DATA')
    calls = []
    monkeypatch.setattr(glir.gl, 'glTexImage2D', lambda *args: calls.append(('SIZE', args)))
    monkeypatch.setattr(glir.gl, 'glTexSubImage2D', lambda *args: calls.append(('DATA', args)))
    backend = object.__new__(glir.GlirTexture2D)
    backend._shape_formats = 0
    backend.activate = lambda: None
    backend.set_size(*size[2:])
    backend.set_data(*upload[2:])
    assert calls[0][1][2:4] == (storage, 0x8D94)
    assert calls[1][1][4] == 0x8D94
    assert calls[1][1][5] == (glir.gl.GL_INT if dtype is np.int32 else glir.gl.GL_UNSIGNED_INT)
    assert calls[1][1][6].tobytes() == upload[3].tobytes()
    packed, _ = pack_commands([size, upload])
    assert packed[0][3:] == (0x8D94, storage)
    assert packed[1][3]['__bytes__'] == upload[3].tobytes()


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
@pytest.mark.parametrize('bad_dtype', [np.float32, np.float64, np.int16, np.uint16, np.int64, np.uint64, np.bool_])
def test_bad_constructor_dtype_rejected_before_create(internal, dtype, sampler, storage, words, bad_dtype):
    previous_id = GLObject._idcount
    with pytest.raises(ValueError, match='requires .* data'):
        gloo.Texture2D(np.zeros((2, 4), bad_dtype), internalformat=internal)
    assert GLObject._idcount == previous_id


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
def test_wrong_signedness_and_non_native_endian_rejected(internal, dtype, sampler, storage, words):
    for bad_dtype in (np.uint32 if dtype is np.int32 else np.int32, np.dtype(dtype).newbyteorder('>')):
        previous_id = GLObject._idcount
        with pytest.raises(ValueError):
            gloo.Texture2D(np.zeros((2, 4), bad_dtype), internalformat=internal)
        assert GLObject._idcount == previous_id


@pytest.mark.parametrize('kwargs', [
    {'shape': (2, 4, 2)}, {'shape': (2, 4), 'format': 'luminance'},
    {'shape': (2, 4), 'format': 'rg'}, {'shape': (2, 4), 'interpolation': 'linear'},
    {'shape': (2, 4), 'interpolation': ('nearest', 'linear')},
    {'shape': (2, 4), 'interpolation': ''},
])
def test_bad_constructor_layout_or_filter_rejected_before_create(kwargs):
    previous_id = GLObject._idcount
    with pytest.raises(ValueError):
        gloo.Texture2D(internalformat='r32ui', **kwargs)
    assert GLObject._idcount == previous_id


@pytest.mark.parametrize('operation', [
    lambda tex: tex.set_data(np.zeros((2, 4), np.float32)),
    lambda tex: tex.set_data(np.zeros((2, 4), np.int32)),
    lambda tex: tex.set_data(np.zeros((2, 4), np.uint64)),
    lambda tex: tex.set_data(np.zeros((1, 1, 2), np.uint32), offset=(0, 0)),
    lambda tex: tex.set_data(np.zeros((3, 5), np.uint32), offset=(1, 0)),
    lambda tex: tex.set_data(np.zeros((1, 1), np.uint32), offset=(-1, 0)),
    lambda tex: tex.set_data(np.zeros((1, 1), np.uint32), offset=(0,)),
    lambda tex: tex.set_data(np.zeros((1, 1), np.uint32), offset=(False, 0)),
    lambda tex: tex.resize((2, 4, 2)),
    lambda tex: tex.resize((2, 4), format='luminance'),
    lambda tex: setattr(tex, 'interpolation', 'linear'),
    lambda tex: setattr(tex, 'interpolation', ('linear', 'nearest')),
    lambda tex: tex.__setitem__(slice(None), np.zeros((2, 4, 1), np.float64)),
])
def test_rejected_mutations_leave_existing_texture_and_queue_unchanged(operation):
    tex = gloo.Texture2D(np.arange(8, dtype=np.uint32).reshape(2, 4), internalformat='r32ui')
    before_state, before_queue = state(tex), queue(tex)
    with pytest.raises((ValueError, RuntimeError)):
        operation(tex)
    assert state(tex) == before_state and queue(tex) == before_queue


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
def test_program_binds_texture_updates_same_object_and_relinks(internal, dtype, sampler, storage, words):
    tex = gloo.Texture2D(np.array(words, dtype=dtype).reshape(2, 4), internalformat=internal)
    prog = program(sampler)
    prog['u_words'] = tex
    commands = prog.glir.clear()
    assert commands[-1] == ('TEXTURE', prog.id, 'u_words', tex.id)
    assert not any(cmd[0] == 'UNIFORM' for cmd in commands)
    changed = np.array(words[::-1], dtype=dtype).reshape(2, 4)
    prog['u_words'] = changed
    assert prog['u_words'] is tex
    commands = prog.glir.clear()
    assert [cmd[0] for cmd in commands] == ['SIZE', 'DATA']
    assert commands[-1][3].tobytes() == changed.tobytes()
    prog.set_shaders(VERTEX, 'uniform %s u_words; void main(){}' % sampler)
    commands = prog.glir.clear()
    assert prog['u_words'] is tex and 'u_words' not in prog._pending_variables
    assert [cmd for cmd in commands if cmd[0] == 'TEXTURE'] == [('TEXTURE', prog.id, 'u_words', tex.id)]
    assert not any(cmd[0] in ('UNIFORM', 'SIZE', 'DATA') and cmd[1] == tex.id for cmd in commands)


@pytest.mark.parametrize('internal,dtype,sampler,storage,words', CASES)
def test_pending_assignment_replays_typed_texture(internal, dtype, sampler, storage, words):
    tex = gloo.Texture2D(np.array(words, dtype=dtype).reshape(2, 4), internalformat=internal)
    prog = gloo.Program()
    prog['u_words'] = tex
    assert prog._pending_variables['u_words'] is tex
    prog.set_shaders(VERTEX, 'uniform %s u_words; void main(){}' % sampler)
    commands = prog.glir.clear()
    assert prog['u_words'] is tex and 'u_words' not in prog._pending_variables
    assert commands[-1] == ('TEXTURE', prog.id, 'u_words', tex.id)
    assert not any(cmd[0] == 'UNIFORM' for cmd in commands)


@pytest.mark.parametrize('sampler,make_data', [
    ('usampler2D', lambda: gloo.Texture2D(np.zeros((2, 4), np.int32), internalformat='r32i')),
    ('isampler2D', lambda: gloo.Texture2D(np.zeros((2, 4), np.uint32), internalformat='r32ui')),
    ('usampler2D', lambda: gloo.Texture2D(np.zeros((2, 4), np.uint32))),
    ('usampler2D', lambda: gloo.Texture3D(np.zeros((2, 4, 2), np.uint32))),
    ('usampler2D', lambda: gloo.TextureCube(np.zeros((6, 2, 2, 1), np.uint32))),
    ('usampler2D', lambda: np.zeros((2, 4), np.uint32)),
    ('sampler2D', lambda: gloo.Texture2D(np.zeros((2, 4), np.uint32), internalformat='r32ui')),
    ('sampler3D', lambda: gloo.Texture2D(np.zeros((2, 4), np.int32), internalformat='r32i')),
])
def test_sampler_scalar_dimension_or_implicit_creation_rejected_atomically(sampler, make_data):
    prog, data = program(sampler), make_data()
    prog._pending_variables['u_words'] = 'retained pending sentinel'
    before_state, before_queue, previous_id = state(prog), queue(prog), GLObject._idcount
    with pytest.raises(ValueError):
        prog['u_words'] = data
    assert state(prog) == before_state and queue(prog) == before_queue
    assert GLObject._idcount == previous_id


def test_bad_existing_texture_array_update_preserves_program_pending_and_queue():
    prog = program('usampler2D')
    tex = gloo.Texture2D(np.zeros((2, 4), np.uint32), internalformat='r32ui')
    prog['u_words'] = tex
    prog._pending_variables['u_words'] = 'retained pending sentinel'
    before_program, before_texture, before_queue = state(prog), state(tex), queue(prog)
    with pytest.raises(ValueError):
        prog['u_words'] = np.zeros((2, 4), np.float32)
    assert state(prog) == before_program and state(tex) == before_texture and queue(prog) == before_queue


def test_failed_pending_replay_retains_pending_but_new_shader_request_is_queued():
    prog = gloo.Program()
    wrong = gloo.Texture2D(np.zeros((2, 4), np.float32))
    prog['u_words'] = wrong
    prog['later'] = 4.0
    with pytest.raises(ValueError):
        prog.set_shaders(VERTEX, 'uniform usampler2D u_words; void main(){}')
    assert prog._pending_variables['u_words'] is wrong and prog._pending_variables['later'] == 4.0
    commands = prog.glir.clear()
    assert any(cmd[0] == 'LINK' for cmd in commands)
    assert not any(cmd[0] in ('TEXTURE', 'UNIFORM') for cmd in commands)


@pytest.mark.parametrize('texture,shape', [(gloo.Texture1D, (4,)), (gloo.Texture3D, (2, 3, 4)),
                                          (gloo.TextureCube, (6, 2, 2, 1)), (gloo.TextureEmulated3D, (2, 3, 4))])
@pytest.mark.parametrize('internal', ['r32i', 'r32ui'])
def test_other_integer_dimensions_and_emulation_remain_rejected(texture, shape, internal):
    with pytest.raises(ValueError):
        texture(shape, internalformat=internal)


def test_float_and_untyped_integer_defaults_remain_unchanged():
    for dtype in (np.float32, np.int32, np.uint32, np.uint8):
        tex = gloo.Texture2D(np.zeros((2, 4), dtype), interpolation='linear')
        assert tex.format == 'luminance' and tex.internalformat is None
        assert tex.glsl_type == ('uniform', 'sampler2D') and tex.glsl_sample == 'texture2D'
        assert all(cmd[3:] == ('luminance', None) for cmd in tex.glir.clear() if cmd[0] == 'SIZE')
    prog = program('sampler2D')
    prog['u_words'] = np.ones((2, 4), np.float32)
    original = prog['u_words']
    prog['u_words'] = np.zeros((2, 4), np.float32)
    assert prog['u_words'] is original


def test_float_to_integer_resize_rejects_linear_without_changing_layout():
    tex = gloo.Texture2D(np.zeros((2, 4), np.float32), interpolation='linear')
    before_state, before_queue = state(tex), queue(tex)
    with pytest.raises(ValueError, match='nearest'):
        tex.resize((2, 4), internalformat='r32ui')
    assert state(tex) == before_state and queue(tex) == before_queue


def test_integer_to_float_resize_returns_to_legacy_format_and_data_rules():
    tex = gloo.Texture2D(np.zeros((2, 4), np.uint32), internalformat='r32ui')
    tex.glir.clear()
    tex.resize((3, 5), internalformat='r32f')
    assert tex.shape == (3, 5, 1) and tex.format == 'red' and tex.internalformat == 'r32f'
    assert tex.glsl_type == ('uniform', 'sampler2D') and tex.glsl_sample == 'texture2D'
    assert tex.glir.clear() == [('SIZE', tex.id, (3, 5, 1), 'red', 'r32f')]
    tex.interpolation = 'linear'
    values = np.full((3, 5), .25, np.float32)
    tex.set_data(values)
    assert tex.glir.clear()[-1][3].tobytes() == values.tobytes()


@pytest.mark.parametrize('dtype', [np.float32, np.uint32])
def test_float_sampler_rejects_array_update_after_texture_retagged_integer(dtype):
    prog = program('sampler2D')
    tex = gloo.Texture2D(np.zeros((2, 4), np.float32))
    prog['u_words'] = tex
    tex.resize((2, 4), internalformat='r32ui')
    prog._pending_variables['u_words'] = 'retained pending sentinel'
    before_program, before_texture, before_queue = state(prog), state(tex), queue(prog)
    with pytest.raises(ValueError, match='floating-point sampler'):
        prog['u_words'] = np.zeros((2, 4), dtype)
    assert state(prog) == before_program and state(tex) == before_texture and queue(prog) == before_queue
