# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Original proxy interface notices retained; see LICENSE-BSD.
# Dawn implementation SPDX-License-Identifier: AGPL-3.0-only

"""OpenGL-free compatibility functions for the Dawn GLIR renderer."""

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


class DawnProxy(BaseGLProxy):
    def __call__(self, funcname, returns, *args):
        if funcname == 'glGetParameter':
            from ..dawn_parser import get_gl_parameter
            return get_gl_parameter(*args)
        if funcname == 'glGetError':
            # Dawn failures are synchronous Python exceptions; this facade has
            # no deferred GL error queue. Never use this to discard an error.
            return int(GL_NO_ERROR)
        raise DawnCompatibilityError(
            '%s is an immediate OpenGL operation and is not supported by the '
            'Dawn renderer. Use gloo objects/GLIR commands instead.' % funcname)


_proxy = DawnProxy()
_copy_gl_functions(_proxy, globals())
