# SPDX-License-Identifier: AGPL-3.0-only
"""The napari layer-control comparison (W5: B03, H01, V04), with decisions D13 and D14.

The fixture (tools/fixture_napari_layer_controls.py, bound to its references by hash) fixed every case as exact
before capture. Two user decisions (2026-10-29) followed:

- D13: the glFinish counts of the change and the capture are recorded, not compared. napari requests the same
  finishes in both renderers, but OpenGL's QOpenGLWidget.grabFramebuffer synchronizes inside Qt, while the Dawn
  readback logs the same synchronization as a glFinish. The parity test therefore does not compare them.
- D14: volume_iso differs by a few levels where floating-point differences move the iso hit point or the shading
  normal. Pixels whose reference 3x3 neighbourhood is uniform stay exact; at most 0.1% of the frame may differ, each
  by at most 4 levels.

Every other case stays exact.
"""
from __future__ import annotations

import numpy as np

try:
    from .smooth_line_parity import reference_edges
except ImportError:
    from smooth_line_parity import reference_edges

COMPARED_PARAMETERS = ("layer_types", "layer_names", "ndisplay")  # decision D13: finish_commands is evidence only
SHADING = frozenset({"volume_iso"})  # decision D14
MAX_SHADING_FRACTION = .001
MAX_SHADING_LEVELS = 4


def layer_control_difference(name, image, reference):
    """Return None if ``image`` matches ``reference`` under the case's comparison, else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return "shape or dtype differs"
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    differing = np.any(difference, axis=2)
    if not differing.any():
        return None
    if name not in SHADING:
        return "%d pixels differ, by up to %d" % (int(differing.sum()), int(difference.max()))
    uniform = differing & ~reference_edges(reference)
    if uniform.any():
        return "%d uniform pixels differ" % int(uniform.sum())
    if difference.max() > MAX_SHADING_LEVELS:
        return "shading difference %d exceeds %d" % (int(difference.max()), MAX_SHADING_LEVELS)
    if differing.sum() > MAX_SHADING_FRACTION * differing.size:
        return "%d shading pixels differ" % int(differing.sum())
    return None
