# SPDX-License-Identifier: AGPL-3.0-only
"""Stock napari baseline for the hot-swap audit: image and labels layers, 2D and 3D renders, close."""
import numpy as np
import napari

viewer = napari.Viewer()
viewer.add_image(np.linspace(0, 1, 32 * 64 * 64, dtype='float32').reshape(32, 64, 64), name='volume')
viewer.add_labels((np.arange(32 * 64 * 64, dtype='uint32').reshape(32, 64, 64) % 7).astype('uint8'), name='labels')
for ndisplay in (2, 3):
    viewer.dims.ndisplay = ndisplay
    image = viewer.screenshot(canvas_only=True, flash=False)
    assert image.size and image[..., :3].max() > 0, ndisplay
viewer.close()
