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
        mapped = ((array.dtype.kind in "iu" and array.dtype.itemsize in (1, 2, 4)) or
                  (array.dtype.kind == "f" and array.dtype.itemsize in (2, 4, 8)) or
                  array.dtype.kind == "b")
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
    if code == 2978:  # GL_VIEWPORT
        canvas = get_current_canvas()
        backend = getattr(canvas, '_backend', None)
        canvas_id = int(getattr(backend, '_dawn_canvas_id', 0) or 0)
        if not canvas_id or getattr(canvas, '_closed', True):
            raise RuntimeError("viewport query requires a current Dawn canvas")
        canvas.context.flush_commands()
        return tuple(_dawn.viewport(canvas_id))
    if code in (32937, 3123, 3122):  # SAMPLES, STEREO, DOUBLEBUFFER
        configuration = get_framebuffer_configuration()
        field = {32937: 'samples', 3123: 'stereo', 3122: 'double_buffer'}[code]
        return configuration[field]
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
    strings = {
        7936: "Dawn",  # GL_VENDOR
        7937: str(device),  # GL_RENDERER
        7938: "4.5.0 Dawn " + backend,  # GL_VERSION
        7939: "GL_ARB_texture_float GL_ARB_texture_non_power_of_two",  # GL_EXTENSIONS
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


def read_pixels_dawn(viewport, alpha, mode, out_type="unsigned_byte"):
    from .. import gloo
    from vispy import _dawn

    if mode not in ("color", "depth", "stencil"):
        raise ValueError("mode must be color, depth or stencil")
    canvas = gloo.context.get_current_canvas()
    if canvas is None or canvas._backend is None:
        raise RuntimeError("read_pixels requires a current canvas")
    if out_type not in ("unsigned_byte", "float", np.uint8, np.float32):
        raise ValueError("out_type must be unsigned_byte or float")
    canvas.context.finish()
    if viewport is None:
        viewport = _dawn.viewport(int(canvas._backend._dawn_canvas_id))
    viewport = np.asarray(viewport, dtype=int)
    if viewport.ndim != 1 or viewport.size != 4:
        raise ValueError("viewport should be a 1D four-element array")
    x, y, width, height = viewport
    canvas_id = int(getattr(canvas._backend, "_dawn_canvas_id", 0) or 0)
    image = _dawn.read_pixels(canvas_id, x, y, width, height, bool(alpha),
                              out_type in ("float", np.float32), mode)
    return np.array(image, copy=True)
