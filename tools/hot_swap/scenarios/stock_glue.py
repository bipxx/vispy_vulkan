# SPDX-License-Identifier: AGPL-3.0-only
"""Stock Glue baseline for the hot-swap audit: the five public workflows of the Glue fixture, each shown and closed."""
from tools.fixture_glue_extensions import CASES, assert_landmarks, render

for name in CASES:
    image, commands, shaders, parameters = render(name)
    assert commands and shaders, name
    assert_landmarks(name, image)
