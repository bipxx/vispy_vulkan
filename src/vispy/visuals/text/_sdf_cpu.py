"""Source fallback for the pinned CPU signed-distance implementation.

Editable and wheel builds provide the Cython extension of the same name.
This fallback preserves the extension's in-place contract and 8SSEDT passes
for source imports before the first build; it is intentionally slower.
"""

import math

import numpy as np


def _distance(value):
    return np.float32(value.real * value.real + value.imag * value.imag)


def _propagate(grid):
    height, width = np.array(grid.shape) - 1

    def compare(y, x, candidate, current):
        candidate = np.complex64(candidate)
        distance = _distance(candidate)
        if distance < current:
            grid[y, x] = candidate
            return distance
        return current

    for y in range(1, height):
        for x in range(1, width):
            current = _distance(grid[y, x])
            current = compare(y, x, grid[y, x - 1] - 1, current)
            current = compare(y, x, grid[y - 1, x] - 1j, current)
            current = compare(y, x, grid[y - 1, x - 1] - 1 - 1j, current)
            compare(y, x, grid[y - 1, x + 1] + 1 - 1j, current)
        for x in range(width - 1, 0, -1):
            compare(y, x, grid[y, x + 1] + 1, _distance(grid[y, x]))
    for y in range(height - 1, 0, -1):
        for x in range(width - 1, 0, -1):
            current = _distance(grid[y, x])
            current = compare(y, x, grid[y, x + 1] + 1, current)
            current = compare(y, x, grid[y + 1, x] + 1j, current)
            current = compare(y, x, grid[y + 1, x - 1] - 1 + 1j, current)
            compare(y, x, grid[y + 1, x + 1] + 1 + 1j, current)
        for x in range(1, width):
            compare(y, x, grid[y, x - 1] - 1, _distance(grid[y, x]))


def _calc_distance_field(pixels, w, h, sp_f):
    """Replace the interior of a float32 image with its signed distance field."""
    if not isinstance(pixels, np.ndarray):
        raise TypeError("pixels must be a NumPy array")
    if pixels.dtype != np.float32:
        raise ValueError("Buffer dtype mismatch: expected float32")
    if pixels.ndim != 2:
        raise ValueError("pixels must have two dimensions")
    if w < 2 or h < 2 or pixels.shape[0] < h or pixels.shape[1] < w:
        raise ValueError("distance field dimensions must fit the input")
    if not pixels.flags.writeable:
        raise ValueError("pixels must be writable")
    sp_f = np.float32(sp_f)
    g0 = np.zeros((h, w), np.complex64)
    g1 = np.zeros((h, w), np.complex64)
    maximum = np.complex64(1e6 + 1e6j)
    g0[:, 1:-1][pixels[:h, 1:w - 1] > 0] = maximum
    g1[:, 1:-1][pixels[:h, 1:w - 1] < 1] = maximum
    for grid in (g0, g1):
        grid[:, 0] = grid[:, -1] = grid[0, :] = grid[-1, :] = maximum
        _propagate(grid)
    scale = np.float32(1.0 / (float(sp_f) * 2.0))
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            distance = np.float32(math.sqrt(_distance(g0[y, x])) - math.sqrt(_distance(g1[y, x])))
            if distance < 0:
                result = np.float32(distance + sp_f) * scale
            else:
                result = 0.5 + float(distance) * float(scale)
            pixels[y, x] = min(max(result, 0), 1)
    # The upstream caller relies on mutation and ignores the return value.
