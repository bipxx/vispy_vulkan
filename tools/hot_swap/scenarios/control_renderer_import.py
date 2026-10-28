# SPDX-License-Identifier: AGPL-3.0-only
"""Negative control: an OpenGL import from a renderer-attributed frame (module vispy.*) must FAIL renderer_gl.

Attribution reads each frame's module name, so this frame stands for renderer code that imports GL.
"""
exec(compile('import OpenGL.GL', 'vispy/_hot_swap_control.py', 'exec'), {'__name__': 'vispy._hot_swap_control'})
