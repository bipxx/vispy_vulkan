# -*- coding: utf-8 -*-
"""GLIR parser that forwards filtered commands to the Dawn extension."""

import operator

import numpy as np

from .glir import BaseGlirParser


def _freeze(value, arrays):
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        return {
            "__bytes__": array.tobytes(),
            "shape": [int(dim) for dim in array.shape],
            "dtype": array.dtype.str,
        }
    if isinstance(value, np.generic):
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.integer):
            return int(value)
        return value.item()
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [_freeze(item, arrays) for item in value]
    if value is None:
        return None
    if hasattr(value, "__int__") and type(value).__name__ == "Enum":
        return int(value)
    return value


def _freeze_owned(value, arrays, capture, stats):
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        # Structured and void arrays (vispy's vertex buffers) decode as raw bytes on either path.
        mapped = ((array.dtype.kind in "iu" and array.dtype.itemsize in (1, 2, 4)) or
                  (array.dtype.kind == "f" and array.dtype.itemsize in (2, 4, 8)) or
                  array.dtype.kind in "bV")
        if mapped:
            try:
                snapshot = capture(memoryview(array))
            except (BufferError, TypeError, ValueError):
                stats["fallback_exports"] += 1
            else:
                stats["captures"] += 1
                stats["bytes"] += array.nbytes
                return {"__owned_blob__": snapshot,
                        "shape": [int(dim) for dim in array.shape], "dtype": array.dtype.str}
        else:
            stats["fallback_dtypes"] += 1
        return {
            "__bytes__": array.tobytes(),
            "shape": [int(dim) for dim in array.shape],
            "dtype": array.dtype.str,
        }
    if isinstance(value, np.generic):
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.integer):
            return int(value)
        return value.item()
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [_freeze_owned(item, arrays, capture, stats) for item in value]
    if value is None:
        return None
    if hasattr(value, "__int__") and type(value).__name__ == "Enum":
        return int(value)
    return value


def get_framebuffer_configuration():
    """Describe the actual active target, preserving unknown native precision."""
    from vispy.gloo.context import get_current_canvas
    canvas = get_current_canvas()
    backend = getattr(canvas, '_backend', None) if canvas is not None else None
    canvas_id = int(getattr(backend, '_dawn_canvas_id', 0) or 0)
    if not canvas_id or getattr(canvas, '_closed', True):
        raise RuntimeError('framebuffer configuration requires a current Dawn canvas')
    from vispy import _dawn
    query = getattr(_dawn, 'framebuffer_config', None)
    if query is None:
        raise RuntimeError('framebuffer configuration requires a matching native Dawn build')
    canvas.context.flush_commands()
    return dict(query(canvas_id))


# Logical native state, before pipeline lowering. Keep the selector boundary
# explicit so unsupported queries cannot consume preceding GLIR or start a device.
_STATE_QUERY_PARAMETERS = frozenset((
    0xbe2, 0x8005, 0x80c9, 0x80c8, 0x80cb, 0x80ca,
    0x8009, 0x883d, 0xb71, 0xb72, 0xb74, 0xb70,
    0xb73, 0xb90, 0xb91, 0xb92, 0xb93, 0xb94,
    0xb95, 0xb96, 0xb97, 0xb98, 0x8800, 0x8801,
    0x8802, 0x8803, 0x8ca3, 0x8ca4, 0x8ca5, 0xb44,
    0xb45, 0xb46, 0xc22, 0xc23, 0xc11, 0xc10,
    0xb21, 0xb20, 0x8037, 0x8038, 0x2a00, 0x809d,
    0x809e, 0x80a0, 0x80aa, 0x80ab,
))
_DEVICE_QUERY_PARAMETERS = frozenset((
    7936, 7937, 7938, 7939, 35724, 3379, 32883, 34024,
    34930, 35660, 35376, 34921, 35071, 35661, 35379,
))


def get_gl_parameter(pname):
    """Answer an admitted GL-shaped query from actual Dawn capabilities."""
    from vispy import _dawn
    from vispy.gloo.context import get_current_canvas

    if isinstance(pname, (bool, np.bool_)):
        raise TypeError('glGetParameter requires an integer query enum')
    try:
        code = operator.index(pname)
    except TypeError:
        raise TypeError('glGetParameter requires an integer query enum') from None
    if code in _STATE_QUERY_PARAMETERS:
        canvas = get_current_canvas()
        backend = getattr(canvas, '_backend', None)
        canvas_id = int(getattr(backend, '_dawn_canvas_id', 0) or 0)
        if not canvas_id or getattr(canvas, '_closed', True):
            raise RuntimeError('state query requires a current Dawn canvas')
        query = getattr(_dawn, 'state_parameter', None)
        if getattr(_dawn, 'state_query_contract_version', None) != 1 or not callable(query):
            raise RuntimeError('state query requires a matching native state-query build')
        canvas.context.flush_commands()
        return query(canvas_id, code)
    if code == 2978:  # GL_VIEWPORT
        canvas = get_current_canvas()
        backend = getattr(canvas, '_backend', None)
        canvas_id = int(getattr(backend, '_dawn_canvas_id', 0) or 0)
        if not canvas_id or getattr(canvas, '_closed', True):
            raise RuntimeError("viewport query requires a current Dawn canvas")
        canvas.context.flush_commands()
        return tuple(_dawn.viewport(canvas_id))
    if code in (32936, 32937, 3123, 3122):  # SAMPLE_BUFFERS, SAMPLES, STEREO, DOUBLEBUFFER
        configuration = get_framebuffer_configuration()
        if code == 32936:
            return int(configuration['sample_count'] > 1)
        field = {32937: 'samples', 3123: 'stereo', 3122: 'double_buffer'}[code]
        return configuration[field]
    if code not in _DEVICE_QUERY_PARAMETERS:
        raise RuntimeError("unsupported GL query %s" % pname)
    info = _dawn.device_info()
    if not info.get('ok', True):
        raise RuntimeError('Dawn capability query failed: ' + str(info.get('error', 'device unavailable')))
    limit = int(info["max_texture_dimension_2d"])
    device = info.get("device") or "Dawn"
    if isinstance(device, bytes):
        device = device.decode("utf-8", "replace")
    backend = info.get("backend") or "Dawn"
    # Hosts compare these with Python str (`'texture_float' in extensions`).
    # These are compatibility-profile labels for GL-shaped host probes, not
    # evidence of an OpenGL context or arbitrary OpenGL operation support.
    # Hosts that see texture_float upload linear-filtered float32 textures, which
    # need the Float32Filterable device feature; without it they use their fallback.
    texture_float = "GL_ARB_texture_float " if info.get("float32_filterable") else ""
    strings = {
        7936: "Dawn",  # GL_VENDOR
        7937: str(device),  # GL_RENDERER
        7938: "4.5.0 Dawn " + backend,  # GL_VERSION
        7939: texture_float + "GL_ARB_texture_non_power_of_two",  # GL_EXTENSIONS
        35724: "4.50 Dawn " + backend + " GLSL",  # GL_SHADING_LANGUAGE_VERSION
    }
    if code in strings:
        return strings[code]
    budgets = {
        3379: limit,  # GL_MAX_TEXTURE_SIZE
        32883: int(info["max_texture_dimension_3d"]),
        34024: limit,  # GL_MAX_RENDERBUFFER_SIZE
        # Dawn grants these limits per shader stage, for both vertex and fragment.
        34930: min(int(info["max_sampled_textures_per_shader_stage"]), int(info["max_samplers_per_shader_stage"])),  # GL_MAX_TEXTURE_IMAGE_UNITS
        35660: min(int(info["max_sampled_textures_per_shader_stage"]), int(info["max_samplers_per_shader_stage"])),  # GL_MAX_VERTEX_TEXTURE_IMAGE_UNITS
        35376: int(info["max_uniform_buffer_binding_size"]),  # GL_MAX_UNIFORM_BLOCK_SIZE, bytes
        34921: int(info["max_vertex_attributes"]),
    }
    # These domains are not a per-stage sampler count or a byte binding size.
    # Require a separately reported backend/renderer grant; do not invent one.
    for query, field in (
        (35071, "max_texture_array_layers"),  # GL_MAX_ARRAY_TEXTURE_LAYERS
        (35661, "max_combined_texture_image_units"),  # GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS
        (35379, "max_combined_fragment_uniform_components"),  # components, not bytes
    ):
        if field in info:
            budgets[query] = int(info[field])
    if code in budgets:
        return budgets[code]
    raise RuntimeError("unsupported GL query %s" % pname)


get_gl_parameter._dawn_query = True


def install_gl_queries():
    """Keep the admitted compatibility query route across backend aliases."""
    import vispy.gloo.gl as glmod
    glmod.glGetParameter = get_gl_parameter
    glmod._dawn_queries = True


def pack_commands(commands, *, native_capture=None, capture_stats=None):
    """Snapshot payloads during packing; default output retains the bytes protocol."""
    arrays = []
    packed = []
    if native_capture is None:
        freeze = lambda item: _freeze(item, arrays)
    else:
        if capture_stats is None:
            raise ValueError("owned packing requires capture counters")
        freeze = lambda item: _freeze_owned(item, arrays, native_capture, capture_stats)
    for command in commands:
        packed.append(tuple(freeze(item) for item in command))
    return packed, arrays


class DawnGlirParser(BaseGlirParser):
    """Execute filtered GLIR on the shared Dawn device."""

    def __init__(self):
        super().__init__()
        self.canvas_id = 0
        self.capabilities = dict(gl_version="Dawn Vulkan", max_texture_size=None)

    @property
    def shader_compatibility(self):
        return "desktop"

    def is_remote(self):
        return False

    def parse(self, commands):
        from vispy import _dawn

        if getattr(_dawn, 'submission_contract_version', 0) < 1:
            original_commands = commands
            def guarded_commands():
                for command in original_commands:
                    if len(command) > 1 and command[0] == 'FUNC' and command[1] == 'glFlush':
                        raise RuntimeError('glFlush requires a matching native submission-contract build; '
                                           'the older native module does not submit this operation')
                    yield command
            commands = guarded_commands()

        if hasattr(_dawn, "_capture_upload") and hasattr(_dawn, "_execute_owned"):
            stats = dict(captures=0, bytes=0, fallback_dtypes=0, fallback_exports=0)
            packed, arrays = pack_commands(commands, native_capture=_dawn._capture_upload,
                                           capture_stats=stats)
            _dawn._execute_owned(int(self.canvas_id), packed, arrays, stats)
        else:
            packed, arrays = pack_commands(commands)
            _dawn.execute(int(self.canvas_id), packed, arrays)
        info = _dawn.device_info()
        if info.get("max_texture_dimension_2d"):
            self.capabilities["max_texture_size"] = int(info["max_texture_dimension_2d"])
        if info.get("backend"):
            self.capabilities["gl_version"] = "Dawn " + info["backend"]


def read_pixels_dawn(viewport, alpha, mode, out_type="unsigned_byte", copy=True):
    from .. import gloo
    from vispy import _dawn

    if mode not in ("color", "depth", "stencil"):
        raise ValueError("mode must be color, depth or stencil")
    canvas = gloo.context.get_current_canvas()
    if canvas is None or canvas._backend is None:
        raise RuntimeError("read_pixels requires a current canvas")
    if out_type not in ("unsigned_byte", "float", np.uint8, np.float32):
        raise ValueError("out_type must be unsigned_byte or float")
    use_current_viewport = viewport is None
    if use_current_viewport:
        # Apply queued viewport updates before resolving the default region.
        canvas.context.finish()
        viewport = _dawn.viewport(int(canvas._backend._dawn_canvas_id))
    viewport = np.asarray(viewport, dtype=int)
    if viewport.ndim != 1 or viewport.size != 4:
        raise ValueError("viewport should be a 1D four-element array")
    if not use_current_viewport:
        # Explicit viewport coercion/shape errors must precede submission.
        canvas.context.finish()
    x, y, width, height = viewport
    canvas_id = int(getattr(canvas._backend, "_dawn_canvas_id", 0) or 0)
    image = _dawn.read_pixels(canvas_id, x, y, width, height, bool(alpha),
                              out_type in ("float", np.float32), mode)
    # The native array owns a fresh buffer; copy=False returns it as is (B19).
    return np.array(image, copy=True) if copy else image
