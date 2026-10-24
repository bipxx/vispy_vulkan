# SPDX-License-Identifier: AGPL-3.0-only
"""Third-party font managers retain the established array-kernel contract."""

import numpy as np

from vispy.visuals.text.text import _font_kernel_texture


def test_custom_font_without_private_helper_reuses_texture_and_tracks_edits():
    # Slots also prove that the renderer does not inject state into host fonts.
    class HostFont:
        __slots__ = ('_kernel',)

    font = HostFont()
    font._kernel = np.arange(16, dtype=np.float32).reshape(4, 4)
    original = font._kernel.copy()
    cache = {}
    texture = _font_kernel_texture(font, cache)
    assert _font_kernel_texture(font, cache) is texture
    assert texture.shape[:2] == (4, 4)
    np.testing.assert_array_equal(cache['data'], original)
    font._kernel[1, 2] = -7
    # The saved snapshot is independent; the texture object remains resident.
    np.testing.assert_array_equal(cache['data'], original)
    assert _font_kernel_texture(font, cache) is texture
    np.testing.assert_array_equal(cache['data'], font._kernel)
    font._kernel = np.zeros((8, 8), np.float32)
    assert _font_kernel_texture(font, cache) is texture
    assert texture.shape[:2] == (8, 8)


def test_font_specific_cache_helper_remains_authoritative():
    sentinel = object()

    class Font:
        def _get_kernel_texture(self):
            return sentinel

    cache = {}
    assert _font_kernel_texture(Font(), cache) is sentinel
    assert cache == {}
