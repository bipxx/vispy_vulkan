# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""
Object oriented rendering interface executed by Dawn.

Program, texture, framebuffer and buffer objects express rendering through an
ordered GLIR command stream. Dawn executes the supported commands using Vulkan
or Metal. GL-named resources and constants preserve familiar VisPy call sites.

The fork's compatibility documentation defines supported shader forms, formats,
state operations and platform profiles. Exported classes have distinct scopes;
their availability does not establish support for every upstream method/value.

GLObject supplies logical resource identity and queued deletion. Program objects
bind textures as uniforms and vertex buffers as attributes, then submit draws
through the active canvas/context.

Example::

    # Init
    program = gloo.Program(vertex_source, fragment_source)
    program['a_position'] = gloo.VertexBuffer(my_positions_array)
    program['s_texture'] = gloo.Texture2D(my_image)
    ...

    # Draw event handler
    program['u_color'] = 0.0, 1.0, 0.0
    program.draw(gl.GL_TRIANGLES)

"""

from __future__ import division

from . import gl  # noqa
from .wrappers import *  # noqa
from .context import (GLContext, get_default_config,  # noqa
                      get_current_canvas)  # noqa
from .globject import GLObject  # noqa
from .buffer import VertexBuffer, IndexBuffer  # noqa
from .texture import Texture1D, Texture2D, TextureAtlas, Texture3D, TextureCube, TextureEmulated3D  # noqa
from .program import Program  # noqa
from .framebuffer import FrameBuffer, RenderBuffer  # noqa
from . import util  # noqa
