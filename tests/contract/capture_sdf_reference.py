"""Regenerate CPU reference data with independently installed upstream VisPy.

Run with the upstream environment's Python using ``-I`` from outside the repo:
    python -I /path/to/capture_sdf_reference.py /path/to/tests/contract/data
"""

import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys

import numpy as np
import vispy
from vispy.util.fonts import _load_glyph
from vispy.visuals.text import _sdf_cpu


def capture(destination):
    assert vispy.__version__ == "0.17.0", vispy.__version__
    assert Path(vispy.__file__).is_relative_to(Path(sys.prefix))
    destination.mkdir(parents=True, exist_ok=True)
    rectangle = np.zeros((13, 17), np.float32)
    rectangle[4:9, 5:12] = 1
    antialias = rectangle.copy()
    antialias[4:9, 4] = 0.5
    antialias[4:9, 12] = 0.25
    random = np.zeros((15, 19), np.float32)
    random[2:-2, 2:-2] = np.random.default_rng(8192).choice([0, 0.3, 0.8, 1], (11, 15))
    glyphs = {}
    _load_glyph(dict(face="OpenSans", size=32, bold=False, italic=False), "R", glyphs)
    bitmap = glyphs["R"]["bitmap"].astype(np.float32) / 255
    glyph = np.pad(bitmap, 8).astype(np.float32)
    cases = {"rectangle": rectangle, "antialias": antialias, "random": random, "glyph_R": glyph}
    arrays = {}
    for name, pixels in cases.items():
        arrays[name + "_input"] = pixels.copy()
        h, w = pixels.shape
        result = _sdf_cpu._calc_distance_field(pixels, w, h, 8)
        assert result is None
        arrays[name + "_expected"] = pixels
    data = destination / "sdf_upstream.npz"
    np.savez_compressed(data, **arrays)
    extension = Path(_sdf_cpu.__file__)
    package = Path(vispy.__file__).parent
    font = package / "util/fonts/data/OpenSans-Regular.ttf"
    provenance = {
        "schema": 1, "vispy_version": vispy.__version__,
        "vispy_origin": str(Path(vispy.__file__).resolve()),
        "sdf_origin": str(extension.resolve()),
        "sdf_sha256": hashlib.sha256(extension.read_bytes()).hexdigest(),
        "font_sha256": hashlib.sha256(font.read_bytes()).hexdigest(),
        "font": "OpenSans-Regular.ttf version 1.10 (Apache-2.0)",
        "python": platform.python_version(), "numpy": np.__version__,
        "freetype_py": metadata.version("freetype-py"),
        "spread": 8, "random_seed": 8192, "cases": list(cases),
        "source": "PyPI vispy==0.17.0; isolated installed wheel, no fork overlay",
        "capture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "arrays_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
    }
    (destination / "sdf_upstream.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance))


if __name__ == "__main__":
    capture(Path(sys.argv[1]).resolve())
