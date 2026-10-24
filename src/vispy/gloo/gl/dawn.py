# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Original proxy interface notices retained; see LICENSE-BSD.
# Dawn implementation SPDX-License-Identifier: AGPL-3.0-only

"""OpenGL-free compatibility functions for the Dawn GLIR renderer."""

import operator

from . import BaseGLProxy, _copy_gl_functions
from ._constants import *  # noqa

# Additional enum names used by admitted desktop-GL-shaped host queries.
# Defining an enum does not advertise arbitrary immediate GL functionality.
_QUERY_ENUMS = {
    'GL_DOUBLEBUFFER': 3122,
    'GL_STEREO': 3123,
    'GL_MAX_3D_TEXTURE_SIZE': 32883,
    'GL_MAX_ARRAY_TEXTURE_LAYERS': 35071,
    'GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS': 35661,
    'GL_MAX_RENDERBUFFER_SIZE': 34024,
    'GL_MAX_UNIFORM_BLOCK_SIZE': 35376,
    'GL_MAX_COMBINED_FRAGMENT_UNIFORM_COMPONENTS': 35379,
    'GL_GEOMETRY_SHADER': 36313,
}
for _name, _value in _QUERY_ENUMS.items():
    globals()[_name] = Enum(_name, _value)


class DawnCompatibilityError(RuntimeError):
    """An immediate GL operation has no supported Dawn compatibility route."""


# These operations already have validated native GLIR implementations. Object
# IDs, shader compilation, bindings and raw draw calls are deliberately absent.
_STATE_COMMANDS = frozenset((
    'glViewport', 'glScissor', 'glClearColor', 'glClearDepth', 'glClearStencil',
    'glClear', 'glEnable', 'glDisable', 'glColorMask', 'glDepthMask',
    'glDepthRange', 'glDepthFunc', 'glFrontFace', 'glCullFace', 'glLineWidth',
    'glPolygonOffset', 'glBlendColor', 'glBlendFunc', 'glBlendFuncSeparate',
    'glBlendEquation', 'glBlendEquationSeparate', 'glStencilFunc',
    'glStencilFuncSeparate', 'glStencilMask', 'glStencilMaskSeparate',
    'glStencilOp', 'glStencilOpSeparate', 'glSampleCoverage', 'glFinish', 'glFlush',
))


class DawnProxy(BaseGLProxy):
    def __call__(self, funcname, returns, *args):
        if funcname == 'glGetParameter':
            from ..dawn_parser import get_gl_parameter
            return get_gl_parameter(*args)
        if funcname == 'glGetError':
            # Dawn failures are synchronous Python exceptions; this facade has
            # no deferred GL error queue. Never use this to discard an error.
            return int(GL_NO_ERROR)
        if funcname in _STATE_COMMANDS:
            from ..context import get_current_canvas
            canvas = get_current_canvas()
            backend = getattr(canvas, '_backend', None)
            if not getattr(backend, '_dawn_canvas_id', 0) or canvas._closed:
                raise DawnCompatibilityError('%s requires a current Dawn canvas' % funcname)
            if funcname == 'glClear':
                mask = operator.index(args[0])
                if mask < 0 or mask & ~0x4500:
                    raise DawnCompatibilityError('glClear has unsupported buffer mask %s' % mask)
            context = canvas.context
            context.glir.command('FUNC', funcname, *args)
            # Flush preceding gloo commands too, keeping raw state changes in
            # their original order with queued draws and framebuffer bindings.
            # Native glFinish waits; glFlush submits without a completion wait
            # and reports bounded-capacity backpressure rather than deferring
            # silently. Neither operation requests presentation.
            context.flush_commands()
            if funcname == 'glViewport':
                context._last_viewport = tuple(args)
            return
        raise DawnCompatibilityError(
            '%s is an immediate OpenGL operation and is not supported by the '
            'Dawn renderer. Use gloo objects/GLIR commands instead.' % funcname)


_proxy = DawnProxy()
_copy_gl_functions(_proxy, globals())
