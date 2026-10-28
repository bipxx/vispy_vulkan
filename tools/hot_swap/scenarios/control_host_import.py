# SPDX-License-Identifier: AGPL-3.0-only
"""Positive control: a host package importing PyOpenGL (as stock napari does) is recorded, not failed."""
exec(compile('import OpenGL.error', 'host_package/_control.py', 'exec'), {'__name__': 'host_package._control'})
