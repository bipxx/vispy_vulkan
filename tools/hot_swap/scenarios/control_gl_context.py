# SPDX-License-Identifier: AGPL-3.0-only
"""Negative control: creating and binding a GL context anywhere in the process must FAIL no_gl_context_or_draw.

qtpy selects whichever Qt binding the environment holds (PyQt6 or PySide6)."""
from qtpy.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext

application = QGuiApplication(['control'])
surface = QOffscreenSurface()
surface.create()
context = QOpenGLContext()
assert context.create(), 'no GL context could be created'
assert context.makeCurrent(surface), 'the GL context could not be made current'
context.doneCurrent()
