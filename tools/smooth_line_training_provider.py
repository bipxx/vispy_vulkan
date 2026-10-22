"""Training-only original-GL observations; no model selection or fork rendering."""
from __future__ import annotations

from functools import lru_cache
import ctypes
import hashlib
import json
import math
from pathlib import Path
import sys
from types import MappingProxyType
import traceback

import numpy as np

try:
    from .smooth_line_mechanism import PIXEL_UNITS, SIZE, Probe, training_probes
    from .fixture_gloo import freeze
except ImportError:
    from smooth_line_mechanism import PIXEL_UNITS, SIZE, Probe, training_probes
    from fixture_gloo import freeze

VERTEX = 'attribute vec2 a_position; void main() { gl_Position=vec4(a_position,0.0,1.0); }'
FRAGMENT = 'void main() { gl_FragColor=vec4(1.0,1.0,1.0,1.0); }'
DISABLED = MappingProxyType(dict(blend=0x0BE2, depth_test=0x0B71, stencil_test=0x0B90,
                scissor_test=0x0C11, cull_face=0x0B44, dither=0x0BD0,
                framebuffer_srgb=0x8DB9, rasterizer_discard=0x8C89,
                sample_alpha_to_coverage=0x809E, sample_alpha_to_one=0x809F,
                sample_coverage=0x80A0, color_logic_op=0x0BF2,
                line_stipple=0x0B24, alpha_test=0x0BC0))
FORMATS = MappingProxyType(dict(rgba8=(np.dtype('uint8'), 8, 255, 0x8C17, 'unsigned_byte'),
                               rgba16=(np.dtype('<f4'), 16, 1, 0x8C17, 'float'),
                               rgba32f=(np.dtype('<f4'), 32, 1, 0x1406, 'float')))


def format_spec(target_format):
    if type(target_format) is not str or target_format not in FORMATS:
        raise ValueError('Only declared RGBA8/RGBA16/RGBA32F observation formats are allowed')
    return FORMATS[target_format]


def repeat_indices():
    """Predeclared stability controls from training only, after the full sweep."""
    return tuple(sorted({0, 7039, *range(0, 7040, 113)}))


@lru_cache(maxsize=1)
def selected_probes():
    return MappingProxyType({probe.identity: probe for probe in training_probes()})


def admit_probe(probe):
    if type(probe) is not Probe or selected_probes().get(probe.identity) != probe:
        raise ValueError('Only exact frozen training descriptors may reach the backend or sink')


@lru_cache(maxsize=1)
def selected_indices():
    return MappingProxyType({probe.identity: index for index, probe in enumerate(training_probes())})


def admit_row(probe, index):
    admit_probe(probe)
    if type(index) is not int or selected_indices()[probe.identity] != index:
        raise ValueError('Training row differs from the frozen descriptor order')


def validate_state(state, probe, baseline, *, target_format='rgba8'):
    _, bits, _, component, _ = format_spec(target_format)
    if state['error'] != 0:
        raise ValueError('OpenGL reported an error')
    if state['context_handle'] <= 0 or state['framebuffer'] <= 0 or not state['framebuffer_complete']:
        raise ValueError('A current context and complete offscreen framebuffer are required')
    if state['read_framebuffer'] != state['framebuffer']:
        raise ValueError('Read and draw framebuffer bindings differ')
    if state['framebuffer'] != baseline['owned_framebuffer'] or state['attachment_name'] != baseline['owned_texture']:
        raise ValueError('Bound target is not the owned Gloo framebuffer/texture')
    if (state['attachment_type'] != 0x1702 or state['attachment_bits'] != [bits] * 4 or
            state['attachment_component_type'] != component):
        raise ValueError('Owned texture attachment differs from the declared format')
    if state['profile_mask'] != 2 or state['context_flags'] & 1:
        raise ValueError('Non-forward-compatible desktop compatibility profile required')
    if state['read_buffer'] != 0x8CE0 or state['pack_state'] != [4, 0, 0, 0, 0, 0, 0]:
        raise ValueError('Owned color read buffer and canonical CPU pixel-pack state required')
    if state['samples'] != 0 or state['sample_buffers'] != 0 or state['channel_bits'] != [bits] * 4:
        raise ValueError('Single-sample declared target format required')
    if state['color_encoding'] != 0x2601 or state['viewport'] != [0, 0, *SIZE] or state['color_mask'] != [True] * 4:
        raise ValueError('Linear full-write target and exact viewport required')
    if state['hint'] != 0x1100 or state['line_smooth'] is not True:
        raise ValueError('Observed smooth-line state/hint differs from contract')
    if any(state[name] is not False for name in DISABLED):
        raise ValueError('An excluded raster operation is enabled')
    width = probe.width_units / PIXEL_UNITS
    low, high = state['width_range']
    granularity = state['width_granularity']
    if not all(math.isfinite(value) for value in (width, low, high, granularity, state['line_width'])):
        raise ValueError('Nonfinite line state')
    if not (0 <= low <= width <= high and width > 0) or state['line_width'] != width or granularity < 0:
        raise ValueError('Requested width is not admitted without clamping')
    if granularity and not math.isclose((width - low) / granularity, round((width - low) / granularity), abs_tol=1e-5):
        raise ValueError('Requested width is not on the observed implementation granularity')
    if state['subpixel_bits'] < 0:
        raise ValueError('Invalid precision observation')
    for name in ('context_handle', 'framebuffer', 'renderer', 'version', 'vendor', 'width_range',
                 'width_granularity', 'subpixel_bits', 'profile_mask', 'context_flags', 'owned_framebuffer', 'owned_texture'):
        if state[name] != baseline[name]:
            raise ValueError('Observation identity changed: ' + name)


def validate_frame(image, *, target_format='rgba8'):
    dtype, _, white, _, _ = format_spec(target_format)
    if image.dtype != dtype or image.shape != (SIZE[1], SIZE[0], 4):
        raise ValueError('Exact declared frame dtype/shape required')
    if not np.all(np.isfinite(image)) or np.any(image < 0) or np.any(image > white):
        raise ValueError('Finite normalized color/coverage observation required')
    rgb, alpha = image[..., :3], image[..., 3]
    if not np.all((rgb == 0) | (rgb == white)) or not np.all(rgb == rgb[..., :1]):
        raise ValueError('Constant-white blend-off protocol violated')
    generated = rgb[..., 0] == white
    if np.any(alpha[~generated] != 0):
        raise ValueError('Unwritten alpha differs from transparent clear')
    if np.count_nonzero(generated) < 20 or float(alpha.max()) <= 0:
        raise ValueError('Missing visible line observation')
    if any(np.any(part) for part in (image[:4], image[-4:], image[:, :4], image[:, -4:])):
        raise ValueError('Unexpected output outside the predeclared interior geometry')


def capture_one(backend, sink, probe, index):
    admit_row(probe, index)  # Before any backend query, readback or artifact access.
    _capture_admitted(backend, sink, probe, index)


def _capture_admitted(backend, sink, probe, index):
    backend.last_before = backend.last_after = None
    backend.last_commands = []
    backend.prepare(probe)
    backend.flush_commands()
    before = backend.observe()
    backend.last_before = before
    backend.last_commands = backend.peek_commands()
    validate_state(before, probe, backend.baseline, target_format=backend.target_format)
    image = backend.read_pixels()  # The only final read for this probe.
    after = backend.observe()
    backend.last_after = after
    # Preserve raw measurements before admission, including a failed final state/frame.
    commands = backend.take_commands()
    backend.last_commands = commands
    sink.record(index, probe, image, before, after, commands)
    validate_state(after, probe, backend.baseline, target_format=backend.target_format)
    validate_frame(image, target_format=backend.target_format)
    validate_commands(commands, probe, backend.program_id, backend.vertex_buffer_id)
    sink.accept(index)


def expected_vertex_upload(probe):
    # Unchanged upstream VertexBuffer._prepare_data makes this structured view.
    return freeze(probe.clip_positions().view(dtype=[('f0', np.float32, 2)]))


def validate_commands(commands, probe, program_id, vertex_buffer_id):
    draws = [(i, command) for i, command in enumerate(commands) if command[0] == 'DRAW']
    finishes = [i for i, command in enumerate(commands) if command[:2] == ['FUNC', 'glFinish']]
    clears = [i for i, command in enumerate(commands) if command[:2] == ['FUNC', 'glClear']]
    widths = [command for command in commands if command[:2] == ['FUNC', 'glLineWidth']]
    if len(draws) != 1 or draws[0][1] != ['DRAW', program_id, 'lines', [0, 2], 1]:
        raise ValueError('Exactly one original two-vertex line DRAW required')
    if len(finishes) != 1 or len(clears) != 1 or commands[clears[0]] != ['FUNC', 'glClear', 0x4000]:
        raise ValueError('One color clear and standard final-read finish required')
    if not clears[0] < draws[0][0] < finishes[0]:
        raise ValueError('Clear/DRAW/final-read order changed')
    if widths != [['FUNC', 'glLineWidth', probe.width_units / PIXEL_UNITS]]:
        raise ValueError('Actual line-width command differs from descriptor')
    funcs = [command for command in commands if command[0] == 'FUNC']
    expected_funcs = [['FUNC', 'glLineWidth', probe.width_units / PIXEL_UNITS],
                      ['FUNC', 'glClearColor', 0., 0., 0., 0.],
                      ['FUNC', 'glClear', 0x4000], ['FUNC', 'glFinish']]
    if funcs != expected_funcs:
        raise ValueError('Unexpected state operation in training command batch')
    uploads = [command[3] for command in commands if command[:2] == ['DATA', vertex_buffer_id]]
    expected = expected_vertex_upload(probe)
    if not uploads or uploads[-1] != expected:
        raise ValueError('Actual final vertex upload differs from descriptor')


class TrainingSink:
    """One sequential training-only array; partial output never claims completion."""
    def __init__(self, directory, count, row_indices=None, *, target_format='rgba8'):
        self.directory = Path(directory)
        self.dtype = format_spec(target_format)[0]
        self.count = count
        self.row_indices = tuple(range(count)) if row_indices is None else tuple(row_indices)
        if (type(count) is not int or count <= 0 or len(self.row_indices) != count or
                len(set(self.row_indices)) != count or
                any(type(index) is not int or not 0 <= index < 7040 for index in self.row_indices)):
            raise ValueError('Exact distinct training row selection required')
        self.raw_frames = self.accepted_frames = 0
        self.data = self.observations = self.commands = None

    def __enter__(self):
        try:
            self.data = (self.directory / 'training.rgba.npy').open('xb')
            np.lib.format.write_array_header_2_0(self.data, dict(descr=self.dtype.str, fortran_order=False,
                                                                shape=(self.count, SIZE[1], SIZE[0], 4)))
            self.observations = (self.directory / 'observations.jsonl').open('x', encoding='utf-8', newline='\n')
            self.commands = (self.directory / 'commands.jsonl').open('x', encoding='utf-8', newline='\n')
            return self
        except BaseException:
            self.close()
            raise

    def record(self, index, probe, image, before, after, commands):
        admit_row(probe, index)
        self._record_admitted(index, probe, image, before, after, commands)

    def _record_admitted(self, index, probe, image, before, after, commands):
        if self.raw_frames >= self.count or index != self.row_indices[self.raw_frames]:
            raise ValueError('Duplicate, reordered or unselected training row')
        if image.dtype != self.dtype or image.shape != (SIZE[1], SIZE[0], 4):
            np.save(self.directory / 'invalid-frame.npy', image, allow_pickle=False)
            raise ValueError('Invalid raw frame retained separately')
        body = np.ascontiguousarray(image).tobytes()
        self.data.write(body)
        self.observations.write(json.dumps(dict(index=index, identity=probe.identity, state_before=before,
                                               state_after=after, rgba_sha256=hashlib.sha256(body).hexdigest()), sort_keys=True) + '\n')
        self.commands.write(json.dumps(dict(index=index, identity=probe.identity, commands=commands), sort_keys=True) + '\n')
        self.raw_frames += 1

    def accept(self, index):
        if (self.accepted_frames >= self.count or index != self.row_indices[self.accepted_frames] or
                self.raw_frames != self.accepted_frames + 1):
            raise ValueError('Raw observation must precede admission exactly once')
        self.accepted_frames += 1

    def close(self):
        for stream in (self.data, self.observations, self.commands):
            if stream is not None and not stream.closed:
                stream.close()

    def __exit__(self, *args):
        self.close()


class WindowsGLTrainingBackend:
    """One persistent installed-upstream context; unchanged Gloo geometry/DRAW calls."""
    def __init__(self, expected_renderer, expected_version, *, target_format='rgba8'):
        self.expected_renderer, self.expected_version = expected_renderer, expected_version
        self.target_format = target_format
        self.pixel_dtype, _, _, _, self.read_type = format_spec(target_format)
        self.canvas = self.fbo = self.texture = self.program = self.vertices = None
        self.parser = self.original_parse = self.parse_hook = None
        self.active = False
        self.commands, self.shaders = [], {}
        self.direct_state_calls = []
        self.baseline = None
        self.last_before = self.last_after = None
        self.last_commands = []
        self.closed = self.parser_restored = False
        self.cleanup_error = None

    def __enter__(self):
        if sys.platform != 'win32':
            raise ValueError('This first observation provider is Windows desktop GL only')
        from vispy import app, gloo
        self.gloo = gloo
        try:
            self.canvas = app.Canvas(app='pyqt6', size=SIZE, show=True, decorate=False,
                                     config={'samples': 0, 'alpha_size': 8})
            self.canvas.app.native.setQuitOnLastWindowClosed(False)
            self.canvas._backend._vispy_warmup()
            self.canvas.set_current()
            self.parser = self.canvas.context.shared.parser
            if 'parse' in vars(self.parser):
                raise ValueError('Parser already has an instance override')
            self.original_parse = self.parser.parse

            def parse(batch):
                batch = list(batch)
                for command in batch:
                    self.commands.append(freeze(command))
                    if command[0] == 'DATA' and isinstance(command[3], str):
                        self.shaders[str(command[1])] = command[3]
                return self.original_parse(batch)

            self.parse_hook = parse
            self.parser.parse = parse
            self.texture = gloo.Texture2D(np.zeros((SIZE[1], SIZE[0], 4), self.pixel_dtype),
                                          format='rgba', internalformat=self.target_format, interpolation='nearest')
            self.fbo = gloo.FrameBuffer(color=self.texture)
            self.fbo.activate()
            self.active = True
            self.vertices = gloo.VertexBuffer(np.zeros((2, 2), np.float32))
            self.program = gloo.Program(VERTEX, FRAGMENT)
            self.program['a_position'] = self.vertices
            self.program_id, self.vertex_buffer_id = self.program.id, self.vertices.id
            gloo.set_viewport(0, 0, *SIZE)
            gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False,
                           cull_face=False, line_smooth=True, line_width=1)
            gloo.set_color_mask(True, True, True, True)
            self.canvas.context.flush_commands()
            # Desktop-only state enums are not all exported by VisPy's ES2 enum set.
            # Use its unchanged GL2 facade and record the direct state operations.
            for name, value in DISABLED.items():
                gloo.gl.glDisable(value)
                self.direct_state_calls.append(['glDisable', name, value])
            gloo.gl.glHint(0x0C52, 0x1100)
            self.direct_state_calls.append(['glHint', 0x0C52, 0x1100])
            self.native_gl = ctypes.WinDLL('opengl32.dll')
            self.native_gl.glGetFloatv.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_float)]
            self.native_gl.glGetFloatv.restype = None
            self.native_gl.glGetIntegerv.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]
            self.native_gl.glGetIntegerv.restype = None
            self.native_gl.wglGetCurrentContext.argtypes = []
            self.native_gl.wglGetCurrentContext.restype = ctypes.c_void_p
            self.owned_framebuffer = int(self.parser.get_object(self.fbo.id).handle)
            self.owned_texture = int(self.parser.get_object(self.texture.id).handle)
            self.baseline = self.observe()
            self.last_commands = self.peek_commands()
            if self.baseline['renderer'] != self.expected_renderer or self.baseline['version'] != self.expected_version:
                raise ValueError('Actual GL implementation differs from the declared oracle')
            validate_state(self.baseline, training_probes()[0], self.baseline, target_format=self.target_format)
            self.setup_commands = self.take_commands()
            return self
        except BaseException:
            try:
                self.close()
            except BaseException:
                self.cleanup_error = traceback.format_exc()
            raise

    def _integers(self, enum, count=1):
        values = (ctypes.c_int * count)()
        self.native_gl.glGetIntegerv(enum, values)
        return list(values) if count > 1 else int(values[0])

    def _floats(self, enum, count=1):
        values = (ctypes.c_float * count)()
        self.native_gl.glGetFloatv(enum, values)
        return list(values) if count > 1 else float(values[0])

    def observe(self):
        gl = self.gloo.gl
        state = dict(context_handle=int(self.native_gl.wglGetCurrentContext() or 0),
                     framebuffer=self._integers(0x8CA6),
                     read_framebuffer=self._integers(0x8CAA),
                     framebuffer_complete=gl.glCheckFramebufferStatus(0x8D40) == 0x8CD5,
                     channel_bits=[self._integers(enum) for enum in (0x0D52, 0x0D53, 0x0D54, 0x0D55)],
                     color_encoding=int(gl.glGetFramebufferAttachmentParameter(0x8D40, 0x8CE0, 0x8210)),
                     owned_framebuffer=self.owned_framebuffer, owned_texture=self.owned_texture,
                     attachment_type=int(gl.glGetFramebufferAttachmentParameter(0x8D40, 0x8CE0, 0x8CD0)),
                     attachment_name=int(gl.glGetFramebufferAttachmentParameter(0x8D40, 0x8CE0, 0x8CD1)),
                     attachment_component_type=int(gl.glGetFramebufferAttachmentParameter(0x8D40, 0x8CE0, 0x8211)),
                     attachment_bits=[int(gl.glGetFramebufferAttachmentParameter(0x8D40, 0x8CE0, enum))
                                      for enum in (0x8212, 0x8213, 0x8214, 0x8215)],
                     profile_mask=self._integers(0x9126), context_flags=self._integers(0x821E),
                     read_buffer=self._integers(0x0C02),
                     pack_state=[self._integers(enum) for enum in
                                 (0x0D05, 0x0D02, 0x0D03, 0x0D04, 0x0D00, 0x0D01, 0x88ED)],
                     samples=self._integers(0x80A9), sample_buffers=self._integers(0x80A8),
                     viewport=self._integers(0x0BA2, 4), color_mask=[bool(v) for v in self._integers(0x0C23, 4)],
                     line_smooth=bool(gl.glIsEnabled(0x0B20)), hint=self._integers(0x0C52),
                     line_width=self._floats(0x0B21), width_range=self._floats(0x0B22, 2),
                     width_granularity=self._floats(0x0B23), subpixel_bits=self._integers(0x0D50),
                     renderer=str(gl.glGetParameter(0x1F01)), version=str(gl.glGetParameter(0x1F02)),
                     vendor=str(gl.glGetParameter(0x1F00)))
        state.update({name: bool(gl.glIsEnabled(enum)) for name, enum in DISABLED.items()})
        state['error'] = int(gl.glGetError())
        return state

    def prepare(self, probe):
        admit_probe(probe)
        self._prepare_admitted(probe)

    def _prepare_admitted(self, probe):
        self.vertices.set_data(probe.clip_positions())
        self.gloo.set_line_width(probe.width_units / PIXEL_UNITS)
        self.gloo.set_clear_color((0, 0, 0, 0))
        self.gloo.clear(color=True, depth=False, stencil=False)
        self.program.draw('lines')

    def flush_commands(self):
        self.canvas.context.flush_commands()  # GLIR dispatch only, no extra GPU finish/read.

    def read_pixels(self):
        # Standard read_pixels performs its own final glFinish; no extra wait is inserted.
        return self.gloo.read_pixels((0, 0, *SIZE), alpha=True, out_type=self.read_type).copy()

    def take_commands(self):
        commands, self.commands = self.commands, []
        return commands

    def peek_commands(self):
        return list(self.commands)

    def close(self):
        try:
            if self.canvas is not None:
                if self.active:
                    self.fbo.deactivate()
                    self.active = False
                for resource in (self.program, self.vertices, self.fbo, self.texture):
                    if resource is not None:
                        resource.delete()
                self.canvas.context.flush_commands()
        finally:
            try:
                if self.parser is not None and self.original_parse is not None:
                    if self.parse_hook is not None:
                        del self.parser.parse
                    self.parser_restored = 'parse' not in vars(self.parser) and self.parser.parse == self.original_parse
            finally:
                if self.canvas is not None:
                    self.canvas.close()
                self.closed = True

    def __exit__(self, *args):
        self.close()
